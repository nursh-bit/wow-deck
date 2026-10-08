"""Help content for macOS, in the same structure as wowdeck.help.SECTIONS."""
from __future__ import annotations

SECTIONS: list[tuple[str, str, list]] = [
    ('What WoW Deck does on a Mac',
     'World of Warcraft and Battle.net run natively on macOS, so WoW Deck only has to get the '
     'pieces around the game in place: Battle.net, ConsolePort and the error-catching addons. '
     'Pick the parts you want and press one button; everything it does can be undone.',
     []),
    ('The components',
     'Only Battle.net + WoW is required. Ticked items get installed, unticked items get removed.',
     [('Battle.net + World of Warcraft (required)',
       'Checks for Battle.net and World of Warcraft. If Battle.net is missing, the Blizzard download '
       'page opens; install it, log in and install WoW there, then run Set up again for the rest.'),
      ('ConsolePort (optional addon)',
       'The gamepad interface for WoW, installed from its latest release.'),
      ('BugGrabber + BugSack (optional addons)',
       'Catch Lua errors quietly, so an addon problem never blocks the screen.')]),
    ('Good to know', '',
     ['Controllers connect through macOS itself (System Settings > Game Controllers); WoW reads them '
      'directly, no Steam needed.',
      'Addons are installed into every WoW flavour found under /Applications/World of Warcraft. '
      'Set WOW_DECK_WOW_DIR if the game lives somewhere else.',
      'Everything can be removed with "wow-deck uninstall --all". Battle.net and WoW stay.']),
]
