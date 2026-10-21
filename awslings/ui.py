"""Tiny terminal helpers (ANSI colours, progress bar) with no third-party dependency."""

import os
import shutil
import sys

_COLOR = sys.stdout.isatty() and "NO_COLOR" not in os.environ and os.environ.get("TERM") != "dumb"


def _style(code):
    def apply(text):
        return f"\033[{code}m{text}\033[0m" if _COLOR else str(text)

    return apply


bold = _style("1")
dim = _style("2")
red = _style("31")
green = _style("32")
yellow = _style("33")
blue = _style("34")
magenta = _style("35")
cyan = _style("36")


def clear_screen():
    if _COLOR:
        print("\033[2J\033[H", end="", flush=True)


def width(default=80):
    return min(shutil.get_terminal_size((default, 24)).columns, 100)


def rule(char="─"):
    return dim(char * width())


def progress_bar(done, total, size=40):
    if total == 0:
        return ""
    filled = round(size * done / total)
    bar = green("#" * filled) + dim("-" * (size - filled))
    return f"[{bar}] {done}/{total} ({100 * done // total}%)"


def box(title):
    line = "═" * (len(title) + 2)
    return f"╔{line}╗\n║ {title} ║\n╚{line}╝"
