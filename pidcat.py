import re
import sys
import shutil
import argparse
import subprocess

from pathlib import Path
from dataclasses import dataclass

from subprocess import PIPE
from subprocess import Popen

from typing import Set
from typing import List
from typing import Dict
from typing import Tuple
from typing import TextIO
from typing import Optional

from terminalColors import RED
from terminalColors import BLUE
from terminalColors import CYAN
from terminalColors import RESET
from terminalColors import BLACK
from terminalColors import GREEN
from terminalColors import WHITE
from terminalColors import YELLOW
from terminalColors import MAGENTA
from terminalColors import colorize
from terminalColors import termColor

VERSION = "2.5.5"

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
    r"VRI\[.*?\]",
    r"AudioTrack",
    r"ImeTracker",
    r"FrameEvents",
    r"ViewRootImpl",
    r"WindowManager",
    r"OverlayHandler",
    r"ActivityThread",
    r"SurfaceControl",
    r"VelocityTracker",
    r"OplusBracketLog",
    r"PipelineWatcher",
    r"AppWidgetManager",
    r"BLASTBufferQueue",
    r"InsetsController",
    r"AppWidgetHostView",
    r"ViewRootImplExtImpl",
    r"BufferQueueConsumer",
    r"BufferQueueProducer",
    r"OplusCursorFeedback",
    r"BufferPoolAccessor.*?",
    r"OplusViewDebugManager",
    r"WindowOnBackDispatcher",
    r"OplusScrollToTopManager",
    r"ResourcesManagerExtImpl",
    r"DynamicFramerate\s*\[.*?\]",
    r"OplusViewDragTouchViewHelper",
    r"oplus\.android\.OplusFrameworkFactoryImpl",
]

NO_COLOR = re.compile(r"\033\[.*?m")
BACKTRACE_LINE = re.compile(r"^#(.*?)pc\s(.*?)$")
NATIVE_TAGS_LINE = re.compile(r".*nativeGetEnabledTags.*")
LOG_LINE = re.compile(r"^([A-Z])/(.+?)\( *(\d+)\): (.*?)$")
PID_KILL = re.compile(r"^Killing (\d+):([a-zA-Z0-9._:]+)/[^:]+: (.*)$")
PID_LEAVE = re.compile(r"^No longer want ([a-zA-Z0-9._:]+) \(pid (\d+)\): .*$")
PID_DEATH = re.compile(r"^Process ([a-zA-Z0-9._:]+) \(pid (\d+)\) has died.?$")
PID_LINE = re.compile(r"^\w+\s+(\w+)\s+\w+\s+\w+\s+\w+\s+\w+\s+\w+\s+\w\s([\w|\.|\/]+)$")
PID_START = re.compile(r"^.*: Start proc (\d+):([a-zA-Z0-9._:]+)/[a-z0-9]+ for (.*)$")
PID_START_UGID = re.compile(r"^.*: Start proc ([a-zA-Z0-9._:]+) for ([a-z]+ [^:]+): pid=(\d+) uid=(\d+) gids=(.*)$")
PID_START_DALVIK = re.compile(r"^E/dalvikvm\(\s*(\d+)\): >>>>> ([a-zA-Z0-9._:]+) \[ userId:0 \| appId:(\d+) \]$")
CURRENT_PACKAGE = re.compile(r"VisibleActivityProcess\:\[\s*ProcessRecord\{\w+\s*\d+\:(.*?)\/\w+\}\]")


@dataclass
class State:
    """Holds the current state of the logcat processing."""

    pids_map: Dict[str, str]
    last_tag: Optional[str]
    app_pid: Optional[str]
    min_level: int
    named_processes: List[str]
    catchall_package: List[str]


@dataclass
class ColorConfig:
    """Configuration for color output."""

    consoleWidth: int
    showColors: bool
    outputFile: Optional[TextIO]


@dataclass
class Args:
    """Configuration for logcat filtering and display."""

    package: List[str]
    all: bool = False
    keepLogcat: bool = False
    useDevice: bool = False
    useEmulator: bool = False
    colorGC: bool = False
    noColor: bool = False
    showPackage: bool = False
    alwaysShowTags: bool = False
    currentApp: bool = False
    ignoreSystemTags: bool = False
    tag: Optional[List[str]] = None
    ignoreTag: Optional[List[str]] = None
    minLevel: str = "V"
    regex: Optional[str] = None
    tagWidth: int = 20
    packageWidth: int = 20
    deviceSerial: Optional[str] = None
    output: str = ""


def getConsoleWidth() -> int:
    """Return the current terminal width, or -1 if it cannot be determined."""

    try:
        # Works on all platforms (Python 3.3+)
        width = shutil.get_terminal_size(fallback=(80, 20)).columns

        return width
    except Exception as ex:
        error = colorize(f"Warning: Could not get terminal width: {ex}", foreground=RED)
        print(error, file=sys.stderr)

        return -1


def indentWrap(message: str, width: int, headerSize: int) -> str:
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


def allocateColor(tag: str) -> int:
    """Allocates a unique color for a tag based on LRU."""

    if tag not in KNOWN_TAGS:
        KNOWN_TAGS[tag] = LAST_USED[0]

    color = KNOWN_TAGS[tag]

    if color in LAST_USED:
        LAST_USED.remove(color)
        LAST_USED.append(color)

    return color


def isTagInTags(tag: str, tags: List[str]) -> bool:
    """Checks if a tag matches any of the given tag regex patterns."""

    for mTag in map(str.strip, tags):
        # If the pattern contains regex special chars, treat as regex
        if any(mChar in mTag for mChar in r".*+?[]{}()|\^$") and re.match(rf"{mTag}", tag):
            return True

        # Otherwise, do substring matching (contains)
        elif mTag in tag:
            return True

    return False


def getAdbCommand(args: Args) -> List[str]:
    """Constructs the base adb command list."""

    baseAdbCommand = ["adb"]

    if args.deviceSerial:
        baseAdbCommand.extend(["-s", args.deviceSerial])

    if args.useDevice:
        baseAdbCommand.append("-d")

    if args.useEmulator:
        baseAdbCommand.append("-e")

    return baseAdbCommand


def getCurrentAppPackage(baseAdbCommand: List[str]) -> Optional[str]:
    """Gets the package name of the currently running app."""

    try:
        systemDumpCommand = baseAdbCommand + [
            "shell",
            "dumpsys",
            "activity",
            "activities",
        ]

        systemDump = subprocess.run(systemDumpCommand, stdout=PIPE, stderr=PIPE, text=True, errors="replace").stdout

        match = re.search(CURRENT_PACKAGE, systemDump)

        return match.group(1) if match else None
    except Exception as ex:
        error = colorize(f"Error getting current app package: {ex}", foreground=RED)
        print(error, file=sys.stderr)

        return None


def getInitialPidsMap(baseAdbCommand: List[str], catchallPackage: List[str], args: Args) -> Dict[str, str]:
    """Populates initial PIDs map {PID: PackageName} for catch-all packages or all processes if args.all is True."""

    pidsMap = {}
    psCommand = baseAdbCommand + ["shell", "ps"]

    try:
        psPid = subprocess.Popen(psCommand, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        psStdout = psPid.stdout

        while True and psStdout:
            line = psStdout.readline().decode("utf-8", "replace").strip()

            if not line:
                break

            pidMatch = PID_LINE.match(line)

            if pidMatch is not None:
                pid = pidMatch.group(1)
                proc = pidMatch.group(2)

                isTargetPackage = proc in catchallPackage

                # If not using -a, only add targeted packages
                if not args.all and not isTargetPackage:
                    continue

                # Simple filter for system/kernel processes when args.all is used
                if args.all and proc.startswith("/system"):
                    continue

                pidsMap[pid] = proc  # Store {PID: PackageName}
    except Exception as ex:
        error = colorize(f"Warning: Could not get initial PIDs: {ex}", foreground=RED)
        print(error, file=sys.stderr)

    return pidsMap


def matchPackages(token: str, namedProcesses: List[str], catchallPackage: List[str]) -> bool:
    """Checks if a process token matches any of the package filters."""

    if not catchallPackage and not namedProcesses:
        return True  # No filter specified

    if token in namedProcesses:
        return True

    index = token.find(":")

    return (token in catchallPackage) if index == -1 else (token[:index] in catchallPackage)


def parseProcDeath(
    tag: str,
    message: str,
    pidsSet: Set[str],
    namedProcesses: List[str],
    catchallPackage: List[str],
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

            if matchPackages(packageLine, namedProcesses, catchallPackage) and pid in pidsSet:
                return pid, packageLine

    return None, None


def parseProcStart(line: str) -> Optional[Tuple[str, str, str, str, str]]:
    """Parses log lines for process start."""

    for regex in (PID_START, PID_START_UGID, PID_START_DALVIK):
        match = regex.match(line)

        if match:
            if regex == PID_START:
                linePid: str
                linePackage: str
                target: str
                linePid, linePackage, target = match.groups()

                return linePackage, target, linePid, "", ""
            elif regex == PID_START_UGID:
                linePackage, target, linePid, lineUid, lineGids = match.groups()

                return linePackage, target, linePid, lineUid, lineGids
            else:  # PID_START_DALVIK
                linePid, linePackage, lineUid = match.groups()

                return linePackage, "", linePid, lineUid, ""

    return None


def createArgParser() -> argparse.ArgumentParser:
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
        help="Filter logcat by current running app, default: %(default)s",
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
        "--min-level",
        dest="minLevel",
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
        "-m",
        "--tag-width",
        metavar="M",
        dest="tagWidth",
        type=int,
        default=20,
        help="Width of tag column, default: %(default)s",
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
        "-s",
        "--serial",
        metavar="DEVICE_SERIAL",
        dest="deviceSerial",
        help="Device serial number",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        dest="output",
        type=str,
        default="",
        help="Output filename",
    )

    return parser


def processLogLine(line: str, state: State, args: Args, colorConfig: ColorConfig) -> None:
    """Handles the processing and output of a single log line."""

    pidsMap = state.pids_map
    lastTag = state.last_tag
    appPid = state.app_pid
    minLevel = state.min_level
    width = colorConfig.consoleWidth
    showColors = colorConfig.showColors
    outputFile = colorConfig.outputFile
    namedProcesses = state.named_processes
    catchallPackage = state.catchall_package
    packageWidth = args.packageWidth
    tagWidth = args.tagWidth

    def writeOutput(outputLine: str) -> None:
        lineNoColor = NO_COLOR.sub("", outputLine)

        print(outputLine if showColors else lineNoColor)

        if outputFile:
            outputFile.write(lineNoColor + "\n")

    nativeTags = NATIVE_TAGS_LINE.match(line)
    if nativeTags:
        return

    logLine = LOG_LINE.match(line)
    if not logLine:
        return

    level, tag, owner, message = logLine.groups()
    tag = tag.strip()
    start = parseProcStart(line)

    # Calculate current base header size (level + spaces)
    baseLevelSize = 3 + 1  # Level width + space

    # Process Start/Death events
    if start:
        linePackage, target, linePid, lineUid, lineGids = start
        if matchPackages(linePackage, namedProcesses, catchallPackage):
            pidsMap[linePid] = linePackage
            appPid = linePid

            # Recalculate header size for process start/end messages
            currentHeaderSize = (packageWidth + 2 if args.showPackage else 0) + args.tagWidth + baseLevelSize

            lineBuffer = "\n"
            lineBuffer += colorize(" " * (currentHeaderSize - 1), background=WHITE)
            lineBuffer += indentWrap(" Process %s created for %s\n" % (linePackage, target), width, currentHeaderSize)
            lineBuffer += colorize(" " * (currentHeaderSize - 1), background=WHITE)
            lineBuffer += " PID: %s   UID: %s   GIDs: %s" % (linePid, lineUid, lineGids)
            lineBuffer += "\n"

            writeOutput(lineBuffer)
            lastTag = None

    deadPid, deadPname = parseProcDeath(tag, message, set(pidsMap.keys()), namedProcesses, catchallPackage)
    if deadPid:
        if deadPid in pidsMap:
            del pidsMap[deadPid]

        currentHeaderSize = (packageWidth + 2 if args.showPackage else 0) + args.tagWidth + baseLevelSize

        lineBuffer = "\n"
        lineBuffer += colorize(" " * (currentHeaderSize - 1), background=RED)
        lineBuffer += " Process %s (PID: %s) ended" % (deadPname, deadPid)
        lineBuffer += "\n"

        writeOutput(lineBuffer)
        lastTag = None

    # Filter logs
    if not args.all and owner not in pidsMap:
        return

    if level in LOG_LEVELS_MAP and LOG_LEVELS_MAP[level] < minLevel:
        return

    if args.ignoreTag and isTagInTags(tag, args.ignoreTag):
        return

    if args.tag and not isTagInTags(tag, args.tag):
        return

    # Handle Backtrace for native crashes
    if tag == "DEBUG":
        btLine = BACKTRACE_LINE.match(message.lstrip())
        if btLine is not None:
            message = message.lstrip()
            owner = appPid  # Associate backtrace with the app PID

    lineBuffer = ""
    currentHeaderSize = 0

    # --- PACKAGE NAME SECTION ---
    if args.showPackage and owner:
        packageName = pidsMap.get(owner, "UNKNOWN")
        pkgColor = allocateColor(packageName)

        if len(packageName) > packageWidth:
            packageName = f"{packageName[: packageWidth - 3]}..."
        pkgDisplay = packageName.ljust(packageWidth)

        lineBuffer += colorize(pkgDisplay, pkgColor)
        lineBuffer += "  "  # Two spaces separator
        currentHeaderSize += packageWidth + 2
    # ----------------------------

    # --- TAG SECTION ---
    if args.tagWidth > 0:
        if tag != lastTag or args.alwaysShowTags:
            lastTag = tag
            color = allocateColor(tag)

            if len(tag) > tagWidth:
                tag = f"{tag[: tagWidth - 3]}..."
            tag = tag.rjust(tagWidth) if args.showPackage else tag.ljust(tagWidth)

            lineBuffer += colorize(tag, color)
        else:
            lineBuffer += " " * tagWidth

        lineBuffer += " "
        currentHeaderSize += tagWidth + 1
    # ----------------------------

    # --- LEVEL SECTION ---
    levelStr = f" {level} "
    if showColors:
        foreground = {
            "V": WHITE,
            "D": BLACK,
            "I": BLACK,
            "W": BLACK,
            "E": BLACK,
            "F": BLACK,
        }.get(level, WHITE)

        background = {
            "V": BLACK,
            "D": BLUE,
            "I": GREEN,
            "W": YELLOW,
            "E": RED,
            "F": RED,
        }.get(level, BLACK)

        lineBuffer += colorize(levelStr, foreground, background)
    else:
        lineBuffer += levelStr

    lineBuffer += " "
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

    lineBuffer += indentWrap(message, width, currentHeaderSize)
    writeOutput(lineBuffer)
    # ----------------------------

    # Update state for next line
    state.last_tag = lastTag
    state.app_pid = appPid


def main() -> None:
    """The main entry point of the script."""
    parser = createArgParser()
    args = parser.parse_args()

    args = Args(**vars(args))

    if args.ignoreSystemTags:
        ignoredSystemTags = []
        for systemTag in SYSTEM_TAGS:
            ignoredSystemTags.append(f"^{systemTag}$")
        args.ignoreTag = ignoredSystemTags

    if args.tag:
        args.tag = [tag.strip() for tag_arg in args.tag for tag in tag_arg.split(",")]

    if args.ignoreTag:
        args.ignoreTag = [tag.strip() for tag_arg in args.ignoreTag for tag in tag_arg.split(",")]

    minLevel = LOG_LEVELS_MAP[args.minLevel.upper()]
    consoleWidth = getConsoleWidth()
    outputFile = None

    try:
        if args.output:
            outputFile = open(args.output, "a+")

        baseAdbCommand = getAdbCommand(args)
        packages = list(set(args.package))

        if args.currentApp:
            runningPackage = getCurrentAppPackage(baseAdbCommand)
            if runningPackage:
                packages.append(runningPackage)

        # Determine exact processes vs. catch-all packages
        catchallPackage = list(filter(lambda package: package.find(":") == -1, packages))
        namedProcesses = list(filter(lambda package: package.find(":") != -1, packages))
        namedProcesses = list(map(lambda package: package[:-1] if package.endswith(":") else package, namedProcesses))

        if not packages:
            args.all = True

        pidsMap = getInitialPidsMap(baseAdbCommand, catchallPackage, args)

        adbCommand = baseAdbCommand + ["logcat", "-v", "brief"]
        if args.regex:
            adbCommand.extend(["-e", args.regex])

        if not args.keepLogcat:
            adbClearCommand = baseAdbCommand + ["logcat", "-c"]
            subprocess.run(adbClearCommand, check=False)

        if sys.stdin.isatty():
            adb = subprocess.Popen(adbCommand, stdout=PIPE, stderr=PIPE)
            logStream = adb.stdout
        else:
            # Ducktype for reading from pipe/file
            class FakeStdinProcess(Popen):
                def __init__(self) -> None:
                    # Popen signature has many args, but we only need a working stdout for ducktyping
                    pass

                @property
                def stdout(self) -> TextIO:
                    return sys.stdin

                def poll(self) -> Optional[int]:
                    return None

            adb = FakeStdinProcess()
            logStream = adb.stdout

        state = State(
            pids_map=pidsMap,
            last_tag=None,
            app_pid=None,
            min_level=minLevel,
            named_processes=namedProcesses,
            catchall_package=catchallPackage,
        )

        colorConfig = ColorConfig(consoleWidth, not args.noColor, outputFile)

        if packages:
            print(f"Capturing logcat messages from packages: [{', '.join(packages)}]...")
        else:
            print("Capturing logcat messages...")

        while adb.poll() is None and logStream:
            rawLine = logStream.readline()
            if not rawLine:
                break

            # Check if the stream is binary (like Popen stdout), which returns bytes
            if isinstance(rawLine, bytes):
                line = rawLine.decode("utf-8", "replace").strip()
            # Otherwise, assume it's a text stream (like sys.stdin), which returns str
            else:
                line = str(rawLine).strip()

            # Update the console width if it has changed
            colorConfig.consoleWidth = getConsoleWidth()
            processLogLine(line, state, args, colorConfig)
    except KeyboardInterrupt:
        print(f"\n\n\n{Path(parser.prog).stem} stopped by user!", file=sys.stderr)
    except Exception as ex:
        error = colorize(f"An error occurred during log processing: {ex}", foreground=RED)
        print(error, file=sys.stderr)
    finally:
        # Cleanup
        if outputFile:
            outputFile.close()


if __name__ == "__main__":
    main()
