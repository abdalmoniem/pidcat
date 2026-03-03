import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from Writer import Writer
from typing import TextIO
from typing import override


class FileWriter(Writer):
    def __init__(self, outputFile: TextIO) -> None:
        super().__init__(width=-1, showColors=False, outputFile=outputFile)

    @override
    def write(self, text: str) -> None:
        self.outputFile.write(f"{text}")

    @override
    def flush(self) -> None:
        self.outputFile.flush()
    
    @override
    def close(self) -> None:
        self.outputFile.close()
