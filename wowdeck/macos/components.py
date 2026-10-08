"""macOS component list. Reuses the shared Component model and addon components; Battle.net
is a native app that the user installs from Blizzard, so the required component only checks
for it and opens the right place."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable
from ..components import Component, _addon_component
from . import mac


@dataclass
class Ctx:
    wtf_dirs: list[str]
    log: Callable = print


def _bn_detect(ctx: Ctx) -> bool:
    return bool(mac.battlenet_app()) and bool(ctx.wtf_dirs)


def wow_installed(ctx: Ctx) -> bool:
    return bool(mac.wow_wtf_dirs())


def _bn_install(ctx: Ctx) -> None:
    app = mac.battlenet_app()
    if not app:
        ctx.log(f'  Battle.net not found; opening {mac.BATTLENET_DOWNLOAD_PAGE}')
        mac.open_url(mac.BATTLENET_DOWNLOAD_PAGE)
    elif not ctx.wtf_dirs:
        ctx.log(f'  World of Warcraft not found; opening {app}')
        mac.open_app(app)
    ctx.wtf_dirs = mac.wow_wtf_dirs()


COMPONENTS: list[Component] = [
    Component('battlenet', 'Battle.net + World of Warcraft', required=True, detect=_bn_detect, install=_bn_install),
    _addon_component('consoleport', 'Install ConsolePort', ['consoleport']),
    _addon_component('bugs', 'Install BugGrabber + BugSack', ['buggrabber', 'bugsack']),
]


def make_ctx(log=print) -> Ctx:
    return Ctx(mac.wow_wtf_dirs(), log)
