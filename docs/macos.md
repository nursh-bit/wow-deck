# macOS

World of Warcraft and Battle.net are native macOS applications. None of the SteamOS machinery
applies there: no Proton prefix, no Steam shortcut, no InputPlumber, no root files. The macOS
platform therefore covers the parts that sit around the game: Battle.net discovery, the addon
components and the hub.

## Platform selection

`wowdeck/host.py` names the platform: `macos` when `sys.platform == 'darwin'`, `steamos`
otherwise. `WOW_DECK_PLATFORM=steamos|macos` forces one. `wowdeck.cli.main` hands control to
`wowdeck.macos.cli.main` on macOS before any SteamOS code runs; SteamOS behaviour is unchanged.

| Shared with SteamOS | macOS-specific (`wowdeck/macos/`) | Not used on macOS |
|---|---|---|
| `addons.py`, the `Component` model and addon components, `help.render_text`, `selfupdate.py`, `ui.py` | `mac.py` (discovery), `components.py`, `cli.py`, `help.py` | `steam.py`, `vdf.py`, `deck.py`, `battlenet.py`, `files.py`, `curseforge.py`, `gtkui.py`, `share/*.yaml`, the launch wrapper, the root phase |

## Paths

| Item | Location |
|---|---|
| Application | `~/Library/Application Support/wow-deck/app/` |
| Addon state (`state.json`) | `~/Library/Application Support/wow-deck/` |
| Command-line entry | `~/.local/bin/wow-deck` (symlink) |
| Finder launcher | `~/Applications/WoW Deck.command` (opens Terminal and runs the hub) |
| Battle.net | `/Applications/Battle.net.app` or `~/Applications/Battle.net.app` |
| World of Warcraft | `/Applications/World of Warcraft` or `~/Applications/World of Warcraft`; `WOW_DECK_WOW_DIR` overrides |

A flavour folder (`_retail_`, `_classic_era_`, ...) counts as installed when it contains a
`World of Warcraft*.app` bundle. Addons go to `<flavour>/Interface/AddOns`, the same layout as
the Windows client, so the shared addon code is used unchanged.

## Python

macOS ships `/usr/bin/python3` as a stub that offers to install the Command Line Tools. The
installer checks `xcode-select -p` and, if the tools are missing, starts `xcode-select
--install` and stops; it is re-run afterwards. The Command Line Tools provide Python 3.9, so
code on the shared and macOS paths must run on 3.9 (`from __future__ import annotations`
keeps `X | None` annotations valid there).

## Dialogs

`ui.py` gains an `osascript` backend, selected on macOS. Every dialog is an AppleScript
`on run argv` handler with the text passed as arguments, so messages need no escaping:
`display dialog` for info, error, yes/no and password; `choose from list` (with multiple
selections for the checklist) for menus; `display notification` for progress notes. The text
viewer writes a temporary file and opens it with `open -t`.

## Components

| Component | macOS behaviour |
|---|---|
| Battle.net + World of Warcraft (required) | Detects `Battle.net.app` and a WoW flavour. Missing Battle.net opens `https://download.battle.net/`; missing WoW opens Battle.net. Setup stops there and is re-run once WoW is installed |
| ConsolePort, BugGrabber + BugSack | Shared addon components |

Addon changes are refused while the game is running. `wow-deck uninstall` removes the addons
WoW Deck installed; `--all` also removes the application, the symlink and the launcher.
`doctor` reports the macOS version and architecture, Python, Battle.net, the WoW folders, the
addons per flavour and the `GamePadEnable` CVar from `WTF/Config.wtf`.

## Not covered yet

- **Controllers and paddles.** The GameController framework reports paddles on the Xbox Elite
  Series 2 and the DualSense Edge; whether the macOS WoW client maps them to `PADPADDLE1-4`
  has not been verified (`GamePadListDevices`, `C_GamePad.GetDeviceRawState`). Presenting one
  controller as another, as InputPlumber does on SteamOS, would need a signed DriverKit
  extension.
- **CurseForge.** The macOS app is a `.dmg`; its game-instance registry location is not yet
  confirmed, so registration is not offered.
- **Battle.net installer automation.** The installer is opened from Blizzard's download page
  rather than downloaded and run.
