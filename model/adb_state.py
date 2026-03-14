from __future__ import annotations
from enum import Enum


class AdbState(Enum):
    Device = "device"
    Emulator = "emulator"
    Offline = "offline"
    UnAuthorized = "unauthorized"
    Recovery = "recovery"
    Sideload = "sideload"
    NoPermissions = "nopermissions"
    NoDevice = "nodevice"

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return str(self)

    @staticmethod
    def fromStr(string: str) -> AdbState:
        match string.lower():
            case "device":
                return AdbState.Device
            case "emulator":
                return AdbState.Emulator
            case "offline":
                return AdbState.Offline
            case "unauthorized":
                return AdbState.UnAuthorized
            case "recovery":
                return AdbState.Recovery
            case "sideload":
                return AdbState.Sideload
            case "nopermissions":
                return AdbState.NoPermissions
            case "nodevice":
                return AdbState.NoDevice
            case unknown:
                raise ValueError(f"Invalid AdbState: {unknown}")
