from __future__ import annotations

from argparse import SUPPRESS
from argparse import ArgumentParser

from dataclasses import dataclass

from model.log_level import LogLevel

from utils.pyproject import get_metadata
from utils.pyproject import PY_PROJECT_FILE

from rich_argparse import RichHelpFormatter
from rich_argparse import RawTextRichHelpFormatter

from typing import List
from typing import Optional


@dataclass
class CliArgs:
    """Command-line arguments for pidcat"""

    package: List[str]
    """List of package names to filter by"""

    use_device: bool = False
    """Use first device for log input"""

    use_emulator: bool = False
    """Use first emulator for log input"""

    device_serial: Optional[str] = None
    """Serial number of device to use for log input"""

    all: bool = False
    """Show all packages"""

    keep_logcat: bool = False
    """Keep entire logcat before running"""

    current_app: bool = False
    """Filter logcat by current running app(s)"""

    ignore_system_tags: bool = False
    """Filter output by ignoring known system tags"""

    tag: Optional[List[str]] = None
    """Filter output by specified tag(s)"""

    ignore_tag: Optional[List[str]] = None
    """Filter output by ignoring specified tag(s)"""

    log_level: LogLevel = LogLevel.Verbose
    """Filter output by log level"""

    regex: Optional[str] = None
    """Filter output by regular expression"""

    show_pid: bool = False
    """Show PID column"""

    show_package: bool = False
    """Show package column"""

    always_show_tags: bool = False
    """Always show the tag name"""

    pid_width: int = 6
    """Width of the PID column"""

    package_width: int = 20
    """Width of the package column"""

    tag_width: int = 20
    """Width of the tag column"""

    gc_color: bool = False
    """Enable garabage collector messages colors"""

    no_color: bool = False
    """Disable colors in output"""

    output_path: str = ""
    """Path to output file"""

    @staticmethod
    def parse_args() -> CliArgs:
        """Creates and returns the ArgumentParser instance."""

        metadata = get_metadata()
        assert metadata.version, f"version not defined in {PY_PROJECT_FILE}"

        prog_name = metadata.name
        version_name = metadata.version

        RichHelpFormatter.styles["argparse.prog"] = "bold green"
        RichHelpFormatter.styles["argparse.groups"] = "bold yellow"
        RichHelpFormatter.styles["argparse.help"] = "default"
        RichHelpFormatter.styles["argparse.args"] = "bold green"
        RichHelpFormatter.styles["argparse.metavar"] = "bold cyan"
        RichHelpFormatter.styles["argparse.syntax"] = "bold yellow"
        RichHelpFormatter.styles["argparse.default"] = "bold cyan"

        parser = ArgumentParser(
            add_help=False,
            prog=prog_name,
            description=f"{prog_name} v{version_name}\n"
            "A colorized Android logcat viewer with advanced filtering capabilities.",
            formatter_class=RawTextRichHelpFormatter,
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
            default=SUPPRESS,
            help="Show this help message and exit.",
        )

        about_options.add_argument(
            "-v",
            "--version",
            action="version",
            version=str(version_name),
            help="Print the version number and exit",
        )

        devices_options.add_argument(
            "-d",
            "--device",
            dest="use_device",
            action="store_true",
            default=False,
            help="Use first device for log input, [bold cyan]\\[default: %(default)s][/]",
        )

        devices_options.add_argument(
            "-e",
            "--emulator",
            dest="use_emulator",
            action="store_true",
            default=False,
            help="Use first emulator for log input, [bold cyan]\\[default: %(default)s][/]",
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
            help="Print log messages from all packages, [bold cyan]\\[default: %(default)s][/]",
        )

        filtering_options.add_argument(
            "-k",
            "--keep",
            dest="keep_logcat",
            action="store_true",
            default=False,
            help="Keep the entire log before running, [bold cyan]\\[default: %(default)s][/]",
        )

        filtering_options.add_argument(
            "-c",
            "--current",
            dest="current_app",
            action="store_true",
            default=False,
            help="Filter logcat by current running app(s), [bold cyan]\\[default: %(default)s][/]",
        )

        filtering_options.add_argument(
            "-I",
            "--ignore-system-tags",
            dest="ignore_system_tags",
            action="store_true",
            default=False,
            help="Filter output by ignoring known system tags, "
            "[bold cyan]\\[default: %(default)s][/]\n"
            "Use --ignore-tag to ignore additional tags if needed",
        )

        filtering_options.add_argument(
            "-t",
            "--tag",
            metavar="TAG",
            dest="tag",
            action="append",
            help="Filter output by specified tag(s)\n"
            "This can be specified multiple times, or as a comma separated list",
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
            metavar="LEVEL",
            type=lambda arg: LogLevel.from_str(arg.upper()),
            choices=list(LogLevel),
            default=LogLevel.Verbose,
            help="Filter messages lower than minimum log level, "
            "[bold cyan]\\[default: %(default)s][/] [bold cyan]\\[possible values: %(choices)s][/]",
        )

        filtering_options.add_argument(
            "-r",
            "--regex",
            metavar="REGEX",
            dest="regex",
            type=str,
            help="Filter output messages using the specified [bold cyan]\\[%(metavar)s][/]",
        )

        formatting_options.add_argument(
            "-P",
            "--show-pid",
            dest="show_pid",
            action="store_true",
            default=False,
            help="Show package name in output, [bold cyan]\\[default: %(default)s][/]",
        )

        formatting_options.add_argument(
            "-p",
            "--show-package",
            dest="show_package",
            action="store_true",
            default=False,
            help="Show package name in output, [bold cyan]\\[default: %(default)s][/]",
        )

        formatting_options.add_argument(
            "-S",
            "--always-show-tags",
            dest="always_show_tags",
            action="store_true",
            default=False,
            help="Always show the tag name, [bold cyan]\\[default: %(default)s][/]",
        )

        formatting_options.add_argument(
            "-x",
            "--pid-width",
            metavar="WIDTH",
            dest="pid_width",
            type=int,
            default=5,
            help="Width of PID column, [bold cyan]\\[default: %(default)s][/]",
        )

        formatting_options.add_argument(
            "-n",
            "--package-width",
            metavar="WIDTH",
            dest="package_width",
            type=int,
            default=20,
            help="Width of package/process name column, [bold cyan]\\[default: %(default)s][/]",
        )

        formatting_options.add_argument(
            "-m",
            "--tag-width",
            metavar="WIDTH",
            dest="tag_width",
            type=int,
            default=20,
            help="Width of tag column, [bold cyan]\\[default: %(default)s][/]",
        )

        color_options.add_argument(
            "-g",
            "--gc-color",
            dest="gc_color",
            action="store_true",
            default=False,
            help="Enable garbage collector messages colors, [bold cyan]\\[default: %(default)s][/]",
        )

        color_options.add_argument(
            "-N",
            "--no-color",
            dest="no_color",
            action="store_true",
            default=False,
            help="Disable message colors, [bold cyan]\\[default: %(default)s][/]",
        )

        output_options.add_argument(
            "-o",
            "--output",
            metavar="FILE_PATH",
            dest="output_path",
            type=str,
            default="",
            help="Save output to [bold cyan]\\[%(metavar)s][/]",
        )

        args = parser.parse_args()
        args = CliArgs(**vars(args))

        return args
