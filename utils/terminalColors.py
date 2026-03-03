from typing import Optional

RESET = "\033[0m"
BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)


def terminalColor(
    foreground: Optional[int] = None, background: Optional[int] = None, bold: bool = False, italic: bool = False
) -> str:
    """Returns the ANSI escape code for terminal color."""
    codes = []
    if bold:
        codes.append("1")
    if italic:
        codes.append("3")
    if foreground is not None:
        codes.append("3%d" % foreground)
        # codes.append("%d" % (90 + foreground))
    if background is not None:
        codes.append("4%d" % background)
        # codes.append("%d" % (100 + background))

    return "\033[%sm" % ";".join(codes) if codes else ""


def colorize(
    message: str,
    foreground: Optional[int] = None,
    background: Optional[int] = None,
    bold: bool = False,
    italic: bool = False,
) -> str:
    """Wraps a message with ANSI color codes."""
    return terminalColor(foreground, background, bold, italic) + message + RESET
