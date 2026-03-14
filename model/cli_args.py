from typing import List
from typing import Optional
from dataclasses import dataclass


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

    log_level: str = "V"
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
