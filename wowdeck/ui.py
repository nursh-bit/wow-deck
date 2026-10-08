"""Dialogs for the guided setup: kdialog (KDE, present on SteamOS), zenity fallback, osascript
on macOS, plain text fallback when no display. Keep the surface tiny: checklist, info, yesno,
progress note."""
from __future__ import annotations
import os, shutil, subprocess, sys
from . import host

TITLE = 'WoW Deck'
BRANDING = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'share', 'branding')
LOGO = os.path.join(BRANDING, 'logo.png')


def header(text: str, sub: str = '') -> str:
    """Rich-text header for kdialog (Qt labels render local <img>). Plain text elsewhere."""
    if backend() != 'kdialog':
        return text + ('\n' + sub if sub else '')
    img = f'<img src="{LOGO}" width="72">' if os.path.isfile(LOGO) else ''
    return (f'<table><tr><td valign="middle">{img}</td><td valign="middle" style="padding-left:12px">'
            f'<h2 style="margin:0">{text}</h2>' + (f'<p style="margin:0">{sub}</p>' if sub else '') + '</td></tr></table>')


def _icon_args() -> list[str]:
    return ['--icon', LOGO] if os.path.isfile(LOGO) else []


def _has_display() -> bool:
    return bool(os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY'))


def backend() -> str:
    if host.is_macos():
        return 'osascript' if shutil.which('osascript') else 'text'
    if not _has_display():
        return 'text'
    for b in ('kdialog', 'zenity'):
        if shutil.which(b):
            return b
    return 'text'


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def _osa(lines: list[str], *argv: str) -> subprocess.CompletedProcess:
    """Run an AppleScript `on run argv` handler. Text goes in as arguments, never spliced into
    the script, so quotes and backslashes in messages need no escaping."""
    cmd = ['osascript']
    for line in ['on run argv', *lines, 'end run']:
        cmd += ['-e', line]
    return _run(cmd + list(argv))


_OSA_CANCEL = '__wow_deck_cancel__'
# choose from list: argv = prompt, title, count, labels..., default labels...
_OSA_CHOOSE = ['set n to (item 3 of argv) as integer',
               'set labels to items 4 thru (3 + n) of argv',
               'if (count of argv) > (3 + n) then',
               'set defs to items (4 + n) thru -1 of argv',
               'else',
               'set defs to {}',
               'end if',
               'set r to choose from list labels with title (item 2 of argv) with prompt (item 1 of argv) default items defs {multi}',
               f'if r is false then return "{_OSA_CANCEL}"',
               "set AppleScript's text item delimiters to linefeed",
               'return r as text']


def _osa_choose(prompt: str, labels: list[str], defaults: list[str], multiple: bool) -> list[str] | None:
    lines = [l.replace('{multi}', 'with multiple selections allowed and empty selection allowed' if multiple else '') for l in _OSA_CHOOSE]
    r = _osa(lines, prompt, TITLE, str(len(labels)), *labels, *defaults)
    out = r.stdout.rstrip('\n')
    if r.returncode != 0 or out == _OSA_CANCEL:
        return None
    return [l for l in out.split('\n') if l]


def checklist(prompt: str, items: list[tuple[str, str, bool, bool]]) -> list[str] | None:
    """items: (id, label, checked, required). Returns chosen ids, or None if cancelled.
    Required items are always included and marked in the label."""
    b = backend()
    if b == 'kdialog':
        args = ['kdialog', '--title', TITLE, *_icon_args(), '--checklist', prompt]
        for id_, label, checked, req in items:
            args += [id_, label + ('  (required)' if req else ''), 'on' if (checked or req) else 'off']
        r = _run(args)
        if r.returncode != 0:
            return None
        chosen = [t.strip('"') for t in r.stdout.strip().split()]
    elif b == 'zenity':
        args = ['zenity', '--list', '--checklist', '--title', TITLE, '--text', prompt, '--column', '', '--column', 'id', '--column', 'Component', '--hide-column=2', '--print-column=2', '--separator=\n', '--height=360', '--width=560']
        for id_, label, checked, req in items:
            args += ['TRUE' if (checked or req) else 'FALSE', id_, label + ('  (required)' if req else '')]
        r = _run(args)
        if r.returncode != 0:
            return None
        chosen = [t for t in r.stdout.strip().split('\n') if t]
    elif b == 'osascript':
        labels = {label + ('  (required)' if req else ''): id_ for id_, label, _, req in items}
        defaults = [l for l, (_, _, checked, req) in zip(labels, items) if checked or req]
        picked = _osa_choose(prompt, list(labels), defaults, multiple=True)
        if picked is None:
            return None
        chosen = [labels[l] for l in picked if l in labels]
    else:
        print(f'\n{prompt}')
        for i, (id_, label, checked, req) in enumerate(items, 1):
            print(f'  {i}. [{"x" if (checked or req) else " "}] {label}{"  (required)" if req else ""}')
        ans = input('Numbers to toggle (space separated), Enter to continue, q to quit: ').strip()
        if ans.lower() == 'q':
            return None
        toggles = {int(x) for x in ans.split() if x.isdigit()}
        chosen = [id_ for i, (id_, _, checked, req) in enumerate(items, 1) if req or (checked != (i in toggles))]
    for id_, _, _, req in items:
        if req and id_ not in chosen:
            chosen.append(id_)
    return chosen


def info(text: str) -> None:
    b = backend()
    if b == 'kdialog':
        _run(['kdialog', '--title', TITLE, *_icon_args(), '--msgbox', text])
    elif b == 'zenity':
        _run(['zenity', '--info', '--title', TITLE, '--text', text, '--width=520'])
    elif b == 'osascript':
        _osa(['display dialog (item 1 of argv) with title (item 2 of argv) buttons {"OK"} default button "OK"'], text, TITLE)
    else:
        print(text)


def error(text: str) -> None:
    b = backend()
    if b == 'kdialog':
        _run(['kdialog', '--title', TITLE, *_icon_args(), '--error', text])
    elif b == 'zenity':
        _run(['zenity', '--error', '--title', TITLE, '--text', text, '--width=520'])
    elif b == 'osascript':
        _osa(['display dialog (item 1 of argv) with title (item 2 of argv) buttons {"OK"} default button "OK" with icon stop'], text, TITLE)
    else:
        print('ERROR:', text, file=sys.stderr)


def yesno(text: str) -> bool:
    b = backend()
    if b == 'kdialog':
        return _run(['kdialog', '--title', TITLE, *_icon_args(), '--yesno', text]).returncode == 0
    if b == 'zenity':
        return _run(['zenity', '--question', '--title', TITLE, '--text', text, '--width=520']).returncode == 0
    if b == 'osascript':
        r = _osa(['display dialog (item 1 of argv) with title (item 2 of argv) buttons {"No", "Yes"} default button "Yes"',
                  'return button returned of result'], text, TITLE)
        return r.returncode == 0 and r.stdout.strip() == 'Yes'
    return input(f'{text} [y/N] ').strip().lower().startswith('y')


def note(text: str) -> None:
    """Non-blocking progress note (desktop notification) plus stdout."""
    print(text, flush=True)
    if backend() == 'osascript':
        subprocess.Popen(['osascript', '-e', 'on run argv', '-e', 'display notification (item 1 of argv) with title (item 2 of argv)',
                          '-e', 'end run', text, TITLE], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif _has_display() and shutil.which('notify-send'):
        subprocess.Popen(['notify-send', '-a', TITLE, TITLE, text], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def menu(prompt: str, items: list[tuple[str, str]]) -> str | None:
    """items: (id, label). Returns chosen id or None."""
    b = backend()
    if b == 'kdialog':
        args = ['kdialog', '--title', TITLE, *_icon_args(), '--menu', prompt]
        for id_, label in items:
            args += [id_, label]
        r = _run(args)
        return r.stdout.strip() or None if r.returncode == 0 else None
    if b == 'zenity':
        args = ['zenity', '--list', '--title', TITLE, '--text', prompt, '--column', 'id', '--column', 'Action', '--hide-column=1', '--print-column=1', '--height=360', '--width=520']
        for id_, label in items:
            args += [id_, label]
        r = _run(args)
        return r.stdout.strip() or None if r.returncode == 0 else None
    if b == 'osascript':
        labels = {label: id_ for id_, label in items}
        picked = _osa_choose(prompt, list(labels), [], multiple=False)
        return labels.get(picked[0]) if picked else None
    print(f'\n{prompt}')
    for i, (id_, label) in enumerate(items, 1):
        print(f'  {i}. {label}')
    ans = input('Choice (Enter to quit): ').strip()
    return items[int(ans) - 1][0] if ans.isdigit() and 0 < int(ans) <= len(items) else None


def password(prompt: str) -> str | None:
    b = backend()
    if b == 'kdialog':
        r = _run(['kdialog', '--title', TITLE, *_icon_args(), '--password', prompt])
        return r.stdout.rstrip('\n') if r.returncode == 0 else None
    if b == 'zenity':
        r = _run(['zenity', '--password', '--title', TITLE])
        return r.stdout.rstrip('\n') if r.returncode == 0 else None
    if b == 'osascript':
        r = _osa(['display dialog (item 1 of argv) with title (item 2 of argv) default answer "" with hidden answer',
                  'return text returned of result'], prompt, TITLE)
        return r.stdout.rstrip('\n') if r.returncode == 0 else None
    import getpass
    return getpass.getpass(prompt + ' ')


def textbox(title: str, text: str) -> None:
    b = backend()
    if b == 'kdialog':
        import tempfile
        with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False) as f:
            f.write(text); path = f.name
        _run(['kdialog', '--title', f'{TITLE}: {title}', '--textbox', path, '640', '420'])
    elif b == 'zenity':
        r = subprocess.run(['zenity', '--text-info', '--title', f'{TITLE}: {title}', '--width=640', '--height=420'], input=text, text=True, capture_output=True)
    elif b == 'osascript':
        import tempfile
        with tempfile.NamedTemporaryFile('w', prefix='wow-deck-', suffix='.txt', delete=False) as f:
            f.write(f'{TITLE}: {title}\n\n{text}'); path = f.name
        _run(['open', '-t', path])          # default text editor
    else:
        print(f'== {title}\n{text}')
