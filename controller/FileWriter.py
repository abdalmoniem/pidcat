from typing import TextIO
from typing import override

from controller.Writer import Writer

class FileWriter(Writer):
    def __init__(self, outputFile: TextIO) -> None:
        super().__init__(width=None, showColors=False, outputFile=outputFile)

    @override
    def write(self, text: str) -> None:
        self.outputFile.write(f"{text}")

    @override
    def flush(self) -> None:
        self.outputFile.flush()

    @override
    def close(self) -> None:
        self.outputFile.close()
