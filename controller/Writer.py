from typing import TextIO


class Writer:
    def __init__(self, width: int, showColors: bool, outputFile: TextIO, isWrappable: bool = False) -> None:
        self.width = width
        self.outputFile = outputFile
        self.showColors = showColors
        self.isWrappable = isWrappable

    def write(self, text: str) -> None:
        pass

    def flush(self) -> None:
        pass

    def close(self) -> None:
        pass
