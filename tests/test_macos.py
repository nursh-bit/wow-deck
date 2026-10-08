import argparse, os, subprocess
from wowdeck import addons, host, ui
from wowdeck.macos import cli as mcli, components as mcomp, mac


def _wow(tmp, *flavours):
    root = os.path.join(tmp, 'World of Warcraft')
    for fl, app in flavours:
        os.makedirs(os.path.join(root, fl, app))
    return root


def test_platform_override(monkeypatch):
    monkeypatch.setenv('WOW_DECK_PLATFORM', 'macos')
    assert host.is_macos()
    assert host.user_data('/Users/x') == '/Users/x/Library/Application Support/wow-deck'
    monkeypatch.setenv('WOW_DECK_PLATFORM', 'steamos')
    assert host.user_data('/home/deck') == '/home/deck/.local/share/wow-deck'


def test_wow_discovery(tmp_path):
    root = _wow(str(tmp_path), ('_retail_', 'World of Warcraft.app'), ('_classic_era_', 'World of Warcraft Classic.app'))
    os.makedirs(os.path.join(root, '_ptr_'))                 # no game app: not a flavour
    assert [os.path.basename(d) for d in mac.wow_flavour_dirs([root])] == ['_classic_era_', '_retail_']
    assert mac.wow_wtf_dirs([root]) == [os.path.join(root, f, 'WTF') for f in ('_classic_era_', '_retail_')]


def test_wow_dir_override(tmp_path, monkeypatch):
    root = _wow(str(tmp_path), ('_retail_', 'World of Warcraft.app'))
    monkeypatch.setenv('WOW_DECK_WOW_DIR', root)
    assert mac.wow_roots() == [root]


def test_shared_addon_components_on_macos_layout(tmp_path, monkeypatch):
    monkeypatch.setattr(addons, 'STATE', str(tmp_path / 'state.json'))
    root = _wow(str(tmp_path), ('_retail_', 'World of Warcraft.app'))
    ctx = mcomp.Ctx(mac.wow_wtf_dirs([root]), log=lambda *a: None)
    bugs = next(c for c in mcomp.COMPONENTS if c.id == 'bugs')
    monkeypatch.setattr(addons, 'install', lambda i, d, log=print: addons.install_zip_bytes(i, _zip(addons.MANIFEST[i]['folders']), d, log))
    bugs.install(ctx)
    assert bugs.detect(ctx)
    assert os.path.isdir(os.path.join(root, '_retail_', 'Interface', 'AddOns', 'BugSack'))
    bugs.remove(ctx)
    assert not bugs.detect(ctx)


def _zip(folders):
    import io, zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        for f in folders:
            z.writestr(f'{f}/{f}.toc', '## Interface: 120000\n')
    return buf.getvalue()


def test_gamepad_cvar(tmp_path):
    (tmp_path / 'Config.wtf').write_text('SET locale "enUS"\nSET GamePadEnable "1"\n')
    assert mcli._gamepad_cvar(str(tmp_path)) == '1'
    assert mcli._gamepad_cvar(str(tmp_path / 'missing')) is None


def test_osascript_checklist_maps_labels_to_ids(monkeypatch):
    monkeypatch.setenv('WOW_DECK_PLATFORM', 'macos')
    monkeypatch.setattr(ui.shutil, 'which', lambda b: '/usr/bin/osascript')
    seen = {}
    def fake_run(cmd):
        seen['cmd'] = cmd
        return subprocess.CompletedProcess(cmd, 0, 'Battle.net  (required)\nInstall ConsolePort\n', '')
    monkeypatch.setattr(ui, '_run', fake_run)
    items = [('battlenet', 'Battle.net', False, True), ('consoleport', 'Install ConsolePort', True, False), ('bugs', 'Bugs', False, False)]
    assert ui.checklist('Pick', items) == ['battlenet', 'consoleport']
    argv = seen['cmd'][seen['cmd'].index('end run') + 1:]
    assert argv == ['Pick', ui.TITLE, '3', 'Battle.net  (required)', 'Install ConsolePort', 'Bugs', 'Battle.net  (required)', 'Install ConsolePort']


def test_osascript_cancel(monkeypatch):
    monkeypatch.setenv('WOW_DECK_PLATFORM', 'macos')
    monkeypatch.setattr(ui.shutil, 'which', lambda b: '/usr/bin/osascript')
    monkeypatch.setattr(ui, '_run', lambda cmd: subprocess.CompletedProcess(cmd, 0, ui._OSA_CANCEL + '\n', ''))
    assert ui.menu('Pick', [('a', 'A')]) is None


def test_steamos_only_verbs_refuse(monkeypatch, capsys):
    monkeypatch.setenv('WOW_DECK_PLATFORM', 'macos')
    from wowdeck.cli import main
    assert main(['paddles', 'on']) == 2
    assert 'does not apply on macOS' in capsys.readouterr().out
