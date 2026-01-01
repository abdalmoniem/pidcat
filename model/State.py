from typing import List
from typing import Dict
from typing import Optional
from dataclasses import dataclass


@dataclass
class State:
    """Holds the current state of the logcat processing."""

    pidsMap: Dict[str, str]
    lastTag: Optional[str]
    appPID: Optional[str]
    logLevel: int
    namedProcesses: List[str]
    catchallPackage: List[str]
