from typing import List
from typing import Optional
from dataclasses import dataclass


@dataclass
class CliArgs:
    """Command-line arguments for pidcat"""

    package: List[str]
    """List of package names to filter by"""

    useDevice: bool = False
    """Use first device for log input"""

    useEmulator: bool = False
    """Use first emulator for log input"""

    deviceSerial: Optional[str] = None
    """Serial number of device to use for log input"""

    all: bool = False
    """Show all packages"""

    keepLogcat: bool = False
    """Keep entire logcat before running"""

    currentApp: bool = False
    """Filter logcat by current running app(s)"""

    ignoreSystemTags: bool = False
    """Filter output by ignoring known system tags"""

    tag: Optional[List[str]] = None
    """Filter output by specified tag(s)"""

    ignoreTag: Optional[List[str]] = None
    """Filter output by ignoring specified tag(s)"""

    logLevel: str = "V"
    """Filter output by log level"""

    regex: Optional[str] = None
    """Filter output by regular expression"""

    showPID: bool = False
    """Show PID column"""

    showPackage: bool = False
    """Show package column"""

    alwaysShowTags: bool = False
    """Always show the tag name"""

    pidWidth: int = 6
    """Width of the PID column"""

    packageWidth: int = 20
    """Width of the package column"""

    tagWidth: int = 20
    """Width of the tag column"""

    gcColor: bool = False
    """Enable garabage collector messages colors"""

    noColor: bool = False
    """Disable colors in output"""

    outputPath: str = ""
    """Path to output file"""
