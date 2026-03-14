from __future__ import annotations

from builtins import str
from typing import Optional
from enum import IntEnum, auto


class Color(IntEnum):
    Black = 30
    Red = auto()
    Green = auto()
    Yellow = auto()
    Blue = auto()
    Magenta = auto()
    Cyan = auto()
    White = auto()
    BrightBlack = 90
    BrightRed = auto()
    BrightGreen = auto()
    BrightYellow = auto()
    BrightBlue = auto()
    BrightMagenta = auto()
    BrightCyan = auto()
    BrightWhite = auto()

    @staticmethod
    def TrueColor(red: int, green: int, blue: int):
        return f"2;{red};{green};{blue}"


class Style:
    def __init__(self) -> None:
        self.foreground: Optional[Color] = None
        self.background: Optional[Color] = None
        self.bold = False
        self.dim = False
        self.italic = False
        self.underline = False
        self.blink = False
        self.reversed = False
        self.strikethrough = False


class ColoredString(str):
    _raw: str
    _style: Style

    def __init__(self, string: str = ""):
        self._raw = string
        self._style = Style()

    def _render(self) -> ColoredString:
        codes = list[str]()
        if self._style.bold:
            codes.append("1")
        if self._style.dim:
            codes.append("2")
        if self._style.italic:
            codes.append("3")
        if self._style.underline:
            codes.append("4")
        if self._style.blink:
            codes.append("5")
        if self._style.reversed:
            codes.append("7")
        if self._style.strikethrough:
            codes.append("9")
        if self._style.foreground is not None:
            if isinstance(self._style.foreground, str):
                codes.append(f"38;{self._style.foreground}")
            else:
                codes.append(f"{self._style.foreground.value}")
        if self._style.background is not None:
            if isinstance(self._style.background, str):
                codes.append(f"48;{self._style.background}")
            else:
                codes.append(f"{10 + self._style.background.value}")

        ansi = f"\033[{';'.join(map(str, codes))}m{self._raw}\033[0m" if codes else self._raw
        new = ColoredString(ansi)
        new._raw = self._raw
        new._style = self._style
        return new

    def color(self, foreground: Color) -> ColoredString:
        self._style.foreground = foreground
        return self._render()

    def onColor(self, background: Color) -> ColoredString:
        self._style.background = background
        return self._render()

    def bold(self) -> ColoredString:
        self._style.bold = True
        return self._render()

    def dim(self) -> ColoredString:
        self._style.dim = True
        return self._render()

    def italic(self) -> ColoredString:
        self._style.italic = True
        return self._render()

    def underline(self) -> ColoredString:
        self._style.underline = True
        return self._render()

    def blink(self) -> ColoredString:
        self._style.blink = True
        return self._render()

    def reversed(self) -> ColoredString:
        self._style.reversed = True
        return self._render()

    def strikethrough(self) -> ColoredString:
        self._style.strikethrough = True
        return self._render()

    def reset(self) -> ColoredString:
        self._style = Style()
        return ColoredString(self._raw)
