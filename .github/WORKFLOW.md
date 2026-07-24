# Workflow

How I work in this repo, so the history stays clean and nothing lands broken.

## Branch, PR, merge

I never commit straight to `main`. I branch off the latest `main`, make one focused
change, open a pull request and let it merge itself. The one direct commit to `main`
is the automated profile refresh writing the SVGs, which is automation, not me.

I name every branch for what it does, the same convention I use across all my repos:

- `feat/<short-description>` a new capability
- `fix/<short-description>` a bug fix
- `chore/<short-description>` maintenance, dependencies, config
- `docs/<short-description>` documentation only
- `ci/<short-description>` a workflow or CI change

The full flow I follow every time:

```bash
git checkout main && git pull                 # I always branch from the latest main
git checkout -b chore/short-description        # a branch named for the change
# I make the change and add an entry under [Unreleased] in CHANGELOG.md
git add -A
git commit -m "chore: short description of what changed"   # conventional prefix, present tense
git push -u origin chore/short-description
gh pr create --title "chore: short description" --body "What changed and why."
gh pr merge --squash --delete-branch --auto    # it merges itself once CI passes
```

- Auto-merge waits for the CI check (`Build script (Python)`) to pass, then squash
  merges and deletes the branch, so I never sit and watch it.
- A branch ruleset on `main` marks that CI check as required, so `gh pr merge --auto`
  genuinely waits for it before merging. The build's deploy key bypasses the ruleset.
- Dependency update PRs and stale branch cleanup are handled centrally by repo-ops.
- One change is one branch is one PR. I keep unrelated work apart.

## The automated SVG refresh

- The build workflow commits the regenerated `profile.svg` straight to `main` as me,
  `Isaac Adjei`, so the commit attributes to me across every forge.
- It pushes over SSH with the `BUILD_DEPLOY_KEY` write deploy key, which bypasses the
  branch ruleset that requires CI, so the direct SVG commit is not blocked. The push
  trigger ignores the SVGs so this commit cannot re-trigger the build.
- It only commits when an SVG actually changed, so a quiet run leaves no empty commit.

## Commits

- Conventional prefixes: `feat`, `fix`, `chore`, `ci`, `docs`.

## Pushing

- zaccesss is mirrored by mirror-ops, so a push to `main` is picked up by the GitHub
  App like any other repo and mirrored on to the forges within the minute.

## Before a PR

- `python -m compileall profile.py` and `python -c "import profile"` (CI runs
  the same).
- I never commit a secret. Gitleaks scans every PR.

## Secrets

- Every credential is an Actions secret, never in the code. `ACCESS_TOKEN` is a read
  only fine grained token the generator uses to read my GitHub stats. The commit back
  to `main` is pushed over SSH with the `BUILD_DEPLOY_KEY` write deploy key, which is
  also the branch ruleset's bypass actor. A GitHub Actions secret name cannot
  start with `GITHUB_` (GitHub reserves that prefix), which is why the stats token is
  `ACCESS_TOKEN`.
- `CONTRIB_TOKEN` is the one deliberate exception to fine-grained-only tokens. GitHub's
  `contributionsCollection` (commits, PR reviews, the contribution calendar) withholds
  private-repo detail from every API caller, even the account owner, unless the token
  carries the classic `read:user` scope; no fine-grained permission grants this. I hold
  it as narrowly as the gap allows: a classic PAT scoped to `read:user` alone, no `repo`
  access at all, so it cannot read or write any repository content, only my own
  profile-level contribution counts.

## The system in one breath

- Three times a day (00:17, 08:17 and 16:17 UTC) `build.yml` runs `profile.py`,
  which reads my live GitHub stats and writes `profile.svg`. If the SVG changed it
  commits, and mirror-ops carries this repo to the forges. See the top-level
  [`../README.md`](../README.md) and [`workflows/README.md`](workflows/README.md).
