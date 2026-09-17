import argparse
import json
from pathlib import Path
import sys


def verify(source, package):
    sys.path.insert(0, str(source.resolve()))
    from hermes_cli.plugin_dev import doctor_plugin, _doctor_runtime
    report = doctor_plugin(str(package.resolve()))
    if not report.ok:
        raise RuntimeError(report.format_text())
    with _doctor_runtime(package.resolve()) as runtime:
        manager = runtime.manager
        skills = sorted(name for name in manager._plugin_skills if name.startswith('clipit:'))
        commands = sorted(name for name in manager._plugin_commands if name.startswith('clipit'))
        assert len(runtime.registered_tools) == 8
        assert len(skills) == 18
        assert commands == ['clipit', 'clipit-approvals', 'clipit-runs']
        assert manager._cli_commands['clipit']['plugin'] == 'clipit'
        assert manager.unload('clipit')
        assert not any(name.startswith('clipit:') for name in manager._plugin_skills)
        assert not any(name.startswith('clipit') for name in manager._plugin_commands)
        assert not any(name.startswith('clipit_') for name in manager._plugin_tool_names)
        assert 'clipit' not in manager._cli_commands
        home = Path(runtime.manifest.path).parent.parent
        sentinel = home / 'unrelated-user-file.txt'
        sentinel.write_text('preserve existing setup')
        manager.discover_and_load(force=True)
        assert not any(name.startswith('clipit_') for name in manager._plugin_tool_names)
        (home / 'config.yaml').write_text('plugins:\n  enabled: [clipit]\n')
        manager.discover_and_load(force=True)
        enabled = manager._plugins.get('clipit')
        assert enabled and enabled.enabled and len(enabled.tools_registered) == 8
        manager.unload('clipit')
        assert sentinel.read_text() == 'preserve existing setup'

    return {"doctor": "passed", "tools": 8, "skills": 18, "commands": 3, "cliCommands": 1, "unload": "passed",
            "consent": "disabled discovery inert; explicit enable registers tools", "unrelatedState": "preserved",
            "registrationNetwork": "blocked by upstream Doctor", "report": report.format_text()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--hermes-source', type=Path, required=True)
    parser.add_argument('--package', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    print(json.dumps(verify(args.hermes_source, args.package), indent=2))
