# AGENTS.md

## Project

AuroraWX is a weewx skin plus Python extension. Extension code lives in
`bin/user/aurorawx/` (scanner, searchlist, generator); Cheetah templates,
CSS, and JS live in `skins/aurorawx/`. It is not a standalone app: it is
developed against a dev weewx instance under `dev-weewx/` (weewx-data).

## Commands

- Unit tests: `.venv/bin/pytest -q` (tests in `tests/`). No lint or
  typecheck tools are installed.
- E2E report build + assertions: `sh tools/run_reports.sh`. Refreshes
  fixtures, syncs the skin into `dev-weewx/`, runs 4 scenarios
  (full/partial/empty/nocam), grep-asserts the generated pages after each
  run, and ends with `ALL-OK`.
- Fixture refresh only: `tools/make_fixtures.sh`. Skin sync only:
  `tools/sync_dev.sh`.
- Scenario configs for the dev instance:
  `dev-weewx/weewx-data/weewx-{full,partial,empty,nocam}.conf`.
- Extension tarball: `tools/gen_install.py` regenerates the file manifest
  in `install.py`, then pack `install.py bin skins` with the `aurorawx/`
  prefix into `dist/aurorawx-<version>.tar.gz` (see README.md; `dist/` is
  git-ignored). `tools/gen_install.py --check` exits nonzero when the
  manifest is stale.

Each report scenario overwrites `dev-weewx/weewx-data/public_html`, so
assertions must run immediately after that scenario's report run.

## Conventions

- Template behavior changes are verified through `run_reports.sh`
  assertions; Python changes through pytest. Write the failing test first.
- Period-selector dropdowns are plain `<select data-periods=...>` elements
  populated client-side from `periods.js` by `js.inc`. Day and week
  archive pages use flatpickr inputs (`period-picker.js`) instead and must
  not contain `<select>`.
- Archive templates under `year/`, `month/`, `week/`, `day/` sit one level
  below the site root: they need `<base href="../">` and load
  `periods.js?v=$aurora.asset_version` themselves.
- CSS must cover light theme, `.dark-theme`, and the
  `prefers-color-scheme` auto mode.
- Week page titles are en-dash date ranges; gallery day cells render moon
  and Kp chips inside `.tl-chip-row`.
