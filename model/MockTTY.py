import sys
from typing import TextIO
from typing import Optional
from io import TextIOWrapper
from subprocess import Popen as ProcessOpen


class MockTTY(ProcessOpen):
    """
    A mock object for ducktyping when reading from a pipe or file.

    This class is used for ducktyping when reading from a pipe or file.
    It only needs a working stdout for ducktyping, so it doesn't need to
    follow the ProcessOpen signature.

    Attributes:
        stdout (TextIO): The stdout of the MockTTY object.
    """

    def __init__(self) -> None:
        # ProcessOpen signature has many args, but we only need a working stdout for ducktyping
        """
        Initialize a MockTTY object.

        This class is used for ducktyping when reading from a pipe or file.
        It only needs a working stdout for ducktyping, so it doesn't need to
        follow the ProcessOpen signature.
        """
        sys.stdin = TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace")

    @property
    def stdout(self) -> TextIO:
        """
        Returns the stdout of the MockTTY object.

        This property is used for ducktyping when reading from a pipe or file.
        It returns sys.stdin for compatibility with ProcessOpen objects.
        """
        return sys.stdin

    def poll(self) -> Optional[int]:
        """
        Check if there is any data available to read from the pipe.

        Returns None if there is no data available, otherwise the number of bytes available to read
        """
        return None
