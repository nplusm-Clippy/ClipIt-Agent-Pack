import argparse
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile


def verify(source, package):
    source, package = source.resolve(), package.resolve()
    with tempfile.TemporaryDirectory(prefix='clipit-hermes-install-') as temporary:
        root = Path(temporary)
        os.environ['HERMES_HOME'] = str(root / 'home')
        os.environ['CLIPPER_API_KEY'] = 'offline-install-probe-not-a-key'
        Path(os.environ['HERMES_HOME']).mkdir()
        sentinel = Path(os.environ['HERMES_HOME']) / 'owner-notes.txt'
        sentinel.write_text('preserve unrelated files')
        snapshot = root / 'source'
        snapshot.mkdir()
        paths = subprocess.check_output(['git', '-C', str(package), 'ls-files', '-z']).decode().split('\0')
        for name in filter(None, paths):
            path = package / name
            assert not path.is_symlink(), name
            destination = snapshot / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
        for arguments in [('init', '-q'), ('add', '.'), ('-c', 'user.name=Install probe', '-c', 'user.email=probe@localhost', 'commit', '-qm', 'Reviewed local installation snapshot')]:
            subprocess.run(['git', '-C', str(snapshot), *arguments], check=True, capture_output=True)
        revision = subprocess.check_output(['git', '-C', str(snapshot), 'rev-parse', 'HEAD']).decode().strip()
        sys.path.insert(0, str(source))
        from hermes_cli import plugins_cmd
        from hermes_cli.plugins_manifest import parse_manifest_file, version_satisfies
        from tools.plugin_guard import scan_plugin
        from tools.skills_guard import scan_skill, should_allow_install
        from tools.skills_hub_github import GitHubSource
        from tools.skills_hub_install import quarantine_bundle, install_from_quarantine

        scan = scan_plugin(snapshot, source='local reviewed candidate')
        assert scan.verdict != 'dangerous', scan.summary
        assert all(f.severity not in {'critical', 'high'} or (f.pattern_id == 'path_traversal_deep' and f.file == 'tests/test_portable_skill_bundles.py') for f in scan.findings), 'Review new high-severity installer findings before accepting them'
        findings = [{'pattern': f.pattern_id, 'severity': f.severity, 'file': f.file, 'line': f.line} for f in scan.findings]
        def deny_network(*args, **kwargs):
            raise AssertionError('Clean installation must not contact ClipIt or a provider')
        socket.socket.connect = deny_network
        socket.socket.connect_ex = deny_network
        socket.socket.sendto = deny_network
        with contextlib.redirect_stdout(io.StringIO()):
            installed, manifest, name = plugins_cmd._install_plugin_core(
                snapshot.as_uri(), force=False, ref=revision,
                scan_decision_cb=lambda result: result.verdict == 'caution' and [vars(item) for item in result.findings] == [vars(item) for item in scan.findings])
        assert name == 'clipit'
        assert plugins_cmd.pinned_revision(name) == revision
        assert not plugins_cmd._config_name_set('plugins', 'enabled')
        parsed = parse_manifest_file(installed / 'plugin.yaml', installed, 'user', '')
        assert parsed.manifest_version == 1
        assert parsed.requires_hermes == '>=0.21.3'
        assert not version_satisfies(parsed.requires_hermes, '0.21.2')
        assert parsed.requires_env == manifest['requires_env']
        assert parsed.python_dependencies == manifest['python_dependencies']
        assert parsed.provides_tools == manifest['provides_tools'] and len(parsed.provides_tools) == 8
        assert parsed.capabilities == []
        assert (installed / 'desktop/plugin.js').read_bytes() == (package / 'desktop/plugin.js').read_bytes()
        assert (installed / 'dashboard/plugin_api.py').is_file()
        plugins_cmd._set_plugin_enabled(name, enable=True)
        assert 'clipit' in plugins_cmd._config_name_set('plugins', 'enabled')
        plugins_cmd._set_plugin_enabled(name, enable=False)
        assert 'clipit' not in plugins_cmd._config_name_set('plugins', 'enabled')

        entries = [{'path': name, 'type': 'blob', 'mode': '100644'} for name in paths if name]
        github = GitHubSource(auth=None, extra_taps=[])
        github._tree_revisions['nplusm-Clippy/ClipIt-Agent-Pack'] = revision
        github._get_repo_tree = lambda repo: (revision, entries)
        def local_content(repo, path, ref=None):
            assert repo == 'nplusm-Clippy/ClipIt-Agent-Pack' and ref == revision
            target = (snapshot / path).resolve()
            assert target.is_relative_to(snapshot)
            return target.read_bytes() if target.is_file() else None
        github._fetch_file_bytes = local_content
        skills = []
        for item in json.loads((package / 'agent-pack.manifest.json').read_text())['skills']:
            skill = item['id']
            bundle = github.fetch(f'nplusm-Clippy/ClipIt-Agent-Pack/skills/{skill}')
            assert bundle is not None, skill
            quarantined = quarantine_bundle(bundle)
            result = scan_skill(quarantined, source='community')
            assert should_allow_install(result)[0] is True, result.summary
            target = install_from_quarantine(quarantined, skill, '', bundle, result)
            expected = {p.relative_to(package / 'skills' / skill).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in (package / 'skills' / skill).rglob('*') if p.is_file()}
            actual = {p.relative_to(target).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in target.rglob('*') if p.is_file()}
            assert expected == actual, skill
            skills.append({'name': skill, 'files': len(actual), 'scan': result.verdict})
        assert sentinel.read_text() == 'preserve unrelated files'
        return {'hermesSource': subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD']).decode().strip(),
                'packageSource': subprocess.check_output(['git', '-C', str(package), 'rev-parse', 'HEAD']).decode().strip(),
                'transport': 'local Git snapshot and GitHub file-transport fixture; real installer, parser, scanner, quarantine and skill installer',
                'native': {'installed': True, 'pinned': True, 'initiallyDisabled': True, 'enableDisable': 'passed', 'manifestFieldsPreserved': True, 'desktopBytesPreserved': True, 'scan': scan.verdict, 'findings': findings},
                'portable': skills, 'unrelatedFiles': 'preserved', 'providerNetwork': 'blocked'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--hermes-source', type=Path, required=True)
    parser.add_argument('--package', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    print(json.dumps(verify(args.hermes_source, args.package), indent=2))
