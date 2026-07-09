# Workflows

One workflow builds the profile itself; the rest keep the repo healthy. The
generator lives in [`../../isaacadjei.py`](../../isaacadjei.py) and the build
workflow is a thin wrapper that hands it the credentials.

## The build

| Workflow | Trigger | Purpose |
| --- | --- | --- |
| [build](build.yml) | four times a day (00:17, 06:17, 12:17, 18:17 UTC), push to main (excluding the generated SVGs), manual `workflow_dispatch` | Runs `isaacadjei.py` to regenerate `dark_mode.svg` and `light_mode.svg` from live GitHub stats, then commits only if something changed. Pushes over SSH with a write deploy key that bypasses the branch ruleset |

## Repo automation

| Workflow | Trigger | Purpose |
| --- | --- | --- |
| [ci](ci.yml) | push, PR | Compile-checks and imports the generator so a broken change cannot land |
| [gitleaks-scan](gitleaks-scan.yml) | push, PR | Scans for hard-coded secrets with a pinned gitleaks binary |

Dependency update PRs and stale branch cleanup are handled centrally by repo-ops, so
this repo carries no `dependabot.yml` or branch maintenance workflow.

## Conventions

- One workflow per job, named for what it does; the build workflow is a thin wrapper
  and the logic lives in the script.
- All runtime settings come from GitHub Actions secrets injected as environment
  variables; nothing configurable is committed.
- Third-party actions are pinned to a full commit SHA so a mutable tag cannot be
  silently updated.
