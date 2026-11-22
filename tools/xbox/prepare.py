#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path
import subprocess
import sys

recipe = Path(__file__).resolve().parent
cache = Path(sys.argv[1]).resolve()
lock = json.loads((recipe / 'backend.lock.json').read_text())
local_patches = ['droiddeck-credentials.patch', 'droiddeck-launch-view.patch', 'droiddeck-library-subscriptions.patch',
                 'droiddeck-credential-fallback.patch', 'droiddeck-credential-diagnostics.patch', 'droiddeck-cloud-token.patch',
                 'droiddeck-licensing-device-ticket.patch', 'droiddeck-dlc-mount.patch',
                 'droiddeck-legacy-packages.patch', 'droiddeck-legacy-install.patch', 'droiddeck-legacy-run.patch',
                 'droiddeck-msixvc2.patch']
identity = hashlib.sha256((recipe / 'backend.lock.json').read_bytes() + b''.join((recipe / name).read_bytes() for name in local_patches)).hexdigest()
source = cache / ('source-' + identity[:16])
if not (source / '.prepared').is_file():
    if source.exists():
        raise RuntimeError('Incomplete Xbox source directory; inspect it before retrying: ' + str(source))
    source.mkdir(parents=True)
    # A host-mounted cache can report the host UID to Git running as container root.
    git = ['git', '-c', f'safe.directory={source}', '-C', str(source)]
    # Nexus keeps its Xodus changes as commits in its backend fork (since 0.2.15), not as patch files.
    subprocess.run([*git, 'init', '-q'], check=True)
    subprocess.run([*git, 'fetch', '-q', '--depth', '1', lock['repository'], lock['commit']], check=True)
    subprocess.run([*git, 'checkout', '-q', '--detach', 'FETCH_HEAD'], check=True)
    assert subprocess.check_output([*git, 'rev-parse', 'HEAD'], text=True).strip() == lock['commit']
    assert hashlib.sha256((source / 'Cargo.lock').read_bytes()).hexdigest() == lock['cargoLockSha256']
    for name in local_patches:
        subprocess.run([*git, 'apply', str(recipe / name)], check=True)
    (source / '.prepared').write_text(identity + '\n')
assert (source / '.prepared').read_text().strip() == identity
print(source)
