import argparse
import ast
import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
FORMAT = "clipit-portable-skills.v1"
FILE_REFERENCE = re.compile(r"(?<![A-Za-z0-9_:/<>-])(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_-]+\.(?:md|py|txt)(?![A-Za-z0-9_-])")
MAX_BUNDLE_BYTES = 1024 * 1024
MAX_PACK_BYTES = 10 * 1024 * 1024


def digest(content):
    return hashlib.sha256(content).hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def safe_relative(value):
    path = PurePosixPath(value)
    if not value or path.is_absolute() or "\\" in value or ":" in value:
        raise ValueError(f"Unsafe bundle path: {value}")
    if any(part in {"", ".", ".."} or part.startswith(".") for part in value.split("/")):
        raise ValueError(f"Unsafe bundle path: {value}")
    return path


def checked_path(root, relative):
    relative = safe_relative(relative)
    path = root
    for component in relative.parts:
        path = path / component
        if path.is_symlink():
            raise ValueError(f"Symlinks are not portable bundle inputs or outputs: {relative}")
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Path leaves bundle root: {relative}")
    return path


def source_files(root, manifest):
    sources = {"requirements.txt", "LICENSE"}
    for item in manifest["skills"]:
        skill_id = item["id"]
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", skill_id):
            raise ValueError(f"Invalid skill ID: {skill_id}")
        if item["path"] != f"clipper/{skill_id}":
            raise ValueError(f"Unexpected canonical skill path: {item['path']}")
        directory = checked_path(root, item["path"])
        sources.add(f"{item['path']}/SKILL.md")
        sources.update(path.relative_to(root).as_posix() for path in directory.glob("references/*.md"))
    sources.update(path.relative_to(root).as_posix() for path in (root / "scripts").glob("*.py"))
    for name in sources:
        checked_path(root, name)
    return sources


def resolve_reference(source, reference, sources):
    candidate = os.path.normpath(str(PurePosixPath(source).parent / reference)).replace("\\", "/")
    if candidate in sources:
        return candidate
    sibling_reference = str(PurePosixPath(source).parent / "references" / reference)
    if sibling_reference in sources:
        return sibling_reference
    if reference in sources:
        return reference
    if reference.endswith(".py") and "/" not in reference and f"scripts/{reference}" in sources:
        return f"scripts/{reference}"
    if reference == "requirements.txt":
        return reference
    raise ValueError(f"Unresolved file reference in {source}: {reference}")


def script_imports(content, sources):
    dependencies = set()
    for node in ast.walk(ast.parse(content)):
        modules = []
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules = [node.module]
        for module in modules:
            candidate = f"scripts/{module.split('.')[0]}.py"
            if candidate in sources:
                dependencies.add(candidate)
    return dependencies


def bundle_path(source, skill_path):
    path = PurePosixPath(source)
    if source == "LICENSE":
        return "references/LICENSE"
    if source == f"{skill_path}/SKILL.md":
        return "SKILL.md"
    if path.parts[0] == "clipper":
        prefix = "" if source.startswith(f"{skill_path}/") else f"{path.parts[1]}--"
        return f"references/{prefix}{path.name}"
    return source


def build_bundle(root, item, sources):
    skill_path = item["path"]
    pending = {f"{skill_path}/SKILL.md", "requirements.txt", "LICENSE"}
    contents = {}
    references = {}
    while pending:
        source = min(pending)
        pending.remove(source)
        if source in contents:
            continue
        data = checked_path(root, source).read_bytes()
        contents[source] = data
        if source.endswith(".md"):
            references[source] = {
                match.group(0): resolve_reference(source, match.group(0), sources)
                for match in FILE_REFERENCE.finditer(data.decode("utf-8"))
            }
            pending.update(set(references[source].values()) - contents.keys())
        elif source.endswith(".py"):
            pending.update(script_imports(data.decode("utf-8"), sources) - contents.keys())

    files = {}
    provenance = {}
    for source, original in sorted(contents.items()):
        target = bundle_path(source, skill_path)
        safe_relative(target)
        if target.casefold() in {name.casefold() for name in files}:
            raise ValueError(f"Bundle destination collision: {target}")
        data = original
        if source in references:
            def rewrite(match):
                dependency = references[source][match.group(0)]
                destination = bundle_path(dependency, skill_path)
                if destination.startswith("references/") and target.startswith("references/"):
                    return PurePosixPath(destination).name
                return destination
            data = FILE_REFERENCE.sub(rewrite, original.decode("utf-8")).encode("utf-8")
        files[target] = data
        provenance[target] = {"source": source, "sourceSha256": digest(original)}

    skill = files["SKILL.md"].decode("utf-8").replace("missing assets/capabilities", "missing assets and capabilities")
    title = re.search(r"^# .+$", skill, re.MULTILINE)
    if not title:
        raise ValueError(f"Missing skill title: {skill_path}")
    introduction = (
        "\n\nThis is a generated standalone bundle. Resolve shell commands and `scripts/` "
        "paths from this installed skill directory, or use absolute paths to its bundled scripts; "
        "a repository checkout is not required. Python fallbacks use "
        "[requirements.txt](requirements.txt). Install those dependencies in your chosen Python "
        "environment before running a fallback. The ClipIt CLI and MCP remain the preferred transports."
    )
    skill = skill[:title.end()] + introduction + skill[title.end():]
    support = sorted(name for name in files if name != "SKILL.md")
    support.append("references/bundle-manifest.json")
    skill += "\n## Bundled Support Files\n\nGenerated from canonical Agent Pack sources; do not edit these copies.\n\n"
    skill += "\n".join(f"- [{name}]({name})" for name in support) + "\n"
    files["SKILL.md"] = skill.encode("utf-8")
    bundle_manifest = {
        "format": FORMAT,
        "skillId": item["id"],
        "sourcePath": skill_path,
        "files": {
            name: {**provenance[name], "sha256": digest(data), "bytes": len(data)}
            for name, data in sorted(files.items())
        },
    }
    files["references/bundle-manifest.json"] = json_bytes(bundle_manifest)
    total = sum(len(data) for data in files.values())
    if total > MAX_BUNDLE_BYTES:
        raise ValueError(f"Bundle exceeds {MAX_BUNDLE_BYTES} bytes: {item['id']}")
    return files


def build_pack(root=ROOT):
    manifest = json.loads((root / "agent-pack.manifest.json").read_text(encoding="utf-8"))
    sources = source_files(root, manifest)
    files = {}
    records = []
    ids = [item["id"] for item in manifest["skills"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate skill IDs")
    for item in sorted(manifest["skills"], key=lambda entry: entry["id"]):
        bundle = build_bundle(root, item, sources)
        files.update({f"{item['id']}/{name}": data for name, data in bundle.items()})
        records.append({
            "id": item["id"],
            "path": item["id"],
            "sourcePath": item["path"],
            "manifestSha256": digest(bundle["references/bundle-manifest.json"]),
            "fileCount": len(bundle),
            "bytes": sum(len(data) for data in bundle.values()),
        })
    files["manifest.json"] = json_bytes({
        "format": FORMAT,
        "packVersion": manifest["packVersion"],
        "sourceManifestSha256": digest((root / "agent-pack.manifest.json").read_bytes()),
        "skills": records,
    })
    if sum(len(data) for data in files.values()) > MAX_PACK_BYTES:
        raise ValueError(f"Pack exceeds {MAX_PACK_BYTES} bytes")
    return files


def verify_output(output, files):
    actual = {}
    if output.is_symlink():
        raise ValueError("Output directory cannot be a symlink")
    if output.exists():
        for path in output.rglob("*"):
            name = path.relative_to(output).as_posix()
            checked_path(output, name)
            if path.is_file():
                actual[name] = path.read_bytes()
    return sorted(name for name in actual.keys() | files.keys() if actual.get(name) != files.get(name))


def write_output(output, files):
    differences = verify_output(output, files)
    if not differences:
        return
    if output.exists():
        extras = [path for path in output.rglob("*") if path.is_file() and path.relative_to(output).as_posix() not in files]
        if extras:
            raise ValueError("Output contains stale or unrelated files; move the generated directory aside before rebuilding")
    for name, data in sorted(files.items()):
        target = checked_path(output, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


def main():
    parser = argparse.ArgumentParser(description="Build self-contained skills from canonical ClipIt sources")
    parser.add_argument("--output", type=Path, default=ROOT / "skills")
    parser.add_argument("--check", action="store_true", help="Verify generated files without writing")
    args = parser.parse_args()
    try:
        files = build_pack()
        if args.check:
            differences = verify_output(args.output, files)
            if differences:
                parser.exit(1, f"Portable bundles are missing or stale ({len(differences)} files). Run tooling/build_portable_skills.py.\n")
        else:
            write_output(args.output, files)
    except (ValueError, OSError) as exc:
        parser.exit(1, f"Portable bundle build failed: {exc}\n")
    print(f"Portable bundles: {len(files)} files, {sum(len(data) for data in files.values())} bytes; {'verified' if args.check else 'built'}")


if __name__ == "__main__":
    main()
