import re
import sys
import shutil
import argparse

from pathlib import Path

from controller.writer import Writer
from controller.file_writer import FileWriter
from controller.console_writer import ConsoleWriter

from model.state import State
from model.cli_args import CliArgs
from model.mock_tty import MockTTY
from model.adb_device import AdbDevice
from model.adb_state import AdbState
from utils.colored import Color, ColoredString

from subprocess import PIPE, CompletedProcess
from subprocess import run as processRun
from subprocess import Popen as ProcessOpen

from result import Result, Ok, Err

from typing import Set
from typing import List
from typing import Dict
from typing import Tuple
from typing import Optional


VERSION = "2.6.1"

LOG_LEVELS = "VDIWEF"
LOG_LEVELS_MAP = {level: index for index, level in enumerate(LOG_LEVELS)}

TAG_COLORS = [
    Color.BrightRed,
    Color.BrightBlue,
    Color.BrightCyan,
    Color.BrightGreen,
    Color.BrightYellow,
    Color.BrightMagenta,
]

KNOWN_TAGS = dict[str, Color]()

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
    r"ViewRootImplExtImpl",
    r"BufferQueueConsumer",
    r"BufferQueueProducer",
    r"OplusCursorFeedback",
    r"ViewRootImplExtImpl",
    r"FirebaseInitProvider",
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
STRICT_MODE = re.compile(r"^(StrictMode policy violation)(; ~duration=)(\d+ ms)")
GC_COLOR = re.compile(
    r"^(GC_(?:CONCURRENT|FOR_M?ALLOC|EXTERNAL_ALLOC|EXPLICIT) )(freed <?\d+.)(, \d+\% free \d+./\d+., )(paused \d+ms(?:\+\d+ms)?)"
)
VISIBLE_ACTIVITIES = re.compile(
    r"VisibleActivityProcess:\[\s*(?:(?:ProcessRecord\{\w+\s*\d+:(?:[a-zA-Z.]+)/\w+\})\s*)+\]"
)
VISIBLE_PACKAGES = re.compile(r"ProcessRecord\{\w+\s*\d+:([a-zA-Z.]+)/\w+\}")


def get_version(name: str) -> str:
    return f"{name} v{VERSION}"


def get_arg_parser() -> argparse.ArgumentParser:
    """Creates and returns the ArgumentParser instance."""

    prog_name = Path(sys.argv[0]).stem
    version_name = get_version(prog_name)

    parser = argparse.ArgumentParser(
        add_help=False,
        prog=prog_name,
        description=f"{version_name}\nA colorized Android logcat viewer with advanced filtering capabilities.",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    positional_arguments = parser.add_argument_group(title="Positional Arguments")
    about_options = parser.add_argument_group(title="Options")
    devices_options = parser.add_argument_group(title="Device Options")
    filtering_options = parser.add_argument_group(title="Filtering Options")
    formatting_options = parser.add_argument_group(title="Formatting Options")
    color_options = parser.add_argument_group(title="Color Options")
    output_options = parser.add_argument_group(title="Output Options")

    positional_arguments.add_argument(
        metavar="package(s)",
        dest="package",
        nargs="*",
        help="Application package name(s)\nThis can be specified multiple times",
    )

    about_options.add_argument(
        "-h",
        "--help",
        action="help",
        default=argparse.SUPPRESS,
        help="Show this help message and exit.",
    )

    about_options.add_argument(
        "-v",
        "--version",
        action="version",
        version=version_name,
        help="Print the version number and exit",
    )

    devices_options.add_argument(
        "-d",
        "--device",
        dest="use_device",
        action="store_true",
        default=False,
        help="Use first device for log input, default: %(default)s",
    )

    devices_options.add_argument(
        "-e",
        "--emulator",
        dest="use_emulator",
        action="store_true",
        default=False,
        help="Use first emulator for log input, default: %(default)s",
    )

    devices_options.add_argument(
        "-s",
        "--serial",
        metavar="DEVICE_SERIAL",
        dest="device_serial",
        help="Device serial number",
    )

    filtering_options.add_argument(
        "-a",
        "--all",
        dest="all",
        action="store_true",
        default=False,
        help="Print log messages from all packages, default: %(default)s",
    )

    filtering_options.add_argument(
        "-k",
        "--keep",
        dest="keep_logcat",
        action="store_true",
        default=False,
        help="Keep the entire log before running, default: %(default)s",
    )

    filtering_options.add_argument(
        "-c",
        "--current",
        dest="current_app",
        action="store_true",
        default=False,
        help="Filter logcat by current running app(s), default: %(default)s",
    )

    filtering_options.add_argument(
        "-I",
        "--ignore-system-tags",
        dest="ignore_system_tags",
        action="store_true",
        default=False,
        help="Filter output by ignoring known system tags, default: %(default)s"
        "\nUse --ignore-tag to ignore additional tags if needed",
    )

    filtering_options.add_argument(
        "-t",
        "--tag",
        metavar="TAG",
        dest="tag",
        action="append",
        help="Filter output by specified tag(s)\nThis can be specified multiple times, or as a comma separated list",
    )

    filtering_options.add_argument(
        "-i",
        "--ignore-tag",
        metavar="IGNORED_TAG",
        dest="ignore_tag",
        action="append",
        help="Filter output by ignoring specified tag(s)\n"
        "This can be specified multiple times, or as a comma separated list",
    )

    filtering_options.add_argument(
        "-l",
        "--log-level",
        dest="log_level",
        metavar=f"LEVEL [{'|'.join(LOG_LEVELS + LOG_LEVELS.lower())}]",
        type=str,
        choices=LOG_LEVELS + LOG_LEVELS.lower(),
        default="V",
        help="Filter messages lower than minimum log level, default: %(default)s",
    )

    filtering_options.add_argument(
        "-r",
        "--regex",
        metavar="REGEX",
        dest="regex",
        type=str,
        help="Filter output messages using the specified %(metavar)s",
    )

    formatting_options.add_argument(
        "-P",
        "--show-pid",
        dest="show_pid",
        action="store_true",
        default=False,
        help="Show package name in output, default: %(default)s",
    )

    formatting_options.add_argument(
        "-p",
        "--show-package",
        dest="show_package",
        action="store_true",
        default=False,
        help="Show package name in output, default: %(default)s",
    )

    formatting_options.add_argument(
        "-S",
        "--always-show-tags",
        dest="always_show_tags",
        action="store_true",
        default=False,
        help="Always show the tag name, default: %(default)s",
    )

    formatting_options.add_argument(
        "-x",
        "--pid-width",
        metavar="WIDTH",
        dest="pid_width",
        type=int,
        default=5,
        help="Width of PID column, default: %(default)s",
    )

    formatting_options.add_argument(
        "-n",
        "--package-width",
        metavar="WIDTH",
        dest="package_width",
        type=int,
        default=20,
        help="Width of package/process name column, default: %(default)s",
    )

    formatting_options.add_argument(
        "-m",
        "--tag-width",
        metavar="WIDTH",
        dest="tag_width",
        type=int,
        default=20,
        help="Width of tag column, default: %(default)s",
    )

    color_options.add_argument(
        "-g",
        "--gc-color",
        dest="gc_color",
        action="store_true",
        default=False,
        help="Enable garbage collector messages colors, default: %(default)s",
    )

    color_options.add_argument(
        "-N",
        "--no-color",
        dest="no_color",
        action="store_true",
        default=False,
        help="Disable message colors, default: %(default)s",
    )

    output_options.add_argument(
        "-o",
        "--output",
        metavar="FILE_PATH",
        dest="output_path",
        type=str,
        default="",
        help="Output filename",
    )

    return parser


def get_console_width() -> int:
    """Return the current terminal width"""

    width = shutil.get_terminal_size(fallback=(80, 20)).columns

    return width


def get_wrapped_indent(
    message: str | ColoredString,
    width: Optional[int],
    header_size: int,
    show_colors: bool,
    foreground: Optional[Color],
    background: Optional[Color],
) -> str | ColoredString:
    """Wraps and indents long log messages."""

    if not width:
        return message

    message = message.replace("\t", "   ")
    wrap_area = width - header_size
    message_buffer = ""
    current = 0

    while current < len(message):
        next_index = min(current + wrap_area, len(message))
        message_buffer += message[current:next_index]

        if next_index < len(message):
            future_index = next_index + wrap_area
            is_last_line = future_index >= len(message)
            message_buffer += "\n"
            message_buffer += " " * (header_size - 5)

            connector = "    " if foreground == background else " ╠═" if not is_last_line else " ╚═"

            if show_colors:
                colored_connector = ColoredString(connector)

                if foreground:
                    colored_connector = colored_connector.color(foreground)

                if background:
                    colored_connector = colored_connector.onColor(background)

                message_buffer += colored_connector
            else:
                message_buffer += connector
            message_buffer += " "
        current = next_index

    return message_buffer


def get_token_color(token: str) -> Color:
    """Allocates a unique color for a tag based on LRU."""

    if token not in KNOWN_TAGS:
        if TAG_COLORS:
            KNOWN_TAGS[token] = TAG_COLORS[0]
        else:
            return Color.White

    color = KNOWN_TAGS[token]

    if color in TAG_COLORS:
        TAG_COLORS.remove(color)
        TAG_COLORS.append(color)

    return color


def get_adb_command(args: CliArgs) -> List[str]:
    """Constructs the base adb command list."""

    base_adb_command = ["adb"]

    if args.device_serial:
        base_adb_command.extend(["-s", args.device_serial])

    if args.use_device:
        base_adb_command.append("-d")

    if args.use_emulator:
        base_adb_command.append("-e")

    return base_adb_command


def start_adb_server(base_adb_command: List[str]) -> Result[None, CompletedProcess[str]]:
    start_server_command = base_adb_command + list[str](["start-server"])
    result = processRun(start_server_command, stdout=PIPE, stderr=PIPE, text=True, errors="replace")

    if result.returncode != 0:
        return Err(result)

    output = result.stdout if result.stdout else result.stderr
    stdout = "\n".join([line for line in output.splitlines() if line])

    if stdout:
        message = ColoredString(stdout).color(Color.BrightCyan)
        print(message)

    return Ok(None)


def get_adb_devices(base_adb_command: List[str]) -> Optional[List[AdbDevice]]:
    devices_list_command = base_adb_command + list[str](["devices"])
    result = processRun(devices_list_command, stdout=PIPE, stderr=PIPE, text=True, errors="replace")

    if result.returncode != 0:
        return None
    regex = re.compile(r"\s+")
    output = result.stdout if result.stdout else result.stderr
    stdout = "\n".join([line for line in output.splitlines() if line])
    stdout = stdout.splitlines()[1:]

    adb_devices = list[AdbDevice]()
    for line in stdout:
        device_id_str, device_state_str = regex.split(line)
        adb_devices.append(AdbDevice(device_id_str, AdbState.fromStr(device_state_str)))

    if adb_devices:
        return adb_devices

    return None


def get_current_app_package(base_adb_command: List[str]) -> Optional[List[str]]:
    """Gets the package name of the currently running app."""

    system_dump_command = base_adb_command + [
        "shell",
        "dumpsys",
        "activity",
        "activities",
    ]

    system_dump = processRun(system_dump_command, stdout=PIPE, stderr=PIPE, text=True, errors="replace").stdout

    visible_activities = re.search(VISIBLE_ACTIVITIES, system_dump)

    if not visible_activities:
        return None

    visible_packages = re.findall(VISIBLE_PACKAGES, visible_activities.group())

    return visible_packages if visible_packages else None


def get_processes(base_adb_command: List[str], catchall_packages: List[str], args: CliArgs) -> Dict[str, str]:
    """Populates initial PIDs map {PID: PackageName} for catch-all packages or all processes if args.all is True."""

    pids_map = dict[str, str]()
    ps_command = base_adb_command + ["shell", "ps"]

    ps_pid = ProcessOpen(ps_command, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    ps_stdout = ps_pid.stdout

    while True and ps_stdout:
        line = ps_stdout.readline().decode("utf-8", "replace").strip()

        if not line:
            break

        if (pid_match := PID_LINE.match(line)) is not None:
            pid = pid_match.group(1)
            process = pid_match.group(2)

            is_target_package = process in catchall_packages

            # If not using -a, only add targeted packages
            if args.all or is_target_package:
                pids_map[pid] = process

    return pids_map


def get_dead_processes(
    tag: str,
    message: str,
    pids_set: Set[str],
    named_processes: List[str],
    catchall_packages: List[str],
) -> Tuple[Optional[str], Optional[str]]:
    """Parses log lines for process death and removal."""

    if tag != "ActivityManager":
        return None, None

    for regex in (PID_KILL, PID_LEAVE, PID_DEATH):
        if match := regex.match(message):
            # PID_KILL/PID_LEAVE/PID_DEATH have different group indices
            if regex == PID_KILL:
                pid = match.group(1)
                package_line = match.group(2)
            elif regex == PID_LEAVE:
                pid = match.group(2)
                package_line = match.group(1)
            else:  # PID_DEATH
                pid = match.group(2)
                package_line = match.group(1)

            is_a_matching_package = is_matching_package(
                package_line,
                named_processes,
                catchall_packages,
            )
            if is_a_matching_package and pid in pids_set:
                return pid, package_line

    return None, None


def get_started_processes(line: str) -> Optional[Tuple[str, str, str, str, str]]:
    """Parses log lines for process start."""

    for regex in (PID_START, PID_START_UGID, PID_START_DALVIK):
        if match := regex.match(line):
            if regex == PID_START:
                started_package = ""
                started_pid = ""
                started_pid, started_package, started_target = match.groups()

                return started_pid, "", "", started_package, started_target
            elif regex == PID_START_UGID:
                (
                    started_package,
                    started_target,
                    started_pid,
                    started_uid,
                    started_gids,
                ) = match.groups()

                return started_pid, started_uid, started_gids, started_package, started_target
            else:  # PID_START_DALVIK
                started_pid, started_package, started_uid = match.groups()

                return started_pid, started_uid, "", started_package, ""

    return None


def write_log_line(line: str, state: State, args: CliArgs, writers: List[Writer]) -> None:
    """Handles the processing and output of a single log line."""

    pids_map = state.pids_map
    last_tag = state.last_tag
    app_pid = state.app_pid
    log_level = state.log_level
    named_processes = state.named_processes
    catchall_packages = state.catchall_packages
    pid_width = args.pid_width
    package_width = args.package_width
    tag_width = args.tag_width
    header_width = 0

    writer_buffers = [""] * len(writers)

    def write_token(
        message: str | ColoredString,
        wrap: bool = False,
        foreground: Optional[Color] = None,
        background: Optional[Color] = None,
    ) -> None:
        for index, writer in enumerate(writers):
            if wrap and writer.width:
                buffer = get_wrapped_indent(
                    message,
                    writer.width,
                    header_width,
                    writer.show_colors,
                    foreground,
                    background,
                )
            else:
                buffer = message

            if isinstance(buffer, ColoredString) and not writer.show_colors:
                buffer = buffer.raw

            writer_buffers[index] += buffer

    if NATIVE_TAGS_LINE.match(line):
        return

    if not (logLine := LOG_LINE.match(line)):
        return

    level, tag, owner, message = logLine.groups()
    tag = tag.strip()

    # Calculate current base header size (level + spaces)
    base_header_width = 3 + 1 + 1  # level width + 2 spaces between pid and package name and package name and tag name

    if args.show_pid:
        header_width += pid_width

    if args.show_package:
        header_width += package_width

    header_width += 2 + tag_width + base_header_width
                                                
    # Process Start/Death events
    if started_process := get_started_processes(line):
        started_pid, started_uid, started_gids, started_package, started_target = started_process
        if is_matching_package(started_package, named_processes, catchall_packages):
            pids_map[started_pid] = started_package
            app_pid = started_pid

            # Recalculate header size for process start/end messages
            header_width = (package_width + 7 if args.show_package else 0) + args.tag_width + base_header_width

            write_token(ColoredString(" " * (header_width - 1)).color(Color.BrightGreen).onColor(Color.BrightGreen))
            write_token(f" Process {started_package} created for {started_target}\n", wrap=True)

            write_token(ColoredString(" " * (header_width - 1)).color(Color.BrightGreen).onColor(Color.BrightGreen))
            write_token(f" PID: {started_pid}   UID: {started_uid}   GIDs: {started_gids}")
            write_token("\n")

            last_tag = None

            for index, writer in enumerate(writers):
                writer.write(writer_buffers[index])
                writer.flush()

            return

    dead_pid, dead_process_name = get_dead_processes(
        tag,
        message,
        set(pids_map.keys()),
        named_processes,
        catchall_packages,
    )
    if dead_pid:
        if dead_pid in pids_map:
            del pids_map[dead_pid]

        header_width = (package_width + 2 if args.show_package else 0) + args.tag_width + base_header_width

        write_token(ColoredString(" " * (header_width - 1)).color(Color.BrightRed).onColor(Color.BrightRed))
        write_token(f" Process {dead_process_name} (PID: {dead_pid}) ended")

        last_tag = None

        for index, writer in enumerate(writers):
            writer.write(writer_buffers[index])
            writer.flush()

        return

    # Filter logs
    if not args.all and owner not in pids_map:
        return

    if level in LOG_LEVELS_MAP and LOG_LEVELS_MAP[level] < log_level:
        return

    if args.ignore_tag and is_matching_tag(tag, args.ignore_tag):
        return

    if args.tag and not is_matching_tag(tag, args.tag):
        return

    # Handle Backtrace for native crashes
    if tag == "DEBUG":
        backtrace_line = BACKTRACE_LINE.match(message.lstrip())
        if backtrace_line is not None:
            message = message.lstrip()
            owner = app_pid  # Associate backtrace with the app PID

    # lineBuffer = ""
    header_width = 0

    # --- OWNER PID SECTION ---
    if args.show_pid and owner:
        pid_color = get_token_color(owner)

        if len(owner) > pid_width:
            owner = f"{owner[: pid_width - 1]}…"
        pid_display = owner.ljust(pid_width)

        write_token(ColoredString(pid_display).color(pid_color))
        write_token(" ")  # one space separator
        header_width += pid_width + 1
    # ----------------------------

    # --- PACKAGE NAME SECTION ---
    if args.show_package and owner:
        package_name = pids_map.get(owner, f"UNKNOWN({owner})")
        pkg_color = get_token_color(package_name)

        if len(package_name) > package_width:
            package_name = f"{package_name[: package_width - 1]}…"
        pkg_display = package_name.ljust(package_width)

        write_token(ColoredString(pkg_display).color(pkg_color))
        write_token(" ")  # one space separator
        header_width += package_width + 1
    # ----------------------------

    # --- TAG SECTION ---
    if args.tag_width > 0:
        if tag != last_tag or args.always_show_tags:
            last_tag = tag
            tag_color = get_token_color(tag)

            if len(tag) > tag_width:
                tag = f"{tag[: tag_width - 1]}…"
            tag = tag.rjust(tag_width) if args.show_package else tag.ljust(tag_width)

            write_token(ColoredString(tag).color(tag_color))
        else:
            write_token(" " * tag_width)

        write_token(" ")  # one space separator
        header_width += tag_width + 1
    # ----------------------------

    # --- LEVEL SECTION ---
    foreground = Color.Black
    background = {
        "D": Color.BrightBlue,
        "I": Color.BrightGreen,
        "W": Color.BrightYellow,
        "E": Color.BrightRed,
        "F": Color.TrueColor(250, 65, 25),
        "V": Color.BrightCyan,
    }.get(level, Color.Black)

    level = ColoredString(f" {level} ").color(foreground).onColor(background)

    write_token(level)
    write_token(" ")  # one space separator
    # ----------------------------

    header_width += base_header_width

    # --- MESSAGE SECTION --- (apply rules)
    if match := STRICT_MODE.match(message):
        message = f"{match[1]}"
        message += f"{ColoredString(match[2]).color(Color.BrightRed)}"
        message += f"{ColoredString(match[3]).color(Color.BrightYellow)}"

    if args.gc_color and (match := GC_COLOR.match(message)):
        message = f"{match[1]}"
        message += f"{ColoredString(match[2]).color(Color.BrightGreen)}"
        message += f"{match[3]}"
        message += f"{ColoredString(match[4]).color(Color.BrightYellow)}"

    write_token(message, wrap=True, foreground=foreground, background=background)
    write_token("\n")
    header_width += 1
    for index, writer in enumerate(writers):
        writer.write(writer_buffers[index])
        writer.flush()
    # ----------------------------

    # Update state for next line
    state.last_tag = last_tag
    state.app_pid = app_pid


def is_matching_package(token: str, namedProcesses: List[str], catchallPackage: List[str]) -> bool:
    """Checks if a process token matches any of the package filters."""

    if not catchallPackage and not namedProcesses:
        return True  # No filter specified

    if token in namedProcesses:
        return True

    index = token.find(":")

    return (token in catchallPackage) if index == -1 else (token[:index] in catchallPackage)


def is_matching_tag(tag: str, tags: List[str]) -> bool:
    """Checks if a tag matches any of the given tag regex patterns."""

    for m_tag in map(str.strip, tags):
        # If the pattern contains regex special chars, treat as regex
        if any(m_char in m_tag for m_char in r".*+?[]{}()|\^$") and re.match(rf"{m_tag}", tag):
            return True

        # Otherwise, do substring matching (contains)
        elif m_tag in tag:
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
    parser = get_arg_parser()
    args = parser.parse_args()

    args = CliArgs(**vars(args))

    try:
        base_adb_command = get_adb_command(args)
        adb_command = base_adb_command + ["logcat", "-v", "brief"]
        log_level = LOG_LEVELS_MAP[args.log_level.upper()]
        console_width = get_console_width()
        console_writer = ConsoleWriter(width=console_width, show_colors=not args.no_color)
        writers = list[Writer]([console_writer])
        packages = list(set(args.package))

        if args.ignore_system_tags:
            args.ignore_tag = [f"^{systemTag.strip()}$" for systemTag in SYSTEM_TAGS]

        if args.ignore_tag:
            args.ignore_tag = [tag.strip() for tag_arg in args.ignore_tag for tag in tag_arg.split(",")]

        if args.tag:
            args.tag = [tag.strip() for tag_arg in args.tag for tag in tag_arg.split(",")]

        if args.output_path:
            output_file = open(args.output_path, "w+", encoding="utf-8")
            file_writer = FileWriter(outputFile=output_file)
            writers.append(file_writer)

        if args.current_app:
            running_packages = get_current_app_package(base_adb_command)
            packages += running_packages if running_packages else []

        if args.regex:
            adb_command.extend(["-e", args.regex])

        if sys.stdin.isatty():
            msg = ColoredString("Starting ADB Server…").color(Color.BrightCyan)
            print(msg)

            match start_adb_server(base_adb_command):
                case Err() as err:
                    err = CompletedProcess[str](**vars(err.err_value))
                    err_hdr = f"ERROR: {err.stderr.strip()}"
                    err_msg = "Could not start ADB server, check that ADB is added to env PATH and try again!"

                    print(ColoredString(err_hdr).color(Color.BrightCyan).bold(), file=sys.stderr)
                    print(ColoredString(err_msg).color(Color.BrightCyan).bold(), file=sys.stderr)
                    sys.exit(err.returncode)

            match get_adb_devices(base_adb_command):
                # TODO: implement device selection
                case [AdbDevice(), *_] as devices:
                    for index, device in enumerate(devices):
                        msg = f"Found Device #{index}: {device}"
                        print(ColoredString(msg).color(Color.BrightCyan).bold(), file=sys.stderr)
                case None:
                    err_hdr = "ERROR: not connected"
                    err_msg = "ADB cannot find any attached devices, attach a device and try again!"

                    print(ColoredString(err_hdr).color(Color.BrightCyan).bold(), file=sys.stderr)
                    print(ColoredString(err_msg).color(Color.BrightCyan).bold(), file=sys.stderr)
                    sys.exit(2)

            if not args.keep_logcat:
                adb_clear_command = base_adb_command + ["logcat", "-c"]
                processRun(adb_clear_command, check=False)

        if packages:
            msg = f"Capturing logcat messages from packages: [{', '.join(packages)}]…"
        else:
            args.all = True
            msg = "Capturing logcat messages…"

        print(ColoredString(msg).color(Color.BrightCyan))

        # Determine exact processes vs. catch-all packages
        catchall_packages = list[str](filter(lambda package: package.find(":") == -1, packages))
        named_processes = list[str](filter(lambda package: package.find(":") != -1, packages))
        named_processes = list[str](
            map(lambda package: package[:-1] if package.endswith(":") else package, named_processes)
        )
        pids_map = get_processes(base_adb_command, catchall_packages, args)

        adb_pid = ProcessOpen(adb_command, stdout=PIPE, stderr=PIPE) if sys.stdin.isatty() else MockTTY()
        log_stream = adb_pid.stdout

        state = State(pids_map, None, None, log_level, named_processes, catchall_packages)

        while adb_pid.poll() is None and log_stream:
            raw_line = log_stream.readline()

            if not raw_line:
                break

            # Check if the stream is binary (like ProcessOpen stdout), which returns bytes
            if isinstance(raw_line, bytes):
                line = raw_line.decode(encoding="utf-8", errors="replace").strip()
            # Otherwise, assume it's a text stream (like sys.stdin), which returns str
            else:
                line = str(raw_line).strip()

            # Update the writers width if changed
            # writers with width set to None are not
            # console writers and should not be updated
            for writer in filter(lambda writer: writer.width, writers):
                writer.width = get_console_width()

            write_log_line(line=line, state=state, args=args, writers=writers)

    except RuntimeError as ex:
        err = CompletedProcess[str](**vars(ex.args[0]))
        err_hdr = f"ERROR: {err.stderr.strip()}"
        err_msg = "Could not start ADB server, check that ADB is added to env PATH and try again!"

        if sys.stdin.isatty():
            print(ColoredString(err_hdr).color(Color.BrightCyan).bold(), file=sys.stderr)
            print(ColoredString(err_msg).color(Color.BrightCyan).bold(), file=sys.stderr)
            sys.exit(err.returncode)
    except KeyboardInterrupt:
        msg = f"{Path(parser.prog).stem} stopped by user!"

        print(ColoredString(msg).color(Color.BrightCyan).bold(), file=sys.stderr)
    finally:
        # Cleanup
        for writer in writers:
            writer.close()


if __name__ == "__main__":
    main()
