"""Regression tests for the 0.3.1 trust-and-correctness fixes."""
import io, os, tarfile, tempfile, zipfile
import pytest
from wowdeck import addons, battlenet, cli, files, selfupdate


def test_keeplist_has_only_wow_deck_entries():
    lines = [l for l in open(os.path.join(files.SHARE, 'wow-deck.conf')).read().splitlines() if l and not l.startswith('#')]
    assert all(l.startswith(('/etc/inputplumber', '/etc/systemd/system/multi-user.target.wants/inputplumber.service',
                             '/etc/atomic-update.conf.d/wow-deck.conf')) for l in lines), lines


def test_shipped_files_name_no_dev_machine_paths():
    for name in ('wow-deck.conf', 'GamePadConfig_SteamDeck.json'):
        assert 'wow-resources' not in open(os.path.join(files.SHARE, name)).read()


def test_update_verb_accepts_install_options(monkeypatch):
    seen = {}
    monkeypatch.setattr(cli, 'install', lambda args: seen.setdefault('args', args) and 0)
    cli.main(['update', '--dry-run'])
    assert seen['args'].dry_run and not seen['args'].skip_root


def test_finisher_accepts_any_flavour():
    with tempfile.TemporaryDirectory() as compat:
        assert not battlenet.wow_installed_in(compat)
        exe = os.path.join(compat, 'pfx', 'drive_c', 'Program Files (x86)', 'World of Warcraft', '_classic_era_', 'WowClassic.exe')
        os.makedirs(os.path.dirname(exe)); open(exe, 'w').close()
        assert battlenet.wow_installed_in(compat)


def _zip(folder):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        z.writestr(f'{folder}/{folder}.toc', '## Interface: 120000\n')
    return buf.getvalue()


def test_remove_leaves_addons_wow_deck_did_not_place(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setattr(addons, 'STATE', os.path.join(tmp, 'state.json'))
        wtf = os.path.join(tmp, 'World of Warcraft', '_retail_', 'WTF'); os.makedirs(wtf)
        mine = os.path.join(tmp, 'World of Warcraft', '_retail_', 'Interface', 'AddOns', 'BugSack')
        os.makedirs(mine)                                  # installed by the user, e.g. through CurseForge
        addons.remove('bugsack', [wtf], log=lambda *a: None)
        assert os.path.isdir(mine)
        addons.install_zip_bytes('bugsack', _zip('BugSack'), [wtf], log=lambda *a: None)
        addons.remove('bugsack', [wtf], log=lambda *a: None)
        assert not os.path.isdir(mine)                     # recorded by WoW Deck, so removed


def test_update_rejects_links_out_of_the_tree():
    with tempfile.TemporaryDirectory() as tmp:
        outside = os.path.join(tmp, 'outside'); os.makedirs(outside)
        app = os.path.join(tmp, 'app'); os.makedirs(os.path.join(app, 'bin'))
        open(os.path.join(app, 'bin', 'wow-deck'), 'w').write('old')
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode='w:gz') as t:
            for name, data in (('wow-deck-9/VERSION', '9\n'), ('wow-deck-9/bin/wow-deck', '#!/bin/sh\n')):
                info = tarfile.TarInfo(name); b = data.encode(); info.size = len(b); t.addfile(info, io.BytesIO(b))
            link = tarfile.TarInfo('wow-deck-9/escape'); link.type = tarfile.SYMTYPE; link.linkname = outside; t.addfile(link)
            info = tarfile.TarInfo('wow-deck-9/escape/pwned'); info.size = 1; t.addfile(info, io.BytesIO(b'x'))
        selfupdate.apply_update(buf.getvalue(), app, log=lambda *a: None)
        assert not os.path.exists(os.path.join(outside, 'pwned'))


def test_update_reports_missing_release_honestly(monkeypatch):
    monkeypatch.setattr(selfupdate, 'latest_release', lambda: selfupdate.NO_RELEASE)
    assert 'no release' in selfupdate.check_and_update(log=lambda *a: None).lower()


def test_installer_download_is_atomic(monkeypatch):
    class Boom:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self, n, _c=[0]):
            _c[0] += 1
            if _c[0] > 2: raise OSError('connection reset')
            return b'x' * (1 << 20)
    monkeypatch.setattr(battlenet.urllib.request, 'urlopen', lambda *a, **k: Boom())
    with tempfile.TemporaryDirectory() as tmp:
        with pytest.raises(OSError):
            battlenet.download_installer(tmp, log=lambda *a: None)
        assert not os.path.exists(os.path.join(tmp, 'Battle.net-Setup.exe'))
