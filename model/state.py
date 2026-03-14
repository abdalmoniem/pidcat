from typing import List
from typing import Dict
from typing import Optional

from dataclasses import dataclass


@dataclass
class State:
    """Holds the current state of the logcat processing."""

    pids_map: Dict[str, str]
    last_tag: Optional[str]
    app_pid: Optional[str]
    log_level: int
    named_processes: List[str]
    catchall_packages: List[str]
