"""Which platform wow-deck runs on, and the per-platform user data folder. SteamOS (any Linux)
keeps the original layout; macOS gets its own front end and component list (wowdeck.macos).
WOW_DECK_PLATFORM=steamos|macos forces one (tests, development)."""
from __future__ import annotations
import os, sys

STEAMOS, MACOS = 'steamos', 'macos'


def name() -> str:
    forced = os.environ.get('WOW_DECK_PLATFORM', '').lower()
    if forced in (STEAMOS, MACOS):
        return forced
    return MACOS if sys.platform == 'darwin' else STEAMOS


def is_macos() -> bool:
    return name() == MACOS


def user_data(home: str | None = None) -> str:
    home = home or os.path.expanduser('~')
    if is_macos():
        return os.path.join(home, 'Library', 'Application Support', 'wow-deck')
    return os.path.join(home, '.local', 'share', 'wow-deck')


USER_DATA = user_data()
