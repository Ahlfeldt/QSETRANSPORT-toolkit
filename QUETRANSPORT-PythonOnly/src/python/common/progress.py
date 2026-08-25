
"""Progress helpers that work in Spyder, PowerShell, and plain terminals."""
from __future__ import annotations

from contextlib import contextmanager
import sys
from typing import Iterable, Iterator, TypeVar

T = TypeVar("T")

try:
    from tqdm import tqdm as _tqdm
except ImportError:  # The root master script normally installs tqdm first.
    _tqdm = None


def _animated_terminal_available() -> bool:
    """Return True only where carriage-return progress bars render correctly."""
    # Spyder/IPython capture streams rather than exposing a normal terminal.
    # In that setting tqdm's repeated carriage returns often leave only "0%".
    return (
        _tqdm is not None
        and hasattr(sys.stderr, "isatty")
        and sys.stderr.isatty()
    )


class _ConsoleProgress:
    """Newline-based progress milestones for Spyder and captured consoles."""

    def __init__(self, total: int, description: str, unit: str = "step"):
        self.requested_total = int(total)
        self.total = max(self.requested_total, 1)
        self.description = description
        self.unit = unit
        self.current = 0
        self.last_percent = -10
        print(
            f"{description}: starting ({self.requested_total} {unit}"
            f"{'' if self.requested_total == 1 else 's'})",
            flush=True,
        )

    def update(self, amount: int = 1) -> None:
        self.current += amount
        percent = int(100 * min(self.current, self.total) / self.total)
        if percent >= self.last_percent + 10 or self.current >= self.total:
            print(
                f"{self.description}: {percent:3d}% "
                f"({self.current}/{self.requested_total} {self.unit}"
                f"{'' if self.requested_total == 1 else 's'})",
                flush=True,
            )
            self.last_percent = percent

    def close(self) -> None:
        if self.current < self.requested_total:
            print(
                f"{self.description}: stopped at "
                f"{self.current}/{self.requested_total} {self.unit}s",
                flush=True,
            )


@contextmanager
def stage_bar(name: str, total: int) -> Iterator:
    """Display an animated terminal bar or Spyder-safe milestone updates."""
    if _animated_terminal_available():
        bar = _tqdm(
            total=total, desc=name, unit="step", dynamic_ncols=True,
            leave=True, mininterval=0.2,
        )
    else:
        bar = _ConsoleProgress(total, name)
    try:
        yield bar
    finally:
        bar.close()


def progress_range(
    iterable: Iterable[T], *, total: int, description: str, unit: str
) -> Iterator[T]:
    """Wrap a slow loop in progress reporting appropriate to the console."""
    if _animated_terminal_available():
        yield from _tqdm(
            iterable, total=total, desc=description, unit=unit,
            dynamic_ncols=True, leave=True, mininterval=0.2,
        )
        return

    bar = _ConsoleProgress(total, description, unit)
    try:
        for item in iterable:
            yield item
            bar.update()
    finally:
        bar.close()
