"""wow-deck verbs on macOS: hub, setup, doctor, uninstall [--all], help. The SteamOS-only verbs
(install, paddles, curseforge, battlenet) report that they do not apply here."""
from __future__ import annotations
import argparse, contextlib, io, os, re, shutil, sys
from .. import addons, host, selfupdate, ui
from . import components, help as mac_help, mac

OK, WARN, FAIL = '\033[32mOK  \033[0m', '\033[33mWARN\033[0m', '\033[31mFAIL\033[0m'
LAUNCHER = os.path.join(mac.HOME, 'Applications', 'WoW Deck.command')
USER_BIN_LINK = os.path.join(mac.HOME, '.local', 'bin', 'wow-deck')
STEAMOS_ONLY = ('install', 'update', 'paddles', 'curseforge', 'battlenet', 'finish')


def _p(status, msg):
    print(f'{status} {msg}')


def _gamepad_cvar(wtf_dir: str) -> str | None:
    """Value of the GamePadEnable CVar in WTF/Config.wtf, or None when the file or line is absent."""
    try:
        text = open(os.path.join(wtf_dir, 'Config.wtf'), encoding='utf-8', errors='replace').read()
    except OSError:
        return None
    m = re.search(r'^SET GamePadEnable "([^"]*)"', text, re.M)
    return m.group(1) if m else None


def doctor(args) -> int:
    v = mac.macos_version()
    _p(OK if v else WARN, f'macOS {".".join(map(str, v)) if v else "(version unknown)"} on {mac.arch()}')
    _p(OK, f'Python {sys.version.split()[0]} at {sys.executable}')
    app = mac.battlenet_app()
    _p(OK if app else WARN, f'Battle.net: {app or "not installed (WoW Deck -> Set up opens the download page)"}')
    roots = mac.wow_roots()
    _p(OK if roots else WARN, f'World of Warcraft folder: {", ".join(roots) or "not found (install WoW in Battle.net, or set WOW_DECK_WOW_DIR)"}')
    wtfs = mac.wow_wtf_dirs(roots)
    _p(OK if wtfs else WARN, f'WoW installs: {len(wtfs)}')
    for d in wtfs:
        flavour = os.path.basename(os.path.dirname(d))
        present = [addons.MANIFEST[a]['title'] for a in addons.MANIFEST if addons.is_installed(a, [d])]
        _p(OK, f'  {flavour}: addons {", ".join(present) or "(none from WoW Deck)"}')
        gp = _gamepad_cvar(d)
        _p(OK if gp == '1' else WARN, f'  {flavour}: gamepad ' + ('enabled' if gp == '1' else
           'not enabled yet (ConsolePort turns it on, or /console GamePadEnable 1)' if gp is None else f'GamePadEnable = {gp}'))
    return 0


def setup(args) -> int:
    log_lines: list[str] = []
    def log(*a):
        line = ' '.join(str(x) for x in a); print(line, flush=True); log_lines.append(line)
    ctx = components.make_ctx(log)
    comps = components.COMPONENTS
    state = {c.id: c.detect(ctx) for c in comps}
    items = [(c.id, c.title + ('   [installed]' if state[c.id] else ''), state[c.id] or c.default, c.required) for c in comps]
    chosen = ui.checklist(ui.header('Set up World of Warcraft', 'Installed items are ticked; untick one to remove it.'), items)
    if chosen is None:
        print('cancelled'); return 1
    to_install = [c for c in comps if c.id in chosen and not state[c.id]]
    to_remove = [c for c in comps if c.id not in chosen and state[c.id] and not c.required]
    if to_remove and not ui.yesno('Remove: ' + ', '.join(c.title for c in to_remove) + '?'):
        to_remove = []
    if not to_install and not to_remove:
        ui.info('Everything selected is already installed. Nothing to do.'); return 0
    if mac.wow_running() and any(not c.required for c in to_install + to_remove):
        ui.error('World of Warcraft is running. Quit the game first, then run Set up again, so the addon changes are picked up.'); return 1
    failures = []
    def run_step(c, fn, verb):
        log(f'== {verb} {c.title}'); ui.note(f'{verb} {c.title}...')
        try:
            fn(ctx); return True
        except Exception as e:
            failures.append(f'{c.title}: {e}'); log(f'  FAILED {e}'); return False
    for c in to_remove:
        run_step(c, c.remove, 'Removing')
    bn = next((c for c in to_install if c.required), None)
    if bn:
        run_step(bn, bn.install, 'Checking')
    rest = [c for c in to_install if not c.required]
    if rest and not components.wow_installed(ctx):
        ui.info(('Battle.net is not installed yet: its download page is open in your browser. Install it, log in, '
                 if not mac.battlenet_app() else 'Battle.net is open. ')
                + 'Install World of Warcraft, start it once, then run Set up again to finish: '
                + ', '.join(c.title.replace('Install ', '') for c in rest) + '.')
        return 0
    for c in rest:
        run_step(c, c.install, 'Installing')
    summary = '\n'.join(l for l in log_lines if l.startswith('==') or '  FAILED' in l)
    if failures:
        ui.error('Setup finished with problems:\n\n' + '\n'.join(failures) + '\n\nDetails:\n' + summary); return 1
    ui.info('Setup complete.\n\n' + summary + '\n\nStart World of Warcraft from Battle.net.')
    return 0


def uninstall(args) -> int:
    """Remove every optional component WoW Deck installed; with --all also WoW Deck itself.
    Battle.net and World of Warcraft stay."""
    ctx = components.make_ctx(print)
    failures = []
    for c in components.COMPONENTS:
        if c.required or not c.detect(ctx):
            continue
        print(f'== Removing {c.title}')
        try:
            c.remove(ctx)
        except Exception as e:
            failures.append(f'{c.title}: {e}'); print(f'  FAILED {e}')
    if getattr(args, 'all', False):
        print('== Removing WoW Deck')
        for p in (USER_BIN_LINK, LAUNCHER):
            if os.path.lexists(p):
                os.remove(p); print(f'  removed {p}')
        if os.path.isdir(host.USER_DATA):
            shutil.rmtree(host.USER_DATA, ignore_errors=True); print(f'  removed {host.USER_DATA}')
    print('Done. Battle.net and World of Warcraft were left in place.' + ('' if not failures else '\nProblems: ' + '; '.join(failures)))
    return 1 if failures else 0


def help_cmd(args) -> int:
    from ..help import render_text
    print(render_text(min(96, shutil.get_terminal_size((80, 24)).columns - 2), mac_help.SECTIONS)); return 0


def hub(args) -> int:
    """WoW Deck menu on macOS (osascript dialogs, or text menus in a terminal without them)."""
    from ..help import render_text
    while True:
        app = mac.battlenet_app()
        items = [('setup', 'Set up / change installed components'), ('status', 'Check status (doctor)')]
        if app:
            items.append(('battlenet', 'Open Battle.net'))
        items += [('update', f'Check for WoW Deck updates (installed: {selfupdate.current_version()})'),
                  ('help', 'Help: what WoW Deck does'),
                  ('uninstall', 'Uninstall WoW Deck (addons and WoW Deck itself; Battle.net/WoW stay)'),
                  ('quit', 'Quit')]
        choice = ui.menu(ui.header('WoW Deck', 'World of Warcraft on the Mac, with ConsolePort.'), items)
        if choice in (None, 'quit'):
            return 0
        if choice == 'setup':
            setup(argparse.Namespace())
        elif choice == 'status':
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                doctor(argparse.Namespace())
            ui.textbox('Status', re.sub(r'\x1b\[[0-9;]*m', '', buf.getvalue()))
        elif choice == 'battlenet' and app:
            mac.open_app(app); ui.note('Battle.net starting...')
        elif choice == 'update':
            msg = selfupdate.check_and_update(log=print)
            ui.info(msg)
            if 'updated' in msg:
                return 0
        elif choice == 'help':
            ui.textbox('What WoW Deck does', render_text(90, mac_help.SECTIONS))
        elif choice == 'uninstall':
            if ui.yesno('Remove everything WoW Deck installed: the addons and WoW Deck itself?\n\nBattle.net and World of Warcraft stay.'):
                uninstall(argparse.Namespace(all=True)); return 0


def not_here(args) -> int:
    print(f'"wow-deck {args.cmd}" is part of the Steam Deck setup and does not apply on macOS. Try "wow-deck hub" or "wow-deck help".')
    return 2


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(prog='wow-deck', description='World of Warcraft with ConsolePort on macOS.')
    sub = ap.add_subparsers(dest='cmd')
    sub.add_parser('doctor', help='check every layer and report')
    sub.add_parser('hub', help='WoW Deck menu (setup + maintenance)').add_argument('--text', action='store_true', help=argparse.SUPPRESS)
    sub.add_parser('setup', help='guided, opt-in setup (dialogs)')
    pu = sub.add_parser('uninstall', help='remove the addons WoW Deck installed (--all: also WoW Deck itself)')
    pu.add_argument('--all', action='store_true', help='also remove WoW Deck itself (Battle.net/WoW stay)')
    sub.add_parser('help', help='explain what WoW Deck does')
    for cmd in STEAMOS_ONLY:
        sub.add_parser(cmd, help=argparse.SUPPRESS).add_argument('rest', nargs=argparse.REMAINDER)
    args = ap.parse_args(argv)
    if args.cmd in (None, 'doctor'):
        return doctor(args)
    return {'hub': hub, 'setup': setup, 'uninstall': uninstall, 'help': help_cmd,
            **{c: not_here for c in STEAMOS_ONLY}}[args.cmd](args)
