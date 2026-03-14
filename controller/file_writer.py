from typing import TextIO
from typing import override

from controller.writer import Writer

class FileWriter(Writer):
    def __init__(self, outputFile: TextIO) -> None:
        super().__init__(width=None, show_colors=False, output_file=outputFile)

    @override
    def write(self, text: str) -> None:
        self.output_file.write(f"{text}")

    @override
    def flush(self) -> None:
        self.output_file.flush()

    @override
    def close(self) -> None:
        self.output_file.close()
