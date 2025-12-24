#!/usr/bin/python -u

import re
import sys
import shutil
import argparse
import subprocess
from platform import win32_ver
from subprocess import PIPE, Popen
from ctypes import WinError, byref, c_uint, windll
from typing import IO, List, Dict, Set, Optional, Tuple, Any, TextIO

__version__ = "2.5.1"

# --- CONSTANTS and GLOBALS ---
LOG_LEVELS: str = "VDIWEF"
LOG_LEVELS_MAP: Dict[str, int] = dict(
    [(LOG_LEVELS[i], i) for i in range(len(LOG_LEVELS))]
)

RESET: str = "\033[0m"
BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)
LAST_USED: List[int] = [RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN]

KNOWN_TAGS: Dict[str, int] = {
    "dalvikvm": WHITE,
    "Process": WHITE,
    "ActivityManager": WHITE,
    "ActivityThread": WHITE,
    "AndroidRuntime": CYAN,
    "jdwp": WHITE,
    "StrictMode": WHITE,
    "DEBUG": YELLOW,
}

TAGTYPES: Dict[str, str] = {
    "V": " V ",
    "D": " D ",
    "I": " I ",
    "W": " W ",
    "E": " E ",
    "F": " F ",
}

NO_COLOR: re.Pattern = re.compile(r"\033\[.*?m")
BACKTRACE_LINE: re.Pattern = re.compile(r"^#(.*?)pc\s(.*?)$")
NATIVE_TAGS_LINE: re.Pattern = re.compile(r".*nativeGetEnabledTags.*")
LOG_LINE: re.Pattern = re.compile(r"^([A-Z])/(.+?)\( *(\d+)\): (.*?)$")
PID_KILL: re.Pattern = re.compile(r"^Killing (\d+):([a-zA-Z0-9._:]+)/[^:]+: (.*)$")
PID_LEAVE: re.Pattern = re.compile(
    r"^No longer want ([a-zA-Z0-9._:]+) \(pid (\d+)\): .*$"
)
PID_DEATH: re.Pattern = re.compile(
    r"^Process ([a-zA-Z0-9._:]+) \(pid (\d+)\) has died.?$"
)
PID_LINE: re.Pattern = re.compile(
    r"^\w+\s+(\w+)\s+\w+\s+\w+\s+\w+\s+\w+\s+\w+\s+\w\s([\w|\.|\/]+)$"
)
PID_START_5_1: re.Pattern = re.compile(
    r"^.*: Start proc (\d+):([a-zA-Z0-9._:]+)/[a-z0-9]+ for (.*)$"
)
PID_START: re.Pattern = re.compile(
    r"^.*: Start proc ([a-zA-Z0-9._:]+) for ([a-z]+ [^:]+): pid=(\d+) uid=(\d+) gids=(.*)$"
)
PID_START_DALVIK: re.Pattern = re.compile(
    r"^E/dalvikvm\(\s*(\d+)\): >>>>> ([a-zA-Z0-9._:]+) \[ userId:0 \| appId:(\d+) \]$"
)


def Termcolor(
    foreground: Optional[int] = None, background: Optional[int] = None
) -> str:
    """Returns the ANSI escape code for terminal color."""

    codes: List[str] = []

    if foreground is not None:
        codes.append("3%d" % foreground)

    if background is not None:
        codes.append("10%d" % background)

    return "\033[%sm" % ";".join(codes) if codes else ""


def Colorize(
    message: str, foreground: Optional[int] = None, background: Optional[int] = None
) -> str:
    """Wraps a message with ANSI color codes."""

    return Termcolor(foreground, background) + message + RESET


def EnableVt100() -> None:
    """Enables VT100 escape codes on Windows 10/11 console."""

    STD_OUTPUT_HANDLE: int = -11
    ENABLE_VIRTUAL_TERMINAL_PROCESSING: int = 4

    stdout = windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
    if stdout == -1:
        raise WinError()

    mode = c_uint()
    if windll.kernel32.GetConsoleMode(stdout, byref(mode)) == 0:
        raise WinError()

    mode.value = mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING

    if windll.kernel32.SetConsoleMode(stdout, mode) == 0:
        raise WinError()


def ConfigureConsole(args: argparse.Namespace) -> bool:
    """Determine color usage and enable VT100 on Windows if needed."""

    winVer: str = win32_ver()[0]
    showColors: bool = (
        winVer == "10" or winVer == "11" or winVer == ""
    ) and sys.stdout.isatty()

    if args.no_color:
        showColors = False

    if showColors and (winVer == "10" or winVer == "11"):
        try:
            EnableVt100()
        except Exception as ex:
            sys.stderr.write(f"Warning: Could not enable VT100 on Windows: {ex}\n")
            showColors = False  # Fallback if enablement fails

    return showColors


def GetConsoleWidth() -> int:
    """Return the current terminal width, or -1 if it cannot be determined."""

    try:
        # Works on all platforms (Python 3.3+)
        width: int = shutil.get_terminal_size(fallback=(80, 20)).columns

        return width
    except Exception as ex:
        sys.stderr.write(f"Warning: Could not get terminal width: {ex}\n")

        return -1


def IndentWrap(message: str, width: int, headerSize: int) -> str:
    """Wraps and indents long log messages."""

    if width == -1:
        return message

    message = message.replace("\t", "    ")
    wrapArea: int = width - headerSize
    messageBuffer: str = ""
    current: int = 0

    while current < len(message):
        nextIndex: int = min(current + wrapArea, len(message))
        messageBuffer += message[current:nextIndex]

        if nextIndex < len(message):
            messageBuffer += "\n"
            messageBuffer += " " * headerSize

        current = nextIndex
    return messageBuffer


def AllocateColor(tag: str) -> int:
    """Allocates a unique color for a tag based on LRU."""

    global KNOWN_TAGS, LAST_USED

    if tag not in KNOWN_TAGS:
        KNOWN_TAGS[tag] = LAST_USED[0]

    color: int = KNOWN_TAGS[tag]

    if color in LAST_USED:
        LAST_USED.remove(color)
        LAST_USED.append(color)

    return color


def TagInTagsRegex(tag: str, tags: List[str]) -> bool:
    """Checks if a tag matches any of the given tag regex patterns."""

    for t in map(str.strip, tags):
        # If the pattern contains regex special chars, treat as regex
        if any(c in t for c in r".*+?[]{}()|\^$"):
            if re.match(rf"{t}", tag):
                return True
        else:
            # Otherwise, do substring matching (contains)
            if t in tag:
                return True

    return False


def GetAdbCommand(args: argparse.Namespace) -> List[str]:
    """Constructs the base adb command list."""

    baseAdbCommand: List[str] = ["adb"]

    if args.device_serial:
        baseAdbCommand.extend(["-s", args.device_serial])

    if args.use_device:
        baseAdbCommand.append("-d")

    if args.use_emulator:
        baseAdbCommand.append("-e")

    return baseAdbCommand


def GetCurrentAppPackage(baseAdbCommand: List[str]) -> Optional[str]:
    """Gets the package name of the currently running app."""

    try:
        systemDumpCommand: List[str] = baseAdbCommand + [
            "shell",
            "dumpsys",
            "activity",
            "activities",
        ]

        systemDump: str = (
            subprocess.Popen(systemDumpCommand, stdout=PIPE, stderr=PIPE)
            .communicate()[0]
            .decode("utf-8", "replace")
        )

        match: Optional[re.Match[str]] = re.search(
            ".*TaskRecord.*A[= ]([^ ^}]*)", systemDump
        )

        return match.group(1) if match else None
    except Exception as ex:
        sys.stderr.write(f"Error getting current app package: {ex}\n")

        return None


def GetInitialPidsMap(
    baseAdbCommand: List[str], catchallPackage: List[str], args: argparse.Namespace
) -> Dict[str, str]:
    """Populates initial PIDs map {PID: PackageName} for catch-all packages or all processes if args.all is True."""

    pidsMap: Dict[str, str] = {}
    psCommand: List[str] = baseAdbCommand + ["shell", "ps"]

    try:
        psPid: Popen[bytes] = subprocess.Popen(
            psCommand, stdin=PIPE, stdout=PIPE, stderr=PIPE
        )
        psStdout: IO[bytes] | None = psPid.stdout

        while True and psStdout:
            line: str = psStdout.readline().decode("utf-8", "replace").strip()

            if not line:
                break

            pidMatch: Optional[re.Match[str]] = PID_LINE.match(line)

            if pidMatch is not None:
                pid: str = pidMatch.group(1)
                proc: str = pidMatch.group(2)

                isTargetPackage: bool = proc in catchallPackage

                # If not using -a, only add targeted packages
                if not args.all and not isTargetPackage:
                    continue

                # Simple filter for system/kernel processes when args.all is used
                if args.all and proc.startswith("/system"):
                    continue

                pidsMap[pid] = proc  # Store {PID: PackageName}
    except Exception as ex:
        sys.stderr.write(f"Warning: Could not get initial PIDs: {ex}\n")

    return pidsMap


def MatchPackages(
    token: str, namedProcesses: List[str], catchallPackage: List[str]
) -> bool:
    """Checks if a process token matches any of the package filters."""

    if not catchallPackage and not namedProcesses:
        return True  # No filter specified

    if token in namedProcesses:
        return True

    index: int = token.find(":")

    return (
        (token in catchallPackage)
        if index == -1
        else (token[:index] in catchallPackage)
    )


def ParseDeath(
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
        match: Optional[re.Match[str]] = regex.match(message)

        if match:
            # PID_KILL/PID_LEAVE/PID_DEATH have different group indices
            if regex == PID_KILL:
                pid: str = match.group(1)
                packageLine: str = match.group(2)
            elif regex == PID_LEAVE:
                pid = match.group(2)
                packageLine = match.group(1)
            else:  # PID_DEATH
                pid = match.group(2)
                packageLine = match.group(1)

            if (
                MatchPackages(packageLine, namedProcesses, catchallPackage)
                and pid in pidsSet
            ):
                return pid, packageLine

    return None, None


def ParseStartProc(line: str) -> Optional[Tuple[str, str, str, str, str]]:
    """Parses log lines for process start."""

    for regex in (PID_START_5_1, PID_START, PID_START_DALVIK):
        match: Optional[re.Match[str]] = regex.match(line)

        if match:
            if regex == PID_START_5_1:
                linePid: str
                linePackage: str
                target: str
                linePid, linePackage, target = match.groups()

                return linePackage, target, linePid, "", ""
            elif regex == PID_START:
                linePackage, target, linePid, lineUid, lineGids = match.groups()

                return linePackage, target, linePid, lineUid, lineGids
            else:  # PID_START_DALVIK
                linePid, linePackage, lineUid = match.groups()

                return linePackage, "", linePid, lineUid, ""

    return None


def CreateArgParser() -> argparse.ArgumentParser:
    """Creates and returns the ArgumentParser instance."""

    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Filter logcat by package name and colorize output."
    )
    parser.add_argument("package", nargs="*", help="Application package name(s)")
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version="%(prog)s " + __version__,
        help="Print the version number and exit",
    )
    parser.add_argument(
        "-m",
        "--tag-width",
        metavar="M",
        dest="tag_width",
        type=int,
        default=20,
        help="Width of log tag",
    )
    parser.add_argument(
        "-n",
        "--package-width",
        metavar="N",
        dest="package_width",
        type=int,
        default=20,  # Defaulting to the old fixed width
        help="Width of package/process name column.",
    )
    parser.add_argument(
        "-l",
        "--min-level",
        dest="min_level",
        type=str,
        choices=LOG_LEVELS + LOG_LEVELS.lower(),
        default="V",
        help="Minimum level to be displayed",
    )
    parser.add_argument(
        "-p",
        "--show-package",
        dest="show_package",
        action="store_true",
        default=False,
        help="Show package/process name of each log message.",
    )
    parser.add_argument(
        "-s",
        "--serial",
        dest="device_serial",
        help="Device serial number (adb -s option)",
    )
    parser.add_argument(
        "-d",
        "--device",
        dest="use_device",
        action="store_true",
        help="Use first device for log input (adb -d option)",
    )
    parser.add_argument(
        "-e",
        "--emulator",
        dest="use_emulator",
        action="store_true",
        help="Use first emulator for log input (adb -e option)",
    )
    parser.add_argument(
        "-k",
        "--keep",
        dest="keep_logcat",
        action="store_true",
        default=False,
        help="Keep the entire log before running",
    )
    parser.add_argument(
        "-t",
        "--tag",
        metavar="TAG",
        dest="tag",
        action="append",
        help="Filter output by specified tag(s)",
    )
    parser.add_argument(
        "-i",
        "--ignore-tag",
        metavar="IGNORED_TAG",
        dest="ignored_tag",
        action="append",
        help="Filter output by ignoring specified tag(s)",
    )
    parser.add_argument(
        "-a",
        "--all",
        dest="all",
        action="store_true",
        # default=True,
        help="Print all log messages (disables package filter)",
    )
    parser.add_argument(
        "-o", "--output", dest="output", type=str, default="", help="Output filename"
    )
    parser.add_argument(
        "-r",
        "--regex",
        dest="regex",
        type=str,
        help="Print only when matches REGEX (passed to logcat -e REGEX)",
    )
    parser.add_argument(
        "--color-gc",
        dest="color_gc",
        action="store_true",
        help="Color garbage collection",
    )
    parser.add_argument(
        "--no-color", dest="no_color", action="store_true", help="Disable colors"
    )
    parser.add_argument(
        "--always-display-tags",
        dest="always_tags",
        action="store_true",
        help="Always display the tag name",
    )
    parser.add_argument(
        "--current",
        dest="current_app",
        action="store_true",
        help="Filter logcat by current running app",
    )

    return parser


def ProcessLogLine(
    line: str,
    state: Dict[str, Any],
    args: argparse.Namespace,
    colorConfig: Dict[str, Any],
) -> None:
    """Handles the processing and output of a single log line."""

    pidsMap: Dict[str, str] = state["pids_map"]
    lastTag: Optional[str] = state["last_tag"]
    appPid: Optional[str] = state["app_pid"]
    minLevel: int = state["min_level"]
    width: int = colorConfig["width"]
    showColors: bool = colorConfig["show_colors"]
    outputFile: Optional[TextIO] = colorConfig["output_file"]
    namedProcesses: List[str] = state["named_processes"]
    catchallPackage: List[str] = state["catchall_package"]
    packageWidth: int = args.package_width
    tagWidth: int = args.tag_width

    def WriteOutput(outputLine: str) -> None:
        lineNoColor: str = NO_COLOR.sub("", outputLine)

        print(outputLine if showColors else lineNoColor)

        if outputFile:
            outputFile.write(lineNoColor + "\n")

    nativeTags: Optional[re.Match[str]] = NATIVE_TAGS_LINE.match(line)
    if nativeTags:
        return

    logLine: Optional[re.Match[str]] = LOG_LINE.match(line)
    if not logLine:
        return

    level, tag, owner, message = logLine.groups()
    tag = tag.strip()
    start: Optional[Tuple[str, str, str, str, str]] = ParseStartProc(line)

    # Calculate current base header size (level + spaces)
    baseLevelSize: int = 3 + 1  # Level width + space

    # Process Start/Death events
    if start:
        linePackage, target, linePid, lineUid, lineGids = start
        if MatchPackages(linePackage, namedProcesses, catchallPackage):
            pidsMap[linePid] = linePackage
            appPid = linePid

            # Recalculate header size for process start/end messages
            currentHeaderSize: int = (
                (packageWidth + 2 if args.show_package else 0)
                + args.tag_width
                + baseLevelSize
            )

            lineBuffer: str = "\n"
            lineBuffer += Colorize(" " * (currentHeaderSize - 1), background=WHITE)
            lineBuffer += IndentWrap(
                " Process %s created for %s\n" % (linePackage, target),
                width,
                currentHeaderSize,
            )
            lineBuffer += Colorize(" " * (currentHeaderSize - 1), background=WHITE)
            lineBuffer += " PID: %s   UID: %s   GIDs: %s" % (linePid, lineUid, lineGids)
            lineBuffer += "\n"

            WriteOutput(lineBuffer)
            lastTag = None

    deadPid, deadPname = ParseDeath(
        tag, message, set(pidsMap.keys()), namedProcesses, catchallPackage
    )
    if deadPid:
        if deadPid in pidsMap:
            del pidsMap[deadPid]

        currentHeaderSize = (
            (packageWidth + 2 if args.show_package else 0)
            + args.tag_width
            + baseLevelSize
        )

        lineBuffer = "\n"
        lineBuffer += Colorize(" " * (currentHeaderSize - 1), background=RED)
        lineBuffer += " Process %s (PID: %s) ended" % (deadPname, deadPid)
        lineBuffer += "\n"

        WriteOutput(lineBuffer)
        lastTag = None

    # Filter logs
    if not args.all and owner not in pidsMap:
        return

    if level in LOG_LEVELS_MAP and LOG_LEVELS_MAP[level] < minLevel:
        return

    if args.ignored_tag and TagInTagsRegex(tag, args.ignored_tag):
        return

    if args.tag and not TagInTagsRegex(tag, args.tag):
        return

    # Handle Backtrace for native crashes
    if tag == "DEBUG":
        btLine: Optional[re.Match[str]] = BACKTRACE_LINE.match(message.lstrip())
        if btLine is not None:
            message = message.lstrip()
            owner = appPid  # Associate backtrace with the app PID

    lineBuffer = ""
    currentHeaderSize = 0

    # --- PACKAGE NAME SECTION ---
    if args.show_package and owner:
        packageName: str = pidsMap.get(owner, "UNKNOWN")
        pkgColor: int = AllocateColor(packageName)

        if len(packageName) > packageWidth:
            packageName = f"{packageName[: packageWidth - 3]}..."
        pkgDisplay: str = packageName.ljust(packageWidth)

        lineBuffer += Colorize(pkgDisplay, pkgColor)
        lineBuffer += "  "  # Two spaces separator
        currentHeaderSize += packageWidth + 2
    # ----------------------------

    # --- TAG SECTION ---
    if args.tag_width > 0:
        if tag != lastTag or args.always_tags:
            lastTag = tag
            color: int = AllocateColor(tag)

            if len(tag) > tagWidth:
                tag = f"{tag[: tagWidth - 3]}..."
            tag = tag.rjust(tagWidth) if args.show_package else tag.ljust(tagWidth)

            lineBuffer += Colorize(tag, color)
        else:
            lineBuffer += " " * tagWidth

        lineBuffer += " "
        currentHeaderSize += tagWidth + 1
    # ----------------------------

    # --- LEVEL SECTION ---
    levelStr: str = TAGTYPES.get(level, " " + level + " ")
    if showColors:
        foreground: int = {
            "V": WHITE,
            "D": BLACK,
            "I": BLACK,
            "W": BLACK,
            "E": BLACK,
            "F": BLACK,
        }.get(level, WHITE)

        background: int = {
            "V": BLACK,
            "D": BLUE,
            "I": GREEN,
            "W": YELLOW,
            "E": RED,
            "F": RED,
        }.get(level, BLACK)

        lineBuffer += Colorize(levelStr, foreground, background)
    else:
        lineBuffer += levelStr

    lineBuffer += " "
    currentHeaderSize += baseLevelSize  # Level width + space
    # ----------------------------

    # --- MESSAGE SECTION --- (apply rules)
    messageRules: Dict[re.Pattern, str] = {}
    # StrictMode rule
    messageRules[
        re.compile(r"^(StrictMode policy violation)(; ~duration=)(\d+ ms)")
    ] = r"\1%s\2%s\3%s" % (Termcolor(RED), Termcolor(YELLOW), RESET)
    # GC coloring rule

    if args.color_gc:
        messageRules[
            re.compile(
                r"^(GC_(?:CONCURRENT|FOR_M?ALLOC|EXTERNAL_ALLOC|EXPLICIT) )(freed <?\d+.)(, \d+\% free \d+./\d+., )(paused \d+ms(?:\+\d+ms)?)"
            )
        ] = r"\1%s\2%s\3%s\4%s" % (Termcolor(GREEN), RESET, Termcolor(YELLOW), RESET)

    for matcher in messageRules:
        message = matcher.sub(messageRules[matcher], message)

    lineBuffer += IndentWrap(message, width, currentHeaderSize)
    WriteOutput(lineBuffer)
    # ----------------------------

    # Update state for next line
    state["last_tag"] = lastTag
    state["app_pid"] = appPid


def main() -> None:
    """The main entry point of the script."""
    parser: argparse.ArgumentParser = CreateArgParser()
    args: argparse.Namespace = parser.parse_args()

    if args.tag:
        args.tag = [tag.strip() for tag_arg in args.tag for tag in tag_arg.split(",")]

    if args.ignored_tag:
        args.ignored_tag = [
            tag.strip() for tag_arg in args.ignored_tag for tag in tag_arg.split(",")
        ]

    showColors: bool = ConfigureConsole(args)
    minLevel: int = LOG_LEVELS_MAP[args.min_level.upper()]
    width: int = GetConsoleWidth()
    outputFile: Optional[TextIO] = None

    try:
        if args.output:
            outputFile = open(args.output, "a+")

        baseAdbCommand: List[str] = GetAdbCommand(args)
        packages: List[str] = list(args.package)

        if args.current_app:
            runningPackage: Optional[str] = GetCurrentAppPackage(baseAdbCommand)
            if runningPackage:
                packages.append(runningPackage)

        # Determine exact processes vs. catch-all packages
        catchallPackage: List[str] = list(filter(lambda p: p.find(":") == -1, packages))
        namedProcesses: List[str] = list(filter(lambda p: p.find(":") != -1, packages))
        namedProcesses = list(
            map(lambda p: p[:-1] if p.endswith(":") else p, namedProcesses)
        )

        if not packages:
            args.all = True

        pidsMap: Dict[str, str] = GetInitialPidsMap(
            baseAdbCommand, catchallPackage, args
        )

        adbCommand: List[str] = baseAdbCommand + ["logcat", "-v", "brief"]
        if args.regex:
            adbCommand.extend(["-e", args.regex])

        if not args.keep_logcat:
            adbClearCommand: List[str] = baseAdbCommand + ["logcat", "-c"]
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

        state: Dict[str, Any] = {
            "pids_map": pidsMap,
            "last_tag": None,
            "app_pid": None,
            "min_level": minLevel,
            "named_processes": namedProcesses,
            "catchall_package": catchallPackage,
        }

        colorConfig: Dict[str, Any] = {
            "width": width,
            "show_colors": showColors,
            "output_file": outputFile,
        }

        if packages:
            print(
                f"listening for logcat messages from packages: {', '.join(packages)}..."
            )
        else:
            print("listening for logcat messages...")

        try:
            while adb.poll() is None and logStream:
                rawLine = logStream.readline()
                if not rawLine:
                    break

                # Check if the stream is binary (like Popen stdout), which returns bytes
                if isinstance(rawLine, bytes):
                    line: str = rawLine.decode("utf-8", "replace").strip()
                # Otherwise, assume it's a text stream (like sys.stdin), which returns str
                else:
                    line: str = str(rawLine).strip()

                # Update the console width if it has changed
                colorConfig["width"] = GetConsoleWidth()
                ProcessLogLine(line, state, args, colorConfig)
        except KeyboardInterrupt:
            sys.stderr.write("\nLogcat monitoring stopped by user.\n")
        except Exception as ex:
            sys.stderr.write(f"\nAn error occurred during log processing: {ex}\n")

    finally:
        # Cleanup
        if outputFile:
            outputFile.close()


if __name__ == "__main__":
    main()
