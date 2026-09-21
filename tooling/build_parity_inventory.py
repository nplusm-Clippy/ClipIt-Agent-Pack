import argparse
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'docs' / 'capability-inventory.json'


def inventory():
    manifest = json.loads((ROOT / 'agent-pack.manifest.json').read_text())
    scripts = []
    for path in sorted((ROOT / 'scripts').glob('*.py')):
        source = path.read_text()
        tree = ast.parse(source)
        arguments, requests = [], []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr == 'add_argument':
                arguments.append({'flags': [ast.literal_eval(arg) for arg in node.args if isinstance(arg, ast.Constant)],
                                  'options': {kw.arg: ast.get_source_segment(source, kw.value) for kw in node.keywords}})
            if node.func.attr in {'get', 'post', 'put', 'patch', 'delete', 'request'} and node.args:
                target = ast.get_source_segment(source, node.args[0])
                if '/api/' in target:
                    requests.append({'method': node.func.attr.upper(), 'pathExpression': target, 'line': node.lineno})
        scripts.append({'path': path.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                        'entrypoint': '__name__' in source, 'arguments': arguments, 'requests': requests,
                        'retainedFallback': 'Run this unchanged Python entrypoint with its existing CLI profile and arguments.',
                        'policy': 'Existing public endpoint permission, cost, confirmation and exact-result rules remain authoritative.'})
    skills = []
    for item in manifest['skills']:
        bundle = json.loads((ROOT / 'skills' / item['id'] / 'references' / 'bundle-manifest.json').read_text())
        skills.append({**item, 'canonicalSha256': hashlib.sha256((ROOT / item['path'] / 'SKILL.md').read_bytes()).hexdigest(),
                       'nativeSkill': 'clipit:' + item['id'], 'portableSkill': 'skills/' + item['id'],
                       'includedScripts': sorted({v['source'] for v in bundle['files'].values() if v['source'].startswith('scripts/')}),
                       'nativeRoute': 'clipit_discover -> live capability; clipit_execute or clipit_orchestrate; retain exact Python fallback when no equivalent live tool exists.'})
    return {'schema': 'clipit-capability-inventory.v1', 'packVersion': manifest['packVersion'],
            'capabilityContract': manifest['capabilityContractVersion'], 'skillCount': len(skills), 'pythonFileCount': len(scripts), 'scriptCount': sum(item['entrypoint'] for item in scripts),
            'executionPolicy': 'One mutation owner. A native receipt never licenses replay through a legacy transport.',
            'skills': skills, 'scripts': scripts}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    content = json.dumps(inventory(), indent=2) + '\n'
    if args.check:
        if not TARGET.exists() or TARGET.read_text() != content:
            raise SystemExit('Capability inventory is stale; regenerate it.')
    else:
        TARGET.write_text(content)
    print(json.dumps({'skills': 18, 'scripts': inventory()['scriptCount'], 'check': args.check}))
