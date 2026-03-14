from dataclasses import dataclass

@dataclass
class AnsiSegment:
    code: str
    visible_pos: int
