# CLAUDE.md

## What this repo is

`moneymikeMD/moneymike-plugins`, public, created 2026-09-20. The Claude Code
marketplace these plugins publish through: a plugin becomes installable by
gaining an entry here, and nowhere else. The repo's entire substance is
`.claude-plugin/marketplace.json`, currently four entries: `work-order`
(`github` source, whole repo), `work-order-jira` (`git-subdir` source, path
`plugins/work-order-jira` inside the work-order repo), `night-watchman`
(`github` source, whole repo), `moneymike-skills` (`github` source, whole
repo). Besides it: `README.md`, `.github/CODEOWNERS`,
`.github/workflows/ci.yml` and `scripts/check-marketplace.py`.

## CI

`.github/workflows/ci.yml` runs four jobs on every pull request, on push to
`main`, weekly (Monday 06:17 UTC) and on demand:

- `validate`: every JSON and YAML file parses.
- `marketplace`: `scripts/check-marketplace.py` enforces the publishing contract
  below. Unique names; no `ref` or `sha`; only `github` and `git-subdir`
  sources; each source's `plugin.json` names itself as its entry does; no
  plugin repo carries its own `marketplace.json`; and every dependency range
  resolves against a `<dep>--vX.Y.Z` tag on the dependency's repo. It reads
  public GitHub over HTTPS. The weekly run is what catches a dependency tag
  line breaking upstream with no PR here. `--selftest` covers the range parser.
- `no-major`: the version cap, the same job text as work-order, ai-toolkit and
  night-watchman.
- `no-personal-paths`: the ai-toolkit action.

All four are required status checks on `main`.

## The publishing contract

- One plugin, one entry. A plugin repo carries its own `plugin.json` and MUST
  NOT carry a `marketplace.json` of its own — that would let it self-publish
  outside this file, which is the thing this repo exists to prevent. The
  install id a user types is `<plugin>@moneymike-plugins`.
- Entries carry no `ref` and no `sha`. This is deliberate, not an oversight:
  every install tracks the source repo's default branch. Do not add one to
  "pin" a plugin — that changes the propagation model this file exists to
  provide and belongs in a discussion with the owner first, not a drive-by fix.
- Publishing a new plugin is one entry in `marketplace.json`. Nothing else here
  needs to change for that alone.

## The dependency trap — check this before every new or bumped entry

A plugin's `dependencies` range in its own `plugin.json` is resolved by Claude
Code against `<plugin>--vX.Y.Z` tags on the **dependency's own repository** —
not `vX.Y.Z`, and not a tag on this repo. A range no such tag satisfies is a
hard install failure through this marketplace (confirmed 2026-09-20: installing
through a `CLAUDE_CONFIG_DIR`-isolated HTTPS test, `work-order-jira` and
`night-watchman` both failed to resolve their `work-order` dependency until
`work-order--v1.3.0`..`--v1.5.0` were tagged by hand on the work-order repo).

Before adding or bumping an entry: `git ls-remote --tags` the dependency's repo
and confirm a `<dep>--vX.Y.Z` tag exists inside the declared range. Do not trust
the plain `vX.Y.Z` release tag as a substitute — it is not what gets checked.

work-order's release workflow tags `work-order--v` on every root release
(work-order#44). Verified 2026-10-01: `night-watchman` (`^1.3.0`) and
`work-order-jira` (`^1.2.0`) both resolve to `work-order--v1.9.0`. The
`marketplace` CI job runs this check on every PR and weekly, so a tag line that
stops being cut upstream turns it red here.

## Governance

`main` is protected by ruleset `protect-main`: changes land through a pull
request, deletion and force-pushes are rejected, and the four CI jobs above are
required status checks. No approving review is required (owner decision
2026-10-01, the same as night-watchman, work-order and switchtender);
`CODEOWNERS` (`* @moneymikeMD`) still auto-requests the owner on every PR.
Only accounts with write access can merge, so this does not open the repo to
contributors. Repository admins are bypass actors.

## Version cap

These plugins stay below a major version bump: no commit subject matching
`^[A-Za-z]+(\([^)]*\))?!:`, no `BREAKING CHANGE:` footer. A genuinely breaking
change ships as a plain `feat:` describing the incompatibility in prose.

The `no-major` CI job enforces it on every PR title and commit. There is no
release-please and no version line here, because one JSON file naming unpinned
plugins has nothing to version.
