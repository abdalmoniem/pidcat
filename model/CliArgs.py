from typing import List
from typing import Optional
from dataclasses import dataclass


@dataclass
class CliArgs:
    """Configuration for logcat filtering and display."""

    package: List[str]
    all: bool = False
    keepLogcat: bool = False
    useDevice: bool = False
    useEmulator: bool = False
    colorGC: bool = False
    noColor: bool = False
    showPID: bool = False
    showPackage: bool = False
    alwaysShowTags: bool = False
    currentApp: bool = False
    ignoreSystemTags: bool = False
    tag: Optional[List[str]] = None
    ignoreTag: Optional[List[str]] = None
    logLevel: str = "V"
    regex: Optional[str] = None
    pidWidth: int = 6
    packageWidth: int = 20
    tagWidth: int = 20
    deviceSerial: Optional[str] = None
    outputPath: str = ""
