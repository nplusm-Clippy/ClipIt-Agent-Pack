import argparse
import hashlib
import json
import subprocess
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
FILES = {"__init__.py", "plugin.yaml", "agent-pack.manifest.json", "requirements.txt", "README.md", "AGENTS.md", "CLAUDE.md", "LICENSE"}
DIRECTORIES = {"clipit_plugin", "clipper", "skills", "scripts", "dashboard", "desktop", "docs"}


def release_files(root=ROOT):
    files = []
    selected = [root / name for name in sorted(FILES) if (root / name).exists()]
    for name in sorted(DIRECTORIES):
        directory = root / name
        if directory.is_symlink():
            raise ValueError("Release packages may not contain symbolic links")
        if directory.exists():
            selected.extend(directory.rglob("*"))
    for path in selected:
        relative = path.relative_to(root)
        if relative.parts[0] not in DIRECTORIES and relative.as_posix() not in FILES:
            continue
        if any(part.startswith('.') or part == '__pycache__' for part in relative.parts):
            continue
        if path.is_symlink():
            raise ValueError("Release packages may not contain symbolic links")
        if path.is_file() and path.suffix not in {".pyc", ".pyo"}:
            files.append((relative.as_posix(), path.read_bytes()))
    return sorted(files)


def build(output, root=ROOT):
    manifest = json.loads((root / 'agent-pack.manifest.json').read_text())
    files = release_files(root)
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in files}
    try:
        source_head = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], stderr=subprocess.DEVNULL, text=True).strip()
        dirty = bool(subprocess.check_output(['git', '-C', str(root), 'status', '--porcelain'], stderr=subprocess.DEVNULL, text=True).strip())
    except (OSError, subprocess.CalledProcessError):
        source_head, dirty = None, None
    record = {"sourceHead": source_head, "uncommittedCandidate": dirty, "version": manifest['packVersion'], "contractVersion": manifest['platformContractVersion'],
              "files": hashes, "fileCount": len(files), "bytes": sum(len(data) for _, data in files)}
    output.mkdir(parents=True, exist_ok=True)
    target = output / f"clipit-agent-pack-{manifest['packVersion']}.zip"
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in files + [('release-manifest.json', (json.dumps(record, indent=2) + '\n').encode())]:
            info = zipfile.ZipInfo('clipit/' + name, date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    record['archiveSha256'] = hashlib.sha256(target.read_bytes()).hexdigest()
    (output / 'release-manifest.json').write_text(json.dumps(record, indent=2) + '\n')
    return {"archive": str(target), "sha256": record['archiveSha256'], "fileCount": len(files)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    arguments = parser.parse_args()
    print(json.dumps(build(arguments.output)))
