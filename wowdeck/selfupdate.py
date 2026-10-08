"""Self-update from the GitHub releases of nursh-bit/wow-deck (works once the repo is public;
a private repo returns 404 without a token). Replaces the app directory atomically."""
from __future__ import annotations
import io, json, os, shutil, tarfile, tempfile, urllib.error, urllib.request

REPO = 'nursh-bit/wow-deck'
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def current_version() -> str:
    try:
        return open(os.path.join(APP_DIR, 'VERSION')).read().strip()
    except OSError:
        return '0.0.0'


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={'User-Agent': 'wow-deck', 'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


NO_RELEASE = ('', '')            # the feed answered: nothing published (HTTP 404)


def latest_release() -> tuple[str, str] | None:
    """(version, tarball url), NO_RELEASE when the repository has no release, None when unreachable."""
    try:
        rel = json.loads(_get(f'https://api.github.com/repos/{REPO}/releases/latest'))
    except urllib.error.HTTPError as e:
        return NO_RELEASE if e.code == 404 else None
    except Exception:
        return None
    ver = rel.get('tag_name', '').lstrip('v')
    url = next((a['browser_download_url'] for a in rel.get('assets', []) if a['name'] == 'wow-deck.tar.gz'), None)
    return (ver, url) if ver and url else None


def _vtuple(v: str) -> tuple:
    return tuple(int(x) if x.isdigit() else 0 for x in v.split('.'))


def apply_update(tar_bytes: bytes, app_dir: str = APP_DIR, log=print) -> str:
    """Extract a release tarball (single top-level dir) over app_dir. Returns new version."""
    with tempfile.TemporaryDirectory(dir=os.path.dirname(app_dir)) as tmp:
        with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode='r:gz') as t:
            # regular files and folders only: a link member could point a later file outside tmp
            members = [m for m in t.getmembers() if (m.isfile() or m.isdir()) and not (m.name.startswith('/') or '..' in m.name.split('/'))]
            t.extractall(tmp, members=members, **({'filter': 'data'} if hasattr(tarfile, 'data_filter') else {}))
        tops = [d for d in os.listdir(tmp) if os.path.isdir(os.path.join(tmp, d))]
        src = os.path.join(tmp, tops[0]) if len(tops) == 1 and not os.path.exists(os.path.join(tmp, 'bin')) else tmp
        stage = app_dir + '.new'
        shutil.rmtree(stage, ignore_errors=True)
        shutil.copytree(src, stage)
        old = app_dir + '.old'
        shutil.rmtree(old, ignore_errors=True)
        os.rename(app_dir, old); os.rename(stage, app_dir)
        shutil.rmtree(old, ignore_errors=True)
    os.chmod(os.path.join(app_dir, 'bin', 'wow-deck'), 0o755)
    ver = open(os.path.join(app_dir, 'VERSION')).read().strip() if os.path.isfile(os.path.join(app_dir, 'VERSION')) else '?'
    log(f'  updated wow-deck -> {ver}')
    return ver


def check_and_update(log=print, fetch=_get) -> str:
    cur = current_version()
    latest = latest_release()
    if latest == NO_RELEASE:
        return f'wow-deck {cur}: no release has been published at github.com/{REPO} yet.'
    if not latest:
        return f'wow-deck {cur}: could not reach the release feed (offline?).'
    ver, url = latest
    if _vtuple(ver) <= _vtuple(cur):
        return f'wow-deck {cur} is up to date.'
    log(f'  downloading wow-deck {ver}')
    apply_update(fetch(url), log=log)
    return f'wow-deck updated {cur} -> {ver}. Restart WoW Deck to use it.'
