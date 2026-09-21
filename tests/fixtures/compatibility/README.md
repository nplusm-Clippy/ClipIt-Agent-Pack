# Portable installation compatibility evidence

`hermes-source.json` pins the released Hermes `v2026.9.14` source to commit
`345cd2b057a452236de401d3534b8502a7465e8d`. The three Python files are unchanged
copies of the upstream sources, with their SHA256 digests and original paths in
that record. `hermes-LICENSE` retains the upstream license.

The packaging tests compile selected path validators, reference extractors,
identifier parsing and command parser functions from those real source files.
Unrelated CLI JSON/yes flag helpers are stubbed. No installed Hermes runtime or
network access is needed. This proves parser and support-file compatibility;
it does not establish a published remote installation or native plugin load.

`agent-pack-2.0.0-baseline.json` records the untouched canonical Python scripts
at Agent Pack main `4401cb3f0f7131d679c6999817abd4a626f91810`, including all 52
executable entrypoints, and the existing 75 passing offline tests. It contains
source metadata only. Keep it frozen when adding new adapter functionality.

The generated `skills/` bundles have their own manifests recording the canonical
source and output hashes. Regenerate them with
`python3 tooling/build_portable_skills.py`; validate with `--check` and the Python
test suite. Only referenced documents/scripts and their local Python import
dependencies are included. The one prose normalization from
“missing assets/capabilities” to “missing assets and capabilities” prevents
Hermes from treating that sentence as a reference to a nonexistent support file.
