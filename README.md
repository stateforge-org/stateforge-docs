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

## Interactive lifecycle summaries

Landing pages may use the compact lifecycle component when two endpoints
exchange a short, ordered series of messages. The visible stage buttons remain
the complete static explanation. With JavaScript enabled, selecting a stage
updates the endpoint states and plays its declared messages once.

Each `[data-sf-flow-step]` button declares:

- `data-source-state` and `data-target-state` for the endpoint summaries;
- `data-result` for the stable state reached after playback; and
- `data-events` as a JSON array of `direction`, `label`, and `detail` values.

`forward` moves from source to target and `reverse` moves from target to source.
The component uses native buttons, reports the selected stage with
`aria-pressed`, exposes one polite live status, and skips playback when the
visitor requests reduced motion. The shared script contains no
repository-specific actors or messages.

## Declarative entity flows

Use an entity flow for a compact, animated explanation of one responsibility
transfer across several real components. The renderer, interaction controls,
accessibility behavior, StateForge branding, and bundled third-party marks live
in this package. The owning repository supplies only version-local YAML.

````markdown
```stateforge-entity-flow
source: trigger-publication-overview.yaml
```
````

An entity declaration describes identity, visual role, and initial state. Each
step declares the active entities, state changes, directed transitions, and
the exact owner of responsibility at that point:

```yaml
schema: stateforge.docs/entity-flow/v1
flow: trigger-publication
title: Trigger publication responsibility flow
entities:
  - id: provider
    label: Example Provider
    kind: StateForge Provider
    brand: stateforge
    accent: provider
    state: {label: Pending queue, value: Empty}
  - id: agent
    label: StateForge Agent
    kind: StateForge Agent
    brand: stateforge
    accent: agent
    state: {label: Trigger record, value: Not accepted}
steps:
  - id: publish
    phase: Trigger publication
    title: Publish the trigger
    detail: The Provider retains the publication while sending it.
    active: [provider, agent]
    states:
      provider: {label: Pending queue, value: 1 retained publication}
    transitions:
      - {source: provider, target: agent, label: TriggerPublication}
    responsibility:
      entities: [provider]
      label: The Provider remains responsible until durable acceptance.
```

Supported bundled brands are `stateforge`, `service`, and `none`. `service` is
a neutral service glyph for factual product references; `none` uses a compact
text mark derived from the entity label.

## Consumer configuration

```yaml
theme:
  name: stateforge

plugins:
  - material/search
  - stateforge:
      component: protocol
      documentation_version: v0.1.0
      latest_version: v0.2.0
      versions:
        - label: v0.2.0
          url: v0.2.0/
        - label: v0.1.0
          url: v0.1.0/
```

Version URLs are relative to the documentation root. The theme resolves them
correctly from root pages and nested procedure or reference pages.

Built-in component accents are provided for `stateforge`, `agent`, `provider`,
`protocol`, `control-plane`, and `sf-aop`. A future repository may use any
lowercase hyphenated component identity. It inherits the StateForge accent or
supplies an explicit six-digit `accent`; the theme chooses a WCAG-compliant
light or dark foreground automatically.

The optional version configuration renders one keyboard-accessible selector.
When `documentation_version` differs from `latest_version`, the theme also
renders a historical-version warning with a link to the latest documentation.
Publishing and redirect behavior remain owned by later documentation
milestones.

## Theme ownership and Material boundary

The package owns only shared presentation: the StateForge mark and favicon,
brand tokens, system typography, light and dark palettes, focus treatment,
component accents, repository-link styling, code presentation, the version
selector, and reusable interactive components. Consumers continue to own
their Markdown, navigation, repository metadata, generated references, and
repository-specific plugins.

The Material integration is deliberately limited to:

- one theme inheritance declaration in `mkdocs_theme.yml`;
- one `main.html` override that calls `super()` and adds shared assets,
  version navigation, and the historical warning; and
- CSS layered over Material's public class surface.

No documentation content depends on a Material template. A future centrally
managed Zensical migration can replace this package's template and CSS layer
without rewriting consumer Markdown.

The theme disables remote web fonts and uses a local system-font stack. All
StateForge branding required at runtime is packaged inside the distribution.

## Distribution verification

Build the wheel and source distribution from the same source revision:

```bash
python -m build
```

The repository test and CI suites inspect both archives, install each artifact
in a clean environment, select `theme.name: stateforge`, and build the fixture
site strictly. Browser checks cover desktop and mobile layouts, light and dark
schemes, focus visibility, component contrast, version navigation, and bundled
logo and favicon resolution.

## Development

```bash
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/ruff format --check .
.venv/bin/ruff check .
.venv/bin/mypy src
.venv/bin/pytest
```
