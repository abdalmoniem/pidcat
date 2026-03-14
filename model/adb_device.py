from dataclasses import dataclass
from model.adb_state import AdbState


@dataclass
class AdbDevice:
    device_id: str
    device_state: AdbState

    def __str__(self) -> str:
        field_info = vars(self)
        fields = ", ".join(f"{name} = {value!r}" for name, value in field_info.items())

        return f"{self.__class__.__name__} {{ {fields} }}"

    def __repr__(self) -> str:
        return str(self)
