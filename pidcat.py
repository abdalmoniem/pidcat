import re
import sys
import shutil
import argparse

from pathlib import Path

from subprocess import PIPE
from subprocess import run as processRun
from subprocess import Popen as ProcessOpen

from typing import Set
from typing import List
from typing import Dict
from typing import Tuple
from typing import Optional

from model.State import State
from model.CliArgs import CliArgs
from model.MockTTY import MockTTY

from utils.terminalColors import RED
from utils.terminalColors import BLUE
from utils.terminalColors import CYAN
from utils.terminalColors import RESET
from utils.terminalColors import BLACK
from utils.terminalColors import GREEN
from utils.terminalColors import WHITE
from utils.terminalColors import YELLOW
from utils.terminalColors import MAGENTA
from utils.terminalColors import colorize
from utils.terminalColors import termColor

from controller.Writer import Writer
from controller.FileWriter import FileWriter
from controller.ConsoleWriter import ConsoleWriter

VERSION = "2.6.1"

# --- CONSTANTS and GLOBALS ---
LOG_LEVELS = "VDIWEF"
LOG_LEVELS_MAP = {level: index for index, level in enumerate(LOG_LEVELS)}

LAST_USED = [
    RED,
    BLUE,
    CYAN,
    GREEN,
    YELLOW,
    MAGENTA,
]

KNOWN_TAGS = {
    "jdwp": WHITE,
    "DEBUG": YELLOW,
    "Process": WHITE,
    "dalvikvm": WHITE,
    "StrictMode": WHITE,
    "AndroidRuntime": CYAN,
    "ActivityThread": WHITE,
    "ActivityManager": WHITE,
}

SYSTEM_TAGS = [
    r"Tile",
    r"HWUI",
    r"skia",
    r"libc",
    r"libEGL",
    r"Dialog",
    r"System",
    r"OneTrace",
    r"PreCache",
    r"PlayCore",
    r"BpBinder",
    r"VRI\[.*?\]",
    r"AudioTrack",
    r"ImeTracker",
    r"cutils-dev",
    r"JavaBinder",
    r"FrameEvents",
    r"QualityInfo",
    r"ViewExtract",
    r"FirebaseApp",
    r"AdrenoUtils",
    r"ViewRootImpl",
    r"nativeloader",
    r"WindowManager",
    r"OverlayHandler",
    r"ActivityThread",
    r"SurfaceControl",
    r"\[UAH_CLIENT\]",
    r"DisplayManager",
    r"AdrenoGLES-.*?",
    r"VelocityTracker",
    r"OplusBracketLog",
    r"PipelineWatcher",
    r"AppWidgetManager",
    r"BLASTBufferQueue",
    r"InsetsController",
    r"FirebaseSessions",
    r"ProfileInstaller",
    r"ExtensionsLoader",
    r"SurfaceSyncGroup",
    r"DesktopModeFlags",
    r"AppCompatDelegate",
    r"AppWidgetProvider",
    r"AppWidgetHostView",
    r"ApplicationLoaders",
    r"OplusGraphicsEvent",
    r"OplusAppHeapManager",
    r"FirebaseCrashlytics",
    r"FirebaseInitProvider"
    r"ViewRootImplExtImpl",
    r"BufferQueueConsumer",
    r"BufferQueueProducer",
    r"OplusCursorFeedback",
    r"ViewRootImplExtImpl",
    r"OplusActivityManager",
    r"CompatChangeReporter",
    r"SessionsDependencies",
    r"OplusInputMethodUtil",
    r"BufferPoolAccessor.*?",
    r"OplusViewDebugManager",
    r"WindowOnBackDispatcher",
    r"CompactWindowAppManager",
    r"OplusScrollToTopManager",
    r"ResourcesManagerExtImpl",
    r"ScrollOptimizationHelper",
    r"OplusActivityThreadExtImpl",
    r"DynamicFramerate\s*\[.*?\]",
    r"OplusViewDragTouchViewHelper",
    r"OplusPredictiveBackController",
    r"OplusSystemUINavigationGesture",
    r"OplusInputMethodManagerInternal",
    r"OplusCustomizeRestrictionManager",
    r"oplus\.android\.OplusFrameworkFactoryImpl",
]

NO_COLOR = re.compile(r"\033\[.*?m")
BACKTRACE_LINE = re.compile(r"^#(.*?)pc\s(.*?)$")
NATIVE_TAGS_LINE = re.compile(r".*nativeGetEnabledTags.*")
LOG_LINE = re.compile(r"^([A-Z])/(.+?)\( *(\d+)\): (.*?)$")
PID_KILL = re.compile(r"^Killing (\d+):([a-zA-Z0-9._:]+)/[^:]+: (.*)$")
PID_LEAVE = re.compile(r"^No longer want ([a-zA-Z0-9._:]+) \(pid (\d+)\): .*$")
PID_DEATH = re.compile(r"^Process ([a-zA-Z0-9._:]+) \(pid (\d+)\) has died.?$")
PID_LINE = re.compile(r"^\w+\s+(\w+)\s+\w+\s+\w+\s+\w+\s+\w+\s+\w+\s+\w\s(.*?)$")
PID_START = re.compile(r"^.*: Start proc (\d+):([a-zA-Z0-9._:]+)/[a-z0-9]+ for (.*)$")
PID_START_UGID = re.compile(r"^.*: Start proc ([a-zA-Z0-9._:]+) for ([a-z]+ [^:]+): pid=(\d+) uid=(\d+) gids=(.*)$")
PID_START_DALVIK = re.compile(r"^E/dalvikvm\(\s*(\d+)\): >>>>> ([a-zA-Z0-9._:]+) \[ userId:0 \| appId:(\d+) \]$")
VISIBLE_ACTIVITIES = re.compile(
    r"VisibleActivityProcess\:\[\s*(?:(?:ProcessRecord\{\w+\s*\d+\:(?:[a-zA-Z.]+)\/\w+\})\s*)+\]"
)
VISIBLE_PACKAGES = re.compile(r"ProcessRecord\{\w+\s*\d+\:([a-zA-Z.]+)\/\w+\}")


def getArgParser() -> argparse.ArgumentParser:
    """Creates and returns the ArgumentParser instance."""

    parser = argparse.ArgumentParser(
        add_help=False,
        prog=Path(sys.argv[0]).stem,
        description="A colorized Android logcat viewer with advanced filtering capabilities.",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        metavar="package(s)",
        dest="package",
        nargs="*",
        help="Application package name(s)\nThis can be specified multiple times",
    )

    parser.add_argument(
        "-h",
        "--help",
        action="help",
        default=argparse.SUPPRESS,
        help="Show this help message and exit.",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"{Path(parser.prog).stem} v{VERSION}",
        help="Print the version number and exit",
    )
    parser.add_argument(
        "-a",
        "--all",
        dest="all",
        action="store_true",
        default=False,
        help="Print log messages from all packages, default: %(default)s",
    )
    parser.add_argument(
        "-k",
        "--keep",
        dest="keepLogcat",
        action="store_true",
        default=False,
        help="Keep the entire log before running, default: %(default)s",
    )
    parser.add_argument(
        "-d",
        "--device",
        dest="useDevice",
        action="store_true",
        default=False,
        help="Use first device for log input, default: %(default)s",
    )
    parser.add_argument(
        "-e",
        "--emulator",
        dest="useEmulator",
        action="store_true",
        default=False,
        help="Use first emulator for log input, default: %(default)s",
    )
    parser.add_argument(
        "-g",
        "--color-gc",
        dest="colorGC",
        action="store_true",
        default=False,
        help="Color garbage collection, default: %(default)s",
    )
    parser.add_argument(
        "-N",
        "--no-color",
        dest="noColor",
        action="store_true",
        default=False,
        help="Disable colors, default: %(default)s",
    )
    parser.add_argument(
        "-P",
        "--show-pid",
        dest="showPID",
        action="store_true",
        default=False,
        help="Show package name in output, default: %(default)s",
    )
    parser.add_argument(
        "-p",
        "--show-package",
        dest="showPackage",
        action="store_true",
        default=False,
        help="Show package name in output, default: %(default)s",
    )
    parser.add_argument(
        "-S",
        "--always-show-tags",
        dest="alwaysShowTags",
        action="store_true",
        default=False,
        help="Always show the tag name, default: %(default)s",
    )
    parser.add_argument(
        "-c",
        "--current",
        dest="currentApp",
        action="store_true",
        default=False,
        help="Filter logcat by current running app(s), default: %(default)s",
    )
    parser.add_argument(
        "-I",
        "--ignore-system-tags",
        dest="ignoreSystemTags",
        action="store_true",
        default=False,
        help="Filter output by ignoring known system tags, default: %(default)s"
        "\nUse --ignore-tag to ignore additional tags if needed",
    )
    parser.add_argument(
        "-t",
        "--tag",
        metavar="TAG",
        dest="tag",
        action="append",
        help="Filter output by specified tag(s)\nThis can be specified multiple times, or as a comma separated list",
    )
    parser.add_argument(
        "-i",
        "--ignore-tag",
        metavar="IGNORED_TAG",
        dest="ignoreTag",
        action="append",
        help="Filter output by ignoring specified tag(s)\nThis can be specified multiple times, or as a comma separated list",
    )
    parser.add_argument(
        "-l",
        "--log-level",
        dest="logLevel",
        metavar=f"LEVEL [{'|'.join(LOG_LEVELS + LOG_LEVELS.lower())}]",
        type=str,
        choices=LOG_LEVELS + LOG_LEVELS.lower(),
        default="V",
        help="Filter messages lower than minimum log level, default: %(default)s",
    )
    parser.add_argument(
        "-r",
        "--regex",
        metavar="REGEX",
        dest="regex",
        type=str,
        help="Filter output messages using the specified %(metavar)s",
    )
    parser.add_argument(
        "-x",
        "--pid-width",
        metavar="X",
        dest="pidWidth",
        type=int,
        default=6,
        help="Width of PID column, default: %(default)s",
    )
    parser.add_argument(
        "-n",
        "--package-width",
        metavar="N",
        dest="packageWidth",
        type=int,
        default=20,
        help="Width of package/process name column, default: %(default)s",
    )
    parser.add_argument(
        "-m",
        "--tag-width",
        metavar="M",
        dest="tagWidth",
        type=int,
        default=20,
        help="Width of tag column, default: %(default)s",
    )
    parser.add_argument(
        "-s",
        "--serial",
        metavar="DEVICE_SERIAL",
        dest="deviceSerial",
        help="Device serial number",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE_PATH",
        dest="outputPath",
        type=str,
        default="",
        help="Output filename",
    )

    return parser


def getConsoleWidth() -> int:
    """Return the current terminal width"""

    width = shutil.get_terminal_size(fallback=(80, 20)).columns

    return width


def getWrappedIndent(message: str, width: int, headerSize: int) -> str:
    """Wraps and indents long log messages."""

    if width == -1:
        return message

    message = message.replace("\t", "    ")
    wrapArea = width - headerSize
    messageBuffer = ""
    current = 0

    while current < len(message):
        nextIndex = min(current + wrapArea, len(message))
        messageBuffer += message[current:nextIndex]

        if nextIndex < len(message):
            messageBuffer += "\n"
            messageBuffer += " " * headerSize

        current = nextIndex

    return messageBuffer


def getTagColor(tag: str) -> int:
    """Allocates a unique color for a tag based on LRU."""

    if tag not in KNOWN_TAGS:
        KNOWN_TAGS[tag] = LAST_USED[0]

    color = KNOWN_TAGS[tag]

    if color in LAST_USED:
        LAST_USED.remove(color)
        LAST_USED.append(color)

    return color


def getAdbCommand(args: CliArgs) -> List[str]:
    """Constructs the base adb command list."""

    baseAdbCommand = ["adb"]

    if args.deviceSerial:
        baseAdbCommand.extend(["-s", args.deviceSerial])

    if args.useDevice:
        baseAdbCommand.append("-d")

    if args.useEmulator:
        baseAdbCommand.append("-e")

    return baseAdbCommand


def getCurrentAppPackage(baseAdbCommand: List[str]) -> Optional[List[str]]:
    """Gets the package name of the currently running app."""

    systemDumpCommand = baseAdbCommand + [
        "shell",
        "dumpsys",
        "activity",
        "activities",
    ]

    systemDump = processRun(systemDumpCommand, stdout=PIPE, stderr=PIPE, text=True, errors="replace").stdout

    visibleActivities = re.search(VISIBLE_ACTIVITIES, systemDump)

    if not visibleActivities:
        return None

    visiblePackages = re.findall(VISIBLE_PACKAGES, visibleActivities.group())

    return visiblePackages if visiblePackages else None


def getProcesses(baseAdbCommand: List[str], catchallPackage: List[str], args: CliArgs) -> Dict[str, str]:
    """Populates initial PIDs map {PID: PackageName} for catch-all packages or all processes if args.all is True."""

    pidsMap = {}
    psCommand = baseAdbCommand + ["shell", "ps"]

    psPid = ProcessOpen(psCommand, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    psStdout = psPid.stdout

    while True and psStdout:
        line = psStdout.readline().decode("utf-8", "replace").strip()

        if not line:
            break

        pidMatch = PID_LINE.match(line)

        if pidMatch is not None:
            pid = pidMatch.group(1)
            process = pidMatch.group(2)

            isTargetPackage = process in catchallPackage

            # If not using -a, only add targeted packages
            if args.all or isTargetPackage:
                pidsMap[pid] = process  # Store {PID: PackageName}

    return pidsMap


def getDeadProcesses(
    tag: str, message: str, pidsSet: Set[str], namedProcesses: List[str], catchallPackage: List[str]
) -> Tuple[Optional[str], Optional[str]]:
    """Parses log lines for process death and removal."""

    if tag != "ActivityManager":
        return None, None

    for regex in (PID_KILL, PID_LEAVE, PID_DEATH):
        match = regex.match(message)

        if match:
            # PID_KILL/PID_LEAVE/PID_DEATH have different group indices
            if regex == PID_KILL:
                pid = match.group(1)
                packageLine = match.group(2)
            elif regex == PID_LEAVE:
                pid = match.group(2)
                packageLine = match.group(1)
            else:  # PID_DEATH
                pid = match.group(2)
                packageLine = match.group(1)

            if isMatchingPackage(packageLine, namedProcesses, catchallPackage) and pid in pidsSet:
                return pid, packageLine

    return None, None


def getStartedProcesses(line: str) -> Optional[Tuple[str, str, str, str, str]]:
    """Parses log lines for process start."""

    for regex in (PID_START, PID_START_UGID, PID_START_DALVIK):
        match = regex.match(line)

        if match:
            if regex == PID_START:
                startedPackage = ""
                startedPID = ""
                startedPID, startedPackage, startedTarget = match.groups()

                return startedPID, "", "", startedPackage, startedTarget
            elif regex == PID_START_UGID:
                (
                    startedPackage,
                    startedTarget,
                    startedPID,
                    startedUID,
                    startedGIDs,
                ) = match.groups()

                return startedPID, startedUID, startedGIDs, startedPackage, startedTarget
            else:  # PID_START_DALVIK
                startedPID, startedPackage, startedUID = match.groups()

                return startedPID, startedUID, "", startedPackage, ""

    return None


def writeLogLine(line: str, state: State, args: CliArgs, writers: List[Writer]) -> None:
    """Handles the processing and output of a single log line."""

    pidsMap = state.pidsMap
    lastTag = state.lastTag
    appPid = state.appPID
    logLevel = state.logLevel
    namedProcesses = state.namedProcesses
    catchallPackage = state.catchallPackage
    pidWidth = args.pidWidth
    packageWidth = args.packageWidth
    tagWidth = args.tagWidth
    currentHeaderSize = 0

    def writeOutput(outputLine: str, wrap: bool = False) -> None:
        buffer = ""
        for writer in writers:
            if wrap and writer.isWrappable:
                buffer = getWrappedIndent(outputLine, writer.width, currentHeaderSize)
            else:
                buffer = outputLine

            lineNoColor = NO_COLOR.sub("", buffer)
            showColors = writer.showColors
            writer.write(buffer if showColors else lineNoColor)
            writer.flush()

    nativeTags = NATIVE_TAGS_LINE.match(line)
    if nativeTags:
        return

    logLine = LOG_LINE.match(line)
    if not logLine:
        return

    level, tag, owner, message = logLine.groups()
    tag = tag.strip()
    startedProcess = getStartedProcesses(line)

    # Calculate current base header size (level + spaces)
    baseLevelSize = 3 + 1  # Level width + space

    # Process Start/Death events
    if startedProcess:
        startedPID, startedUID, startedGIDs, startedPackage, startedTarget = startedProcess
        if isMatchingPackage(startedPackage, namedProcesses, catchallPackage):
            pidsMap[startedPID] = startedPackage
            appPid = startedPID

            # Recalculate header size for process start/end messages
            currentHeaderSize = (packageWidth + 2 if args.showPackage else 0) + args.tagWidth + baseLevelSize

            writeOutput("\n")
            writeOutput(colorize(" " * (currentHeaderSize - 1), background=WHITE))
            writeOutput(f" Process {startedPackage} created for {startedTarget}\n", wrap=True)

            writeOutput(colorize(" " * (currentHeaderSize - 1), background=WHITE))
            writeOutput(f" PID: {startedPID}   UID: {startedUID}   GIDs: {startedGIDs}")
            writeOutput("\n")

            lastTag = None

    deadPID, deadProcName = getDeadProcesses(tag, message, set(pidsMap.keys()), namedProcesses, catchallPackage)
    if deadPID:
        if deadPID in pidsMap:
            del pidsMap[deadPID]

        currentHeaderSize = (packageWidth + 2 if args.showPackage else 0) + args.tagWidth + baseLevelSize

        writeOutput("\n")
        writeOutput(colorize(" " * (currentHeaderSize - 1), background=RED))
        writeOutput(f" Process {deadProcName} (PID: {deadPID}) ended")
        writeOutput("\n")

        lastTag = None

    # Filter logs
    if not args.all and owner not in pidsMap:
        return

    if level in LOG_LEVELS_MAP and LOG_LEVELS_MAP[level] < logLevel:
        return

    if args.ignoreTag and isMatchingTag(tag, args.ignoreTag):
        return

    if args.tag and not isMatchingTag(tag, args.tag):
        return

    # Handle Backtrace for native crashes
    if tag == "DEBUG":
        btLine = BACKTRACE_LINE.match(message.lstrip())
        if btLine is not None:
            message = message.lstrip()
            owner = appPid  # Associate backtrace with the app PID

    # lineBuffer = ""
    currentHeaderSize = 0

    # --- OWNER PID SECTION ---
    if args.showPID and owner:
        pidColor = getTagColor(owner)

        if len(owner) > pidWidth:
            owner = f"{owner[: pidWidth - 3]}..."
        pidDisplay = owner.ljust(pidWidth)

        writeOutput(colorize(pidDisplay, pidColor))
        writeOutput("  ")  # Two spaces separator
        currentHeaderSize += pidWidth + 2
    # ----------------------------

    # --- PACKAGE NAME SECTION ---
    if args.showPackage and owner:
        packageName = pidsMap.get(owner, f"UNKNOWN({owner})")
        pkgColor = getTagColor(packageName)

        if len(packageName) > packageWidth:
            packageName = f"{packageName[: packageWidth - 3]}..."
        pkgDisplay = packageName.ljust(packageWidth)

        writeOutput(colorize(pkgDisplay, pkgColor))
        writeOutput("  ")  # Two spaces separator
        currentHeaderSize += packageWidth + 2
    # ----------------------------

    # --- TAG SECTION ---
    if args.tagWidth > 0:
        if tag != lastTag or args.alwaysShowTags:
            lastTag = tag
            color = getTagColor(tag)

            if len(tag) > tagWidth:
                tag = f"{tag[: tagWidth - 3]}..."
            tag = tag.rjust(tagWidth) if args.showPackage else tag.ljust(tagWidth)

            writeOutput(colorize(tag, color))
        else:
            writeOutput(" " * tagWidth)

        writeOutput(" ")
        currentHeaderSize += tagWidth + 1
    # ----------------------------

    # --- LEVEL SECTION ---
    foreground = {"V": WHITE, "D": BLACK, "I": BLACK, "W": BLACK, "E": BLACK, "F": BLACK}.get(level, WHITE)
    background = {"V": BLACK, "D": BLUE, "I": GREEN, "W": YELLOW, "E": RED, "F": RED}.get(level, BLACK)
    levelStr = colorize(f" {level} ", foreground, background)
    writeOutput(levelStr)
    writeOutput(" ")
    currentHeaderSize += baseLevelSize  # Level width + space
    # ----------------------------

    # --- MESSAGE SECTION --- (apply rules)
    messageRules = {}

    # StrictMode rule
    STRICT_MODE = re.compile(r"^(StrictMode policy violation)(; ~duration=)(\d+ ms)")
    messageRules[STRICT_MODE] = r"\1%s\2%s\3%s" % (termColor(RED), termColor(YELLOW), RESET)

    # GC coloring rule
    if args.colorGC:
        COLOR_GC = re.compile(
            r"^(GC_(?:CONCURRENT|FOR_M?ALLOC|EXTERNAL_ALLOC|EXPLICIT) )"
            + r"(freed <?\d+.)(, \d+\% free \d+./\d+., )(paused \d+ms(?:\+\d+ms)?)"
        )
        messageRules[COLOR_GC] = r"\1%s\2%s\3%s\4%s" % (termColor(GREEN), RESET, termColor(YELLOW), RESET)

    for matcher in messageRules:
        message = matcher.sub(messageRules[matcher], message)

    writeOutput(message, wrap=True)
    writeOutput("\n")
    # ----------------------------

    # Update state for next line
    state.lastTag = lastTag
    state.appPID = appPid


def isMatchingPackage(token: str, namedProcesses: List[str], catchallPackage: List[str]) -> bool:
    """Checks if a process token matches any of the package filters."""

    if not catchallPackage and not namedProcesses:
        return True  # No filter specified

    if token in namedProcesses:
        return True

    index = token.find(":")

    return (token in catchallPackage) if index == -1 else (token[:index] in catchallPackage)


def isMatchingTag(tag: str, tags: List[str]) -> bool:
    """Checks if a tag matches any of the given tag regex patterns."""

    for mTag in map(str.strip, tags):
        # If the pattern contains regex special chars, treat as regex
        if any(mChar in mTag for mChar in r".*+?[]{}()|\^$") and re.match(rf"{mTag}", tag):
            return True

        # Otherwise, do substring matching (contains)
        elif mTag in tag:
            return True

    return False


def main() -> None:
    """
    Main entry point for the PidCat logcat viewer.

    This function is responsible for:

    - Parsing command-line arguments
    - Initializing the logcat viewer state
    - Starting the logcat process
    - Writing the logcat output to the console or a file
    """
    parser = getArgParser()
    args = parser.parse_args()

    args = CliArgs(**vars(args))

    try:
        baseAdbCommand = getAdbCommand(args)
        adbCommand = baseAdbCommand + ["logcat", "-v", "brief"]
        packages = list(set(args.package))
        logLevel = LOG_LEVELS_MAP[args.logLevel.upper()]
        consoleWidth = getConsoleWidth()
        consoleWriter = ConsoleWriter(width=consoleWidth, showColors=not args.noColor)
        writers = list[Writer]([consoleWriter])

        if args.ignoreSystemTags:
            args.ignoreTag = [f"^{systemTag.strip()}$" for systemTag in SYSTEM_TAGS]

        if args.tag:
            args.tag = [tag.strip() for tag_arg in args.tag for tag in tag_arg.split(",")]

        if args.ignoreTag:
            args.ignoreTag = [tag.strip() for tag_arg in args.ignoreTag for tag in tag_arg.split(",")]

        if not args.keepLogcat:
            adbClearCommand = baseAdbCommand + ["logcat", "-c"]
            processRun(adbClearCommand, check=False)

        if args.outputPath:
            outputFile = open(args.outputPath, "w+", encoding="utf-8")
            fileWriter = FileWriter(width=consoleWidth, outputFile=outputFile)
            writers.append(fileWriter)

        if args.currentApp:
            runningPackages = getCurrentAppPackage(baseAdbCommand)
            packages += runningPackages if runningPackages else []

        if args.regex:
            adbCommand.extend(["-e", args.regex])

        if packages:
            print(f"Capturing logcat messages from packages: [{', '.join(packages)}]...")
        else:
            args.all = True
            print("Capturing logcat messages...")

        # Determine exact processes vs. catch-all packages
        catchallPackage = list(filter(lambda package: package.find(":") == -1, packages))
        namedProcesses = list(filter(lambda package: package.find(":") != -1, packages))
        namedProcesses = list(map(lambda package: package[:-1] if package.endswith(":") else package, namedProcesses))
        pidsMap = getProcesses(baseAdbCommand, catchallPackage, args)

        adbPID = ProcessOpen(adbCommand, stdout=PIPE, stderr=PIPE) if sys.stdin.isatty() else MockTTY()
        logStream = adbPID.stdout

        state = State(
            pidsMap=pidsMap,
            lastTag=None,
            appPID=None,
            logLevel=logLevel,
            namedProcesses=namedProcesses,
            catchallPackage=catchallPackage,
        )

        while adbPID.poll() is None and logStream:
            rawLine = logStream.readline()
            if not rawLine:
                break

            # Check if the stream is binary (like ProcessOpen stdout), which returns bytes
            if isinstance(rawLine, bytes):
                line = rawLine.decode(encoding="utf-8", errors="replace").strip()
            # Otherwise, assume it's a text stream (like sys.stdin), which returns str
            else:
                line = str(rawLine).strip()

            # Update the writers width if changed
            for writer in writers:
                consoleWidth = getConsoleWidth()
                writer.width = consoleWidth

            writeLogLine(line=line, state=state, args=args, writers=writers)
    except KeyboardInterrupt:
        print(f"\n\n\n{Path(parser.prog).stem} stopped by user!", file=sys.stderr)
    finally:
        # Cleanup
        for writer in writers:
            writer.close()


if __name__ == "__main__":
    main()
