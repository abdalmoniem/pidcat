from typing import TextIO
from typing import Optional


class Writer:
    def __init__(self, width: Optional[int], show_colors: bool, output_file: TextIO) -> None:
        self.width = width
        self.show_colors = show_colors
        self.output_file = output_file

    def write(self, text: str) -> None:
        pass

    def flush(self) -> None:
        pass

    def close(self) -> None:
        pass

    def __str__(self) -> str:
        field_info = vars(self)
        fields = ", ".join(f"{name} = {value!r}" for name, value in field_info.items())

        return f"{self.__class__.__name__} {{ {fields} }}"

    def __repr__(self) -> str:
        return self.__str__()
