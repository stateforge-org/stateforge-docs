# StateForge Docs

Shared documentation infrastructure for the StateForge project.

This repository produces the `stateforge-docs-theme` Python distribution. It
extends Material for MkDocs with StateForge branding, shared presentation
components, and build-time validation. Documentation content remains in the
repository that owns it.

## Interactive procedures

The theme includes a declarative procedure player for explaining interactions
between any number of ordered entities. Processes, services, storage,
resources, external systems, and users can participate in the same flow. Each
step declares its active entities, concurrent transitions, internal activity,
shared context, success paths, and failure paths. The renderer contains no
Agent, Provider, Bootstrap, or other procedure-specific topology.

Documentation versions come exclusively from the source directory. The whole
site for a release lives below that version, including its procedure pages and
declarations:

```text
docs/
├── v0.1.0/
│   ├── index.md
│   ├── bootstrap.md
│   └── procedures/
│       └── bootstrap.yaml
└── v0.2.0/
    └── ...
```

The filename stays `bootstrap.yaml`. A declaration must not contain a
`version`, `protocol_version`, or `documentation_version` field. The build
derives `v0.1.0` from the documentation tree and rejects ambiguous or missing
version locations.

Embed a declaration from Markdown:

````markdown
```stateforge-procedure
source: procedures/bootstrap.yaml
scenario: success
```
````

The source path is relative to the Markdown page and must remain within the
MkDocs `docs_dir`. Builds reject traversal, oversized declarations, unknown
fields, malformed actors, invalid scenarios, and unsafe inline data. The
generated page contains a static ordered fallback before JavaScript enhances
it into the interactive player.

## Consumer configuration

```yaml
theme:
  name: stateforge

plugins:
  - search
  - stateforge:
      component: protocol
```

Supported component identities are `stateforge`, `agent`, `provider`,
`protocol`, `control-plane`, and `sf-aop`.

## Development

```bash
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/ruff format --check .
.venv/bin/ruff check .
.venv/bin/mypy src
.venv/bin/pytest
```
