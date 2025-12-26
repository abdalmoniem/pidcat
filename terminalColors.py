from typing import Optional

RESET = "\033[0m"
BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)


def termColor(foreground: Optional[int] = None, background: Optional[int] = None) -> str:
    """Returns the ANSI escape code for terminal color."""

    codes = []

    if foreground is not None:
        codes.append("3%d" % foreground)

    if background is not None:
        codes.append("10%d" % background)

    return "\033[%sm" % ";".join(codes) if codes else ""


def colorize(message: str, foreground: Optional[int] = None, background: Optional[int] = None) -> str:
    """Wraps a message with ANSI color codes."""

    return termColor(foreground, background) + message + RESET
