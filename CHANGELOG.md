# Changelog

All notable changes to this project are recorded here. The format follows Keep a
Changelog and this project uses date based entries rather than semantic versions,
because it is a living profile rather than a released library.

## Unreleased

### Changed

- CI and gitleaks now run on pull requests only. They no longer re-run on `main` after a
  merge, since the same commit was already checked on the PR.
- Moved the build schedule off the top of the hour to `17 0,6,12,18 * * *` (00:17,
  06:17, 12:17 and 18:17 UTC). The explicit times spell out the four daily runs and the
  off-peak minute dodges GitHub's congested on-the-hour scheduling.
- Relicensed the repository. The visual and written content (the SVGs, the README,
  the ASCII portrait and everything under `assets/`) is now Creative Commons
  Attribution-NonCommercial-NoDerivatives 4.0, and the generator source
  (`isaacadjei.py`) is PolyForm Noncommercial 1.0.0, so the profile can be shared
  with credit but not reused commercially or remixed. This replaces the previous
  MIT licence.

### Added

- Repository scaffolding to match my other repos: a CI workflow that compile and
  import checks the generator, a gitleaks secret scan, Dependabot auto-merge, a
  `.gitattributes` that marks the generated SVGs, and `CODE_OF_CONDUCT.md`,
  `SECURITY.md` and this changelog. Dependency update PRs and stale branch cleanup
  are handled centrally by repo-ops, so this repo carries no `dependabot.yml` or
  branch maintenance workflow.

## 2026-07-06

### Fixed

- Stopped meta-mirror's weekly JSON backup commits inflating my profile Lines of
  Code. The generator now reads each commit's headline and skips commits titled
  `chore: update metadata backup`, so roughly 400k lines of backup data no longer
  count. Because it recomputes from full history every run the number self
  corrected on the next build, from about 801,927 to about 399,182 (#10, #12).
- Forced GitHub to refetch the stats image after the LOC fix. GitHub caches the SVG
  by URL, so with an unchanged filename it kept serving the stale numbers. Bumped
  the cache version query on all three README references from `?v=4` to `?v=5`
  (#11, #13).

## 2026-07-05

### Changed

- Dropped the in-workflow forge mirroring. mirror-ops now carries this repo to
  GitLab, Codeberg, Bitbucket and Gitea server side, so the build only pushes to
  GitHub (#8).
- Counted organisation member repos in the Lines of Code total, crediting only my
  own commits in shared repos (#7).
- Bumped the checkout, setup-python and cache actions to their Node 24 majors.

### Fixed

- Made the SVG push conflict proof. Builds are serialised and the push rebases and
  retries onto the latest `main`, so concurrent runs no longer clash (#9).

## 2026-07-04

### Changed

- Switched the build commit to my GitHub noreply email so the automated refresh
  attributes to me cleanly.

## 2026-06-20

### Changed

- Added Newsletter and Now links to the README nav and moved Contact to the end.

## 2026-06-15

### Added

- `.github/FUNDING.yml` with GitHub Sponsors, Buy Me a Coffee and Patreon links
  (#6, closes #5).

## 2026-06-13

### Changed

- Switched the build commit identity from my personal address to my main email and
  refreshed the SVGs.

## 2026-06-07

### Changed

- Reordered the languages section, bumped the SVG cache version and cleaned up the
  `.gitignore`.

## 2026-06-05

### Changed

- Overhauled the profile SVG layout and content, refined the hobbies section and
  status line and finalised the layout tweaks.
- Added my website URL to the LICENSE copyright line.

### Fixed

- Fixed forge mirroring: mirror to Gitea over SSH, creating the `.ssh` directory
  before the keyscan, and force-push while temporarily unprotecting GitLab `main`
  so the mirror push is accepted (#4).

## 2026-06-04

### Added

- Streak stats, new languages and hobbies and portrait tweaks, plus pushing SVG
  updates to Gitea.com on every build.

### Fixed

- Restored the `ascii_final.txt` portrait asset.
- Pushed SVGs to GitHub before mirroring to the other forges.
- Widened the SVG canvas to 1080px to stop the Languages.Hardware row overflowing,
  and set `LINE_WIDTH` to 66 so every row right-aligns to one vertical edge.
- Used a full clone so Gitea accepts the first push to a new repo.

## 2026-05-20

### Changed

- Workflow maintenance.

## 2026-05-15

### Added

- A looping typing animation for the README, `approach_dark.svg` and
  `approach_light.svg`, that types each line, holds and resets (#2).

### Changed

- Renamed `today.py` to `isaacadjei.py` and updated the workflow to match (#1).
- Section headers now use the main text colour, the schedule moved from daily to
  every six hours so stats stay fresh, trimmed the approach SVG top padding and set
  the workflow to commit under my own name and email (#3).
- Added a newsletter link to the nav.

## 2026-05-14

### Changed

- Restructured the profile card with Mode, Kernel and Status rows, moved the nav
  links above the card for visibility and added website and links to the nav.

### Fixed

- Busted the GitHub README cache to force the SVG to re-render.

## 2026-05-13

### Added

- The first version of my GitHub profile README: an animated SVG portrait with live
  GitHub stats, generated by `isaacadjei.py` into `dark_mode.svg` and
  `light_mode.svg` and committed back by GitHub Actions.

---

The generator also commits an automated `chore: update profile SVG` refresh on its
schedule. Those routine regenerations are omitted here.
