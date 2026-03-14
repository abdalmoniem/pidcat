import re
import sys
import shutil

from controller.writer import Writer
from controller.file_writer import FileWriter
from controller.console_writer import ConsoleWriter

from model.state import State
from model.cli_args import CliArgs
from model.mock_tty import MockTTY
from model.adb_device import AdbDevice
from model.adb_state import AdbState
from model.ansi_segment import AnsiSegment
from model.log_level import LogLevel

from utils.colored import Color
from utils.colored import ColoredString

from typing import List
from typing import Dict
from typing import Tuple
from typing import Optional

from result import Ok
from result import Err
from result import Result

from subprocess import PIPE
from subprocess import CompletedProcess
from subprocess import run as processRun
from subprocess import Popen as ProcessOpen

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

ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")
BACKTRACE_LINE = re.compile(r"^#(.*?)pc\s(.*?)$")
NATIVE_TAGS_LINE = re.compile(r".*nativeGetEnabledTags.*")
LOG_LINE = re.compile(r"^([A-Z])/(.+?)\( *(\d+)\): (.*?)$")
PID_KILL = re.compile(r"^Killing (\d+):([a-zA-Z0-9._:]+)/[^:]+: (.*)$")
PID_LEAVE = re.compile(r"^No longer want ([a-zA-Z0-9._:]+) \(pid (\d+)\): .*$")
PID_DEATH = re.compile(r"^Process ([a-zA-Z0-9._:]+) \(pid (\d+)\) has died.*$")
PID_LINE = re.compile(r"^\w+\s+(\w+)\s+\w+\s+\w+\s+\w+\s+\w+\s+\w+\s+\w\s(.*?)$")
PID_START = re.compile(r"^.*: Start proc (\d+):([a-zA-Z0-9._:]+)/[a-z0-9]+ for .*? \{(.*?)\}$")
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


def get_console_width() -> int:
    """Return the current terminal width"""

    width = shutil.get_terminal_size(fallback=(80, 20)).columns

    return width


def strip_ansi(text: str) -> str:
    return ANSI_ESCAPE.sub("", text)


def get_ansi_segments(message: str) -> list[AnsiSegment]:
    segments = list[AnsiSegment]()
    plain_pos = 0
    index = 0
    while index < len(message):
        if match := ANSI_ESCAPE.match(message, index):
            segments.append(AnsiSegment(match.group(), plain_pos))
            index = match.end()
        else:
            plain_pos += 1
            index += 1

    return segments


def get_active_codes_at_pos(segments: list[AnsiSegment], pos: int) -> list[str]:
    active = dict[str, str]()
    for seg in segments:
        if seg.visible_pos >= pos:
            break

        if (code := seg.code) == "\x1b[0m":
            active.clear()
        else:
            nums = code[2:-1].split(";")
            for num in nums:
                num = int(num) if num else 0
                if num == 0:
                    active.clear()
                elif num == 39 or num in range(30, 38) or num in range(90, 98):
                    active["fg"] = f"\x1b[{num}m"
                elif num == 49 or num in range(40, 48) or num in range(100, 108):
                    active["bg"] = f"\x1b[{num}m"
                elif num in range(1, 10):
                    active[f"attr_{num}"] = f"\x1b[{num}m"
                elif num == 38:
                    active["fg"] = code
                    break
                elif num == 48:
                    active["bg"] = code
                    break

    return list(active.values())


def insert_ansi_codes_in_range(
    segment: str,
    ansi_segments: list[AnsiSegment],
    start: int,
    end: int,
    active_codes: list[str],
) -> str:
    result = "".join(active_codes)
    char_idx = 0
    for seg in ansi_segments:
        if seg.visible_pos < start or seg.visible_pos >= end:
            continue
        relative_pos = seg.visible_pos - start
        result += segment[char_idx:relative_pos]
        result += seg.code
        char_idx = relative_pos
    result += segment[char_idx:]

    return result


def get_wrapped_indent(
    message: str,
    width: Optional[int],
    header_width: int,
    show_colors: bool,
    continuation_char: str,
    foreground: Optional[Color],
    background: Optional[Color],
) -> str:
    if not width or width == -1:
        return message

    message = message.replace("\t", "    ")
    wrap_area = width - header_width

    if wrap_area <= 0:
        return message

    plain_message = strip_ansi(message)

    if len(plain_message) <= wrap_area:
        return message

    ansi_segments = get_ansi_segments(message)
    chars = list(plain_message)
    current = 0
    message_buffer = ""

    while current < len(chars):
        next_index = min(current + wrap_area, len(chars))
        segment = "".join(chars[current:next_index])

        active_codes = get_active_codes_at_pos(ansi_segments, current) if current > 0 else list[str]()
        colored_segment = insert_ansi_codes_in_range(segment, ansi_segments, current, next_index, active_codes)
        message_buffer += colored_segment

        if next_index < len(chars):
            message_buffer += "\x1b[0m\n"

            indent_len = max(header_width - 4, 0)
            spaces = continuation_char * indent_len

            if foreground == background and show_colors:
                colored_spaces = ColoredString(spaces)
                colored_spaces = colored_spaces.color(foreground) if foreground else colored_spaces
                colored_spaces = colored_spaces.onColor(background) if background else colored_spaces

                message_buffer += colored_spaces
            else:
                message_buffer += spaces

            future_index = next_index + wrap_area
            is_last_line = future_index >= len(chars)
            connector = continuation_char * 3 if foreground == background else " ╠═" if not is_last_line else " ╚═"

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
        else:
            message_buffer += "\x1b[0m"

        current = next_index

    return message_buffer


def get_token_color(token: str) -> Color:
    """Allocates a unique color for a tag based on LRU."""

    if token not in KNOWN_TAGS:
        if TAG_COLORS:
            KNOWN_TAGS[token] = TAG_COLORS[0]
        else:
            return Color.BrightWhite

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


def start_adb_server(base_adb_command: List[str]) -> Result[CompletedProcess[str], CompletedProcess[str]]:
    start_server_command = base_adb_command + list[str](["start-server"])
    result = processRun(start_server_command, stdout=PIPE, stderr=PIPE, text=True, errors="replace")

    if result.returncode != 0:
        return Err(result)

    return Ok(result)


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


def get_dead_processes(message: str) -> Tuple[Optional[str], Optional[str]]:
    """Parses log lines for process death and removal."""

    for regex in (PID_KILL, PID_LEAVE, PID_DEATH):
        if match := regex.match(message):
            # PID_KILL / PID_LEAVE / PID_DEATH have different group indices
            if regex == PID_KILL:
                pid = match.group(1)
                package_line = match.group(2)
            elif regex == PID_LEAVE:
                pid = match.group(2)
                package_line = match.group(1)
            else:  # PID_DEATH
                pid = match.group(2)
                package_line = match.group(1)

            return pid, package_line

    return None, None


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

    def flush_writers() -> None:
        for index, writer in enumerate(writers):
            writer.write(writer_buffers[index])
            writer.flush()

    def write_token(
        message: str | ColoredString,
        wrap: bool = False,
        continuation_char: str = " ",
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
                    continuation_char,
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
    level = LogLevel.from_str(level.strip())
    tag = tag.strip()

    base_header_width = 3 + 1  # level width + space
    header_width += base_header_width + tag_width + 1  # base width + tag width + space

    if args.show_pid:
        header_width += pid_width + 1  # pid width + space

    if args.show_package:
        header_width += package_width + 1  # package width + space

    if started_process := get_started_processes(line):
        started_pid, started_uid, started_gids, started_package, started_target = started_process
        if is_matching_package(started_package, named_processes, catchall_packages):
            pids_map[started_pid] = started_package
            app_pid = started_pid

            banner_width = header_width - 1
            banner_char = "▓" if args.no_color else " "
            banner = ColoredString(banner_char * banner_width)

            if not args.no_color:
                banner = banner.color(Color.BrightGreen).onColor(Color.BrightGreen)

            started_package = started_package if started_package else "-" * pid_width
            started_target = started_target if started_target else "-" * pid_width
            started_pid = started_pid if started_pid else "-" * pid_width
            started_uid = started_uid if started_uid else "-" * pid_width
            started_gids = started_gids if started_gids else "-" * pid_width

            if not args.no_color:
                started_package = ColoredString(started_package).color(Color.BrightYellow)
                started_target = ColoredString(started_target).color(Color.BrightYellow)
                started_pid = ColoredString(started_pid).color(Color.BrightYellow)
                started_uid = ColoredString(started_uid).color(Color.BrightYellow)
                started_gids = ColoredString(started_gids).color(Color.BrightYellow)

            write_token(f"{banner}\n{banner}")
            write_token(" ")
            write_token(
                f"Process {started_package} created for {started_target}\n",
                wrap=True,
                continuation_char="▓",
                foreground=Color.BrightGreen,
                background=Color.BrightGreen,
            )

            write_token(f"{banner}")
            write_token(" ")
            write_token(
                f"PID: {started_pid}   UID: {started_uid}   GIDs: {started_gids}\n",
                wrap=True,
                foreground=Color.BrightGreen,
                background=Color.BrightGreen,
            )
            write_token(f"{banner}\n")

            last_tag = None

            return flush_writers()

    dead_pid, dead_process_name = get_dead_processes(message)
    if dead_pid and dead_process_name:
        if dead_pid in pids_map:
            del pids_map[dead_pid]

        banner_width = header_width - 1
        banner_char = "▒" if args.no_color else " "
        banner = ColoredString(banner_char * banner_width)

        if not args.no_color:
            banner = banner.color(Color.BrightRed).onColor(Color.BrightRed)

        dead_pid = dead_pid if dead_pid else "-" * pid_width
        dead_process_name = dead_process_name if dead_process_name else "-" * pid_width

        if not args.no_color:
            dead_pid = ColoredString(dead_pid).color(Color.BrightYellow)
            dead_process_name = ColoredString(dead_process_name).color(Color.BrightYellow)

        write_token(f"{banner}\n{banner}")
        write_token(" ")
        write_token(
            f"Process {dead_process_name} (PID: {dead_pid}) ended\n",
            wrap=True,
            continuation_char="▒",
            foreground=Color.BrightRed,
            background=Color.BrightRed,
        )
        write_token(f"{banner}\n")

        last_tag = None

        return flush_writers()

    # Filter logs
    if not args.all and owner not in pids_map:
        return

    if level < log_level:
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
    header_width = base_header_width

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
        LogLevel.Verbose: Color.BrightCyan,
        LogLevel.Debug: Color.BrightBlue,
        LogLevel.Info: Color.BrightGreen,
        LogLevel.Warn: Color.BrightYellow,
        LogLevel.Error: Color.TrueColor(250, 65, 25),
        LogLevel.Fatal: Color.BrightRed,
    }.get(level, Color.Black)

    level = ColoredString(f" {level} ").color(foreground).onColor(background)

    write_token(level)
    write_token(" ")  # one space separator
    # ----------------------------

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

    flush_writers()
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
    args = CliArgs.parse_args()

    try:
        base_adb_command = get_adb_command(args)
        adb_command = base_adb_command + ["logcat", "-v", "brief"]
        log_level = args.log_level
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
                case Ok(result):
                    output = result.stdout if result.stdout else result.stderr
                    stdout = "\n".join([line for line in output.splitlines() if line])

                    if stdout:
                        if not args.no_color:
                            stdout = ColoredString(stdout).color(Color.BrightCyan).bold()

                        print(stdout)

                case Err() as err:
                    err = CompletedProcess[str](**vars(err.err_value))
                    err_hdr = f"ERROR: {err.stderr.strip()}"
                    err_msg = "Could not start ADB server, check that ADB is added to env PATH and try again!"

                    if not args.no_color:
                        err_hdr = ColoredString(err_hdr).color(Color.BrightRed).bold()
                        err_msg = ColoredString(err_msg).color(Color.BrightRed).bold()

                    print(err_hdr, file=sys.stderr)
                    print(err_msg, file=sys.stderr)
                    sys.exit(err.returncode)

            match get_adb_devices(base_adb_command):
                # TODO: implement device selection
                case [AdbDevice(), *_] as devices:
                    for index, device in enumerate(devices):
                        msg = f"Found Device #{index}: {device}"

                        if not args.no_color:
                            msg = ColoredString(msg).color(Color.BrightCyan).bold()

                        print(msg)
                case None:
                    err_hdr = "ERROR: not connected"
                    err_msg = "ADB cannot find any attached devices, attach a device and try again!"

                    if not args.no_color:
                        err_hdr = ColoredString(err_hdr).color(Color.BrightRed).bold()
                        err_msg = ColoredString(err_msg).color(Color.BrightRed).bold()

                    print(err_hdr, file=sys.stderr)
                    print(err_msg, file=sys.stderr)
                    sys.exit(2)

            if not args.keep_logcat:
                adb_clear_command = base_adb_command + ["logcat", "-c"]
                processRun(adb_clear_command, check=False)

        if packages:
            msg = f"Capturing logcat messages from packages: [{', '.join(packages)}]…"
        else:
            args.all = True
            msg = "Capturing logcat messages…"

        if not args.no_color:
            msg = ColoredString(msg).color(Color.BrightCyan).bold()

        print(msg)

        # Determine exact processes vs. catch-all packages
        catchall_packages = list[str](filter(lambda package: package.find(":") == -1, packages))
        named_processes = list[str](filter(lambda package: package.find(":") != -1, packages))
        named_processes = list[str](
            map(lambda package: package[:-1] if package.endswith(":") else package, named_processes)
        )
        pids_map = get_processes(base_adb_command, catchall_packages, args) if sys.stdin.isatty() else dict[str, str]()

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
    except KeyboardInterrupt:
        # PyInstaller's bootloader on non-Windows platforms forwards SIGINT to the
        # child process, causing KeyboardInterrupt to fire multiple times and
        # interrupting the exception handler itself. Ignore SIGINT to prevent this.
        from signal import signal, SIGINT, SIG_IGN
        signal(SIGINT, SIG_IGN)

        from utils.pyproject import get_metadata
        prog_name = get_metadata().name
        msg = f"{prog_name} stopped by user!"

        if not args.no_color:
            msg = ColoredString(msg).color(Color.BrightCyan).bold()

        print(msg)
    finally:
        # Cleanup
        for writer in writers:
            writer.flush()
            writer.close()


if __name__ == "__main__":
    main()
