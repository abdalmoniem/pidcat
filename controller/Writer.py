from typing import TextIO
from typing import Optional


class Writer:
    def __init__(self, width: Optional[int], showColors: bool, outputFile: TextIO) -> None:
        self.width = width
        self.showColors = showColors
        self.outputFile = outputFile

    def write(self, text: str) -> None:
        pass

    def flush(self) -> None:
        pass

    def close(self) -> None:
        pass

    def __str__(self) -> str:
        width, showColors, outputFile = self.width, self.showColors, self.outputFile.name
        return f"{self.__class__.__name__}({width=}, {showColors=}, {outputFile=})"

    def __repr__(self) -> str:
        return self.__str__()
