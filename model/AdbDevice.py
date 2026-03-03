from dataclasses import dataclass
from model.AdbState import AdbState


@dataclass
class AdbDevice:
    deviceId: str
    deviceState: AdbState

    def __str__(self) -> str:
        deviceId = self.deviceId
        deviceState = self.deviceState

        return f"{self.__class__.__name__} {{ {deviceId = }, {deviceState = } }}"

    def __repr__(self) -> str:
        return str(self)
