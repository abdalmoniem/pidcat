from __future__ import annotations

from typing import List

from enum import auto
from enum import IntEnum


class LogLevel(IntEnum):
    Verbose = auto()
    Debug = auto()
    Info = auto()
    Warn = auto()
    Error = auto()
    Fatal = auto()

    @staticmethod
    def from_str(string: str) -> LogLevel:
        match string:
            case "V":
                return LogLevel.Verbose
            case "D":
                return LogLevel.Debug
            case "I":
                return LogLevel.Info
            case "W":
                return LogLevel.Warn
            case "E":
                return LogLevel.Error
            case "F":
                return LogLevel.Fatal
            case "F":
                return LogLevel.Fatal
            case other:
                raise ValueError(f"Invalid log level '{other}'")

    def __str__(self) -> str:
        return self.name[0]

    def __repr__(self) -> str:
        return self.__str__()

    @staticmethod
    def choices() -> List[str]:
        return [value.name[0] for value in LogLevel]
