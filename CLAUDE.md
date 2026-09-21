# CLAUDE.md

## What this repo is

`moneymikeMD/moneymike-plugins`, public, created 2026-09-20. The Claude Code
marketplace these plugins publish through: a plugin becomes installable by
gaining an entry here, and nowhere else. The repo's entire substance is
`.claude-plugin/marketplace.json`, currently three entries: `work-order`
(`github` source, whole repo), `work-order-jira` (`git-subdir` source, path
`plugins/work-order-jira` inside the work-order repo), `night-watchman`
(`github` source, whole repo). `README.md` and `.github/CODEOWNERS` are the only
other tracked files.

**There is no CI here at all.** No `.github/workflows/`, no JSON validation on
push, no lint. A syntax error in `marketplace.json` is caught only by the next
`/plugin marketplace add` or install attempt, not by a check on the PR. Do not
assume a green anything — there is nothing to go green.

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

**Current state, verified 2026-09-21**: work-order's release workflow now tags
`work-order--v` automatically on every root release (added in work-order#44,
merged 2026-09-20). This is no longer untested — the very next release,
`v1.6.0` (2026-09-21), produced `work-order--v1.6.0` in the same run, at the
same commit. `night-watchman`'s declared range (`^1.3.0`) and
`work-order-jira`'s own declared range (`^1.2.0`) both currently resolve, since
`work-order--v1.3.0` through `--v1.6.0` all exist. If work-order's tagging
workflow is ever reverted or fails silently on a future release, this
marketplace's `night-watchman` and `work-order-jira` entries break with no
signal here — there is no CI in this repo to catch it.

## Governance

`main` is protected by ruleset `protect-main`: every PR needs one approving
review plus a code-owner review (`CODEOWNERS` is `* @moneymikeMD`). Repository
admins are bypass actors, so a maintainer can merge without waiting — treat the
review requirement as real, because for a contributor it is.

## Version cap

These plugins stay below a major version bump: no commit subject matching
`^[A-Za-z]+(\([^)]*\))?!:`, no `BREAKING CHANGE:` footer. A genuinely breaking
change ships as a plain `feat:` describing the incompatibility in prose.

Nothing enforces it here. This repo has no `no-major` job, no CI of any kind,
and no release-please — it carries no version line at all, because one JSON
file naming unpinned plugins has nothing to version. Hold the line by hand.
