"""macOS facts: OS version, Battle.net and World of Warcraft discovery, running processes.
Read-only helpers; nothing here needs root."""
from __future__ import annotations
import glob, os, platform, subprocess

HOME = os.path.expanduser('~')
BATTLENET_APPS = ('/Applications/Battle.net.app', os.path.join(HOME, 'Applications', 'Battle.net.app'))
# Battle.net installs to /Applications by default; the install folder can be changed there, so
# WOW_DECK_WOW_DIR points at a "World of Warcraft" folder anywhere else.
WOW_DIRS = ('/Applications/World of Warcraft', os.path.join(HOME, 'Applications', 'World of Warcraft'))
BATTLENET_DOWNLOAD_PAGE = 'https://download.battle.net/'


def macos_version() -> tuple[int, ...] | None:
    v = platform.mac_ver()[0]
    try:
        return tuple(int(x) for x in v.split('.')) if v else None
    except ValueError:
        return None


def arch() -> str:
    return platform.machine()           # arm64 (Apple silicon) or x86_64


def battlenet_app() -> str | None:
    return next((a for a in BATTLENET_APPS if os.path.isdir(a)), None)


def wow_roots() -> list[str]:
    forced = os.environ.get('WOW_DECK_WOW_DIR')
    cands = [forced] if forced else list(WOW_DIRS)
    return [d for d in cands if d and os.path.isdir(d)]


def _has_game_app(flavour_dir: str) -> bool:
    """`_retail_` holds "World of Warcraft.app", Classic flavours "World of Warcraft Classic.app"."""
    return bool(glob.glob(os.path.join(glob.escape(flavour_dir), 'World of Warcraft*.app')))


def wow_flavour_dirs(roots: list[str] | None = None) -> list[str]:
    """Flavour folders (`_retail_`, `_classic_era_`, ...) that contain the game app. WTF/ and
    Interface/AddOns/ appear on the first launch, so callers create them as needed."""
    out = []
    for root in (wow_roots() if roots is None else roots):
        out += [d for d in sorted(glob.glob(os.path.join(glob.escape(root), '_*_'))) if _has_game_app(d)]
    return out


def wow_wtf_dirs(roots: list[str] | None = None) -> list[str]:
    """`<flavour>/WTF` for every installed flavour (the folder may not exist yet). The addon
    code places addons in the sibling Interface/AddOns, the same layout as on Windows."""
    return [os.path.join(d, 'WTF') for d in wow_flavour_dirs(roots)]


def process_running(name: str) -> bool:
    return subprocess.run(['pgrep', '-x', name], capture_output=True).returncode == 0


def wow_running() -> bool:
    return process_running('World of Warcraft') or process_running('World of Warcraft Classic')


def open_url(url: str) -> bool:
    return subprocess.run(['open', url], capture_output=True).returncode == 0


def open_app(path: str) -> bool:
    return subprocess.run(['open', path], capture_output=True).returncode == 0
