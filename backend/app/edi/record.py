"""80-character CATAIR record. Positions are 1-based and inclusive."""

from __future__ import annotations

RECORD_LEN = 80


class RecordError(ValueError):
    pass


class Record:
    def __init__(self) -> None:
        self._chars = [' '] * RECORD_LEN

    def put(self, start: int, end: int, value: str) -> None:
        if start < 1 or end > RECORD_LEN or end < start:
            raise RecordError(f'Position {start}-{end} is outside 1-{RECORD_LEN}')
        text = (value or '').upper()
        width = end - start + 1
        if len(text) > width:
            raise RecordError(f'Value {text!r} does not fit positions {start}-{end}')
        text = text.ljust(width)
        for offset, ch in enumerate(text):
            self._chars[start - 1 + offset] = ch

    def text(self) -> str:
        line = ''.join(self._chars)
        if len(line) != RECORD_LEN:
            raise RecordError(f'Record is {len(line)} characters')
        return line


def cut(line: str, start: int, end: int) -> str:
    """Slice a 1-based inclusive span. Short lines are treated as space-padded."""
    padded = line.ljust(RECORD_LEN)
    return padded[start - 1:end]
