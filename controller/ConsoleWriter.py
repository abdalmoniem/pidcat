import io
import sys

from typing import override
from controller.Writer import Writer


class ConsoleWriter(Writer):
    """Configuration for color output."""

    def __init__(self, width: int, showColors: bool) -> None:
        self.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        super().__init__(width=width, showColors=showColors, outputFile=self.stdout)

    @override
    def write(self, text: str) -> None:
        self.stdout.write(f"{text}")

    @override
    def flush(self) -> None:
        self.stdout.flush()

    @override
    def close(self) -> None:
        self.stdout.flush()
        self.stdout.detach()
