from __future__ import annotations

from builtins import str
from typing import Optional

from enum import auto
from enum import IntEnum


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
    def __init__(self, string: str = ""):
        self.__raw__: str = string
        self.__style__: Style = Style()

    def __render__(self) -> ColoredString:
        codes = list[str]()
        if self.__style__.bold:
            codes.append("1")
        if self.__style__.dim:
            codes.append("2")
        if self.__style__.italic:
            codes.append("3")
        if self.__style__.underline:
            codes.append("4")
        if self.__style__.blink:
            codes.append("5")
        if self.__style__.reversed:
            codes.append("7")
        if self.__style__.strikethrough:
            codes.append("9")
        if self.__style__.foreground is not None:
            if isinstance(self.__style__.foreground, str):
                codes.append(f"38;{self.__style__.foreground}")
            else:
                codes.append(f"{self.__style__.foreground.value}")
        if self.__style__.background is not None:
            if isinstance(self.__style__.background, str):
                codes.append(f"48;{self.__style__.background}")
            else:
                codes.append(f"{10 + self.__style__.background.value}")

        ansi = f"\033[{';'.join(map(str, codes))}m{self.__raw__}\033[0m" if codes else self.__raw__
        new = ColoredString(ansi)
        new.__raw__ = self.__raw__
        new.__style__ = self.__style__
        return new

    def color(self, foreground: Color) -> ColoredString:
        self.__style__.foreground = foreground
        return self.__render__()

    def onColor(self, background: Color) -> ColoredString:
        self.__style__.background = background
        return self.__render__()

    def bold(self) -> ColoredString:
        self.__style__.bold = True
        return self.__render__()

    def dim(self) -> ColoredString:
        self.__style__.dim = True
        return self.__render__()

    def italic(self) -> ColoredString:
        self.__style__.italic = True
        return self.__render__()

    def underline(self) -> ColoredString:
        self.__style__.underline = True
        return self.__render__()

    def blink(self) -> ColoredString:
        self.__style__.blink = True
        return self.__render__()

    def reversed(self) -> ColoredString:
        self.__style__.reversed = True
        return self.__render__()

    def strikethrough(self) -> ColoredString:
        self.__style__.strikethrough = True
        return self.__render__()

    @property
    def raw(self):
        return self.__raw__

    def reset(self) -> ColoredString:
        self.__style__ = Style()
        return ColoredString(self.__raw__)
