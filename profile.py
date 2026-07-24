#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Isaac Adjei <https://isaacadjei.me>
#
# This generator script is licensed under the PolyForm Noncommercial License 1.0.0;
# see NOTICE.md. The repository's visual output (the SVGs, the README and the
# assets) is licensed under CC BY-NC-ND 4.0; see LICENSE.
"""
profile.py — my GitHub profile README SVG generator.

I generate profile.svg, a single theme-adaptive card (light by default, dark under a
prefers-color-scheme media query so it renders correctly on every forge, not just GitHub):
  - Left column:  my ASCII art portrait (44 cols x 30 rows, loaded from ascii_profile.txt)
  - Right column: neofetch-style info block + live GitHub stats pulled from the API

To run locally I need my ACCESS_TOKEN set as an environment variable:
    export ACCESS_TOKEN=<fine-grained-PAT>
    python profile.py
"""

import os
import sys
import datetime
import requests
from html import escape as esc

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

USERNAME   = 'zaccesss'  # GitHub username to query

ASCII_ART_PATH = os.path.join(os.path.dirname(__file__), 'assets', 'ascii_profile.txt')  # path to ASCII portrait file
GRAPHQL_URL    = 'https://api.github.com/graphql'  # GitHub GraphQL endpoint

# Portrait dimensions (rows must match ascii_profile.txt line count)
ASCII_ROWS = 30  # must match the line count of ascii_profile.txt

SVG_WIDTH  = 1080  # total canvas width in pixels
ROW_STEP   = 20   # vertical gap between rows in pixels
ROW_START  = 30   # y-coordinate of the first row

# Right column char width: dots are calculated so every value ends here.
LINE_WIDTH = 66   # character budget for the right column; dots fill to this width exactly

ASCII_X = 35   # left edge of the ASCII portrait column
STATS_X = 410  # left edge of the stats column
ASCII_Y_OFFSET = ROW_STEP  # visually centres the portrait after the taller Git Stats block

# Stats rows: content goes to row 33 (y=690); SVG height adds bottom margin.
STATS_ROWS = 34                                                        # total number of rows in the stats block
SVG_HEIGHT = ROW_START + (STATS_ROWS - 1) * ROW_STEP + ROW_STEP + 20  # 730px total canvas height

# ---------------------------------------------------------------------------
# Colour schemes
# ---------------------------------------------------------------------------

DARK = {
    'bg':     '#161b22',
    'text':   '#c9d1d9',
    'key':    '#ffa657',
    'value':  '#a5d6ff',
    'add':    '#3fb950',
    'delete': '#f85149',
    'dots':   '#616e7f',
}

LIGHT = {
    'bg':     '#f6f8fa',
    'text':   '#24292f',
    'key':    '#953800',
    'value':  '#0a3069',
    'add':    '#1a7f37',
    'delete': '#cf222e',
    'dots':   '#c2cfde',
}

# ---------------------------------------------------------------------------
# ASCII art loader
# ---------------------------------------------------------------------------

def load_ascii_art(path: str) -> list[str]:
    """Return ASCII_ROWS strings of 44 chars each from ascii_profile.txt."""
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.read().splitlines()
    result = []
    for i in range(ASCII_ROWS):
        line = lines[i] if i < len(lines) else ''
        result.append(line.ljust(44)[:44])  # pad short lines to exactly 44 chars and clip any that are longer
    return result

# ---------------------------------------------------------------------------
# GitHub API helpers
# ---------------------------------------------------------------------------

def graphql(token: str, query: str, variables: dict | None = None) -> dict:
    headers = {'Authorization': f'bearer {token}', 'Content-Type': 'application/json'}  # bearer auth for GitHub API
    resp = requests.post(GRAPHQL_URL,
                         json={'query': query, 'variables': variables or {}},
                         headers=headers, timeout=30)  # 30-second timeout so a slow API cannot hang the workflow
    resp.raise_for_status()
    result = resp.json()
    if 'errors' in result:
        raise RuntimeError(f'GraphQL errors: {result["errors"]}')
    return result.get('data', {})


def get_user_info(token: str, username: str) -> tuple[int, int, int, int, int, int]:
    """Return (followers, prs, contributed_repos, issues, gists, creation_year)."""
    data = graphql(token, """
        query ($login: String!) {
            user(login: $login) {
                followers { totalCount }
                pullRequests { totalCount }
                issues { totalCount }
                gists(first: 1, privacy: PUBLIC) { totalCount }
                repositoriesContributedTo(
                    first: 1
                    contributionTypes: [COMMIT, PULL_REQUEST, PULL_REQUEST_REVIEW, ISSUE, REPOSITORY]
                    includeUserRepositories: true
                ) { totalCount }
                createdAt
            }
        }""", {'login': username})
    u = data.get('user', {})
    return (
        u.get('followers',                  {}).get('totalCount', 0),
        u.get('pullRequests',               {}).get('totalCount', 0),
        u.get('repositoriesContributedTo',  {}).get('totalCount', 0),
        u.get('issues',                     {}).get('totalCount', 0),
        u.get('gists',                      {}).get('totalCount', 0),
        int(u.get('createdAt', '2022-01-01T00:00:00Z')[:4]),  # slice the year from the ISO timestamp
    )


def get_repos_stars_and_forks(token: str, username: str) -> tuple[int, int, int]:
    """Return (total_owned_repos, total_stars, total_forks)."""
    query = """
        query ($login: String!, $cursor: String) {
            user(login: $login) {
                repositories(first: 100, after: $cursor, ownerAffiliations: OWNER,
                             orderBy: {field: UPDATED_AT, direction: DESC}) {
                    nodes { stargazerCount forkCount }
                    pageInfo { hasNextPage endCursor }
                    totalCount
                }
            }
        }"""
    stars, forks, total, cursor, first = 0, 0, 0, None, True
    while True:
        r = graphql(token, query, {'login': username, 'cursor': cursor})
        r = r.get('user', {}).get('repositories', {})
        if first:
            total, first = r.get('totalCount', 0), False  # capture total count from the first page only
        stars += sum(n.get('stargazerCount', 0) for n in r.get('nodes', []))
        forks += sum(n.get('forkCount', 0) for n in r.get('nodes', []))
        page = r.get('pageInfo', {})
        if not page.get('hasNextPage'):
            break
        cursor = page.get('endCursor')
    return total, stars, forks


def get_contributions_for_year(token: str, username: str, year: int) -> tuple[int, int, int]:
    """Return (commits, reviews, total_contributions) for one calendar year."""
    data = graphql(token, """
        query ($login: String!, $from: DateTime!, $to: DateTime!) {
            user(login: $login) {
                contributionsCollection(from: $from, to: $to) {
                    totalCommitContributions
                    totalPullRequestReviewContributions
                    contributionCalendar {
                        totalContributions
                    }
                }
            }
        }""", {'login': username,
               'from': f'{year}-01-01T00:00:00Z',
               'to':   f'{year}-12-31T23:59:59Z'})
    collection = (data.get('user', {})
                      .get('contributionsCollection', {}))
    return (
        collection.get('totalCommitContributions', 0),
        collection.get('totalPullRequestReviewContributions', 0),
        collection.get('contributionCalendar', {}).get('totalContributions', 0),
    )


def get_streak(token: str, username: str) -> tuple[int, int]:
    """Return (current_streak_days, longest_streak_days) from the past year's contribution calendar."""
    data = graphql(token, """
        query ($login: String!) {
            user(login: $login) {
                contributionsCollection {
                    contributionCalendar {
                        weeks {
                            contributionDays {
                                contributionCount
                                date
                            }
                        }
                    }
                }
            }
        }""", {'login': username})
    weeks = (data.get('user', {})
                 .get('contributionsCollection', {})
                 .get('contributionCalendar', {})
                 .get('weeks', []))
    days = sorted(
        [(d['date'], d['contributionCount'])
         for w in weeks for d in w.get('contributionDays', [])],
        key=lambda x: x[0]
    )
    longest = current_run = 0
    for _, count in days:
        if count > 0:
            current_run += 1
            longest = max(longest, current_run)
        else:
            current_run = 0
    # I don't penalise the streak if today has no contributions yet
    today = datetime.date.today().isoformat()
    days_to_check = [(d, c) for d, c in days if d <= today]
    if days_to_check and days_to_check[-1][0] == today and days_to_check[-1][1] == 0:
        days_to_check = days_to_check[:-1]
    current = 0
    for _, count in reversed(days_to_check):
        if count > 0:
            current += 1
        else:
            break
    return current, longest


def get_all_contributions(token: str, username: str, creation_year: int) -> tuple[int, int, int]:
    """Sum commits, reviews and total contributions across every year since account creation."""
    commits = reviews = total_contribs = 0
    for year in range(creation_year, datetime.datetime.utcnow().year + 1):  # walk every year from account creation to today
        try:
            year_commits, year_reviews, year_total = get_contributions_for_year(token, username, year)
            commits += year_commits
            reviews += year_reviews
            total_contribs += year_total
        except Exception as e:
            print(f'  Warning (contributions {year}): {e}', file=sys.stderr)
    return commits, reviews, total_contribs


def get_loc(token: str, username: str) -> tuple[int, int, int]:
    """
    Total LOC across all owned non-forked repos.
    Counts commits by this user (including unlinked terminal commits).
    Returns (added, deleted, net).
    """
    repos = []
    cursor = None
    while True:
        data = graphql(token, """
            query ($login: String!, $cursor: String) {
                user(login: $login) {
                    repositories(first: 100, after: $cursor,
                                 ownerAffiliations: [OWNER, ORGANIZATION_MEMBER], isFork: false) {
                        nodes { nameWithOwner isEmpty defaultBranchRef { name } }
                        pageInfo { hasNextPage endCursor }
                    }
                }
            }""", {'login': username, 'cursor': cursor})
        rd = data.get('user', {}).get('repositories', {})
        for n in rd.get('nodes', []):
            if not n.get('isEmpty') and n.get('defaultBranchRef'):
                repos.append(n['nameWithOwner'])
        page = rd.get('pageInfo', {})
        if not page.get('hasNextPage'):
            break
        cursor = page.get('endCursor')

    commit_q = """
        query ($owner: String!, $name: String!, $cursor: String) {
            repository(owner: $owner, name: $name) {
                defaultBranchRef {
                    target {
                        ... on Commit {
                            history(first: 100, after: $cursor) {
                                nodes {
                                    additions deletions messageHeadline
                                    author { user { login } }
                                }
                                pageInfo { hasNextPage endCursor }
                            }
                        }
                    }
                }
            }
        }"""
    add, delete = 0, 0
    for repo in repos:
        owner, name = repo.split('/', 1)
        # Only in my own repos do I credit unlinked terminal commits (they're mine).
        # In org/shared repos an unlinked commit could be someone else's, so there
        # I require the commit to be authored by me.
        is_own_repo = owner.lower() == username.lower()
        cursor = None
        try:
            while True:
                data = graphql(token, commit_q,
                               {'owner': owner, 'name': name, 'cursor': cursor})
                history = (data.get('repository', {})
                               .get('defaultBranchRef', {})
                               .get('target', {})
                               .get('history', {}))
                for c in history.get('nodes', []):
                    # I skip my automated metadata backup commits (from the meta-mirror repo) so their
                    # JSON dumps do not inflate my lines of code with data I did not actually write.
                    if c.get('messageHeadline', '') == 'chore: update metadata backup':
                        continue
                    login = ((c.get('author') or {}).get('user') or {}).get('login', '')
                    if login.lower() == username.lower() or (is_own_repo and not login):
                        add    += c.get('additions', 0)
                        delete += c.get('deletions', 0)
                page = history.get('pageInfo', {})
                if not page.get('hasNextPage'):
                    break
                cursor = page.get('endCursor')
        except Exception as e:
            print(f'  Warning (LOC {repo}): {e}', file=sys.stderr)
    return add, delete, add - delete

# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def fmt(n: int) -> str:
    return f'{n:,}'  # comma-separated thousands (e.g. 1,234)


def pad_dots(label: str, value: str, width: int = LINE_WIDTH) -> str:
    """
    Return dots so that '. LABEL: DOTS VALUE' = width chars exactly.
    The full value string (including any trailing text like '( add++, del-- )')
    must be passed so dots are calculated correctly.
    """
    n = width - 2 - len(label) - 2 - 1 - len(str(value))  # 2 = '. ', 2 = ': ', 1 = space before value
    return '.' * max(1, n)

# ---------------------------------------------------------------------------
# SVG fragment builders
# ---------------------------------------------------------------------------

def cc(t: str)  -> str: return f'<tspan class="cc">{esc(t)}</tspan>'    # punctuation and dots colour class
def key(t: str) -> str: return f'<tspan class="key">{esc(t)}</tspan>'   # label colour class
def val(t: str) -> str: return f'<tspan class="value">{esc(t)}</tspan>' # value colour class

def trow(y: int, content: str) -> str:
    return f'    <tspan x="{STATS_X}" y="{y}">{content}</tspan>'  # pin each row to the stats column x-offset

def info_row(y: int, label: str, value: str) -> str:
    """Standard right-aligned info row."""
    return trow(y, cc('. ') + key(label) + cc(f': {pad_dots(label, str(value))} ') + val(str(value)))

def section_header(y: int, title: str) -> str:
    # I want my section headers to match the weight of the first "isaac@adjei" line,
    # so the whole thing - title and hyphens - uses the main text colour, no grey.
    hyphens = '-' * max(2, LINE_WIDTH - 2 - len(title) - 1)
    return trow(y, f'- {title} {hyphens}')

def blank(y: int) -> str:
    return trow(y, '')

PIPE_LEFT = 36  # chars from line-start to the space before ' | '; pins | column

def dual_row(y: int, lbl1: str, v1: str, lbl2: str, v2: str) -> str:
    """Two key-value pairs with the | separator pinned to column PIPE_LEFT."""
    d1 = max(1, PIPE_LEFT - 5 - len(lbl1) - len(v1))
    d2 = max(1, LINE_WIDTH - PIPE_LEFT - 6 - len(lbl2) - len(v2))
    return trow(y,
        cc('. ') + key(lbl1) + cc(f': {"."*d1} ') + val(v1) +
        cc(' | ') + key(lbl2) + cc(f': {"."*d2} ') + val(v2))

def contribs_repos_row(y: int, lbl1: str, v1: str, repos: int, contributed: int) -> str:
    """Any headline stat paired with Repos (Contributed in key-coloured curly braces) on the right,
    the same headline-left, detail-right shape as the Lines of Code row."""
    v2_plain = f'{fmt(repos)} {{Contrib: {fmt(contributed)}}}'
    d1 = max(1, PIPE_LEFT - 5 - len(lbl1) - len(v1))
    d2 = max(1, LINE_WIDTH - PIPE_LEFT - 6 - len('Repos') - len(v2_plain))
    v2_svg = (f'<tspan class="value">{esc(fmt(repos))} {{'
              f'<tspan class="key">Contrib</tspan>: {esc(fmt(contributed))}}}</tspan>')
    return trow(y,
        cc('. ') + key(lbl1) + cc(f': {"."*d1} ') + val(v1) +
        cc(' | ') + key('Repos') + cc(f': {"."*d2} ') + v2_svg)

def loc_dual_row(y: int, total: int, add: int, delete: int) -> str:
    """Lines of Code on left, add/del breakdown on right with } aligned to right edge."""
    net_str = fmt(total)
    add_str = fmt(add)
    del_str = fmt(delete)
    d1 = max(1, PIPE_LEFT - 5 - len('Lines of Code') - len(net_str))
    right_chars = LINE_WIDTH - PIPE_LEFT - 3
    inner = f'{add_str}++, {del_str}--'
    total_pad = right_chars - 2 - len(inner)
    lp = ' ' * (total_pad // 2)
    rp = ' ' * (total_pad - total_pad // 2)
    rhs = (f'{{{lp}<tspan class="addColor">{esc(add_str)}</tspan>++, '
           f'<tspan class="delColor">{esc(del_str)}</tspan>--{rp}}}')
    return trow(y,
        cc('. ') + key('Lines of Code') + cc(f': {"."*d1} ') + val(net_str) +
        cc(' | ') + rhs)

# ---------------------------------------------------------------------------
# SVG builder
# ---------------------------------------------------------------------------

def build_svg(
    ascii_rows: list[str],
    repos: int, contributed: int, stars: int, forks: int,
    commits: int, followers: int,
    prs: int, issues: int, reviews: int, gists: int,
    total_contribs: int,
    loc_total: int, loc_add: int, loc_del: int,
    current_streak: int, longest_streak: int,
) -> str:

    # One adaptive stylesheet: the light palette is the default (light and no-preference viewers)
    # and a prefers-color-scheme:dark media query swaps in the dark palette. Because the browser
    # renders the SVG, this theme switch works on every forge (GitHub, GitLab, Codeberg, gitea.com),
    # unlike a <picture> element, which the other forges strip. Every colour lives on a class, so the
    # background rect and the text follow the theme too.
    style = f"""
      @font-face {{
        src: local('Consolas'), local('Consolas Bold');
        font-family: 'ConsolasFallback';
        font-display: swap;
        size-adjust: 109%;
      }}
      .bg       {{ fill: {LIGHT['bg']};     }}
      .fg       {{ fill: {LIGHT['text']};   }}
      .key      {{ fill: {LIGHT['key']};    }}
      .value    {{ fill: {LIGHT['value']};  }}
      .addColor {{ fill: {LIGHT['add']};    }}
      .delColor {{ fill: {LIGHT['delete']}; }}
      .cc       {{ fill: {LIGHT['dots']};   }}
      text, tspan {{ white-space: pre; }}
      @media (prefers-color-scheme: dark) {{
        .bg       {{ fill: {DARK['bg']};     }}
        .fg       {{ fill: {DARK['text']};   }}
        .key      {{ fill: {DARK['key']};    }}
        .value    {{ fill: {DARK['value']};  }}
        .addColor {{ fill: {DARK['add']};    }}
        .delColor {{ fill: {DARK['delete']}; }}
        .cc       {{ fill: {DARK['dots']};   }}
      }}
    """

    # ASCII art at 14px: keeps 44-char lines clear of the stats column at x={STATS_X}
    ascii_tspans = [
        f'    <tspan x="{ASCII_X}" y="{ROW_START + ROW_STEP + 10 + ASCII_Y_OFFSET + i * ROW_STEP}">{esc(line)}</tspan>'
        for i, line in enumerate(ascii_rows)
    ]

    Y = [ROW_START + i * ROW_STEP for i in range(STATS_ROWS)]

    header_dashes = '-' * (LINE_WIDTH - len('isaac@adjei ') - 1)

    stats_tspans = [
        trow(Y[0],  f'isaac@adjei {header_dashes}'),

        info_row(Y[1],  'Host',     'Aston University'),
        info_row(Y[2],  'Location', 'London & Birmingham, UK'),
        info_row(Y[3],  'Mode',     'Electronic Engineering and Computer Science'),
        info_row(Y[4],  'Kernel',   'Sleep deprived but functional'),
        info_row(Y[5],  'OS',       'Windows, macOS, Ubuntu, Linux'),
        info_row(Y[6],  'IDE',      'JetBrains, VS Code, Visual/Microchip Studio'),

        blank(Y[7]),

        info_row(Y[8],  'Languages.Tools',       'Git, Shell, Bash, Docker, Make, CI/CD'),
        info_row(Y[9],  'Languages.Software',    'C, C++, Python, TypeScript, Rust'),
        info_row(Y[10], 'Languages.Hardware',    'Embedded C, MATLAB, MicroPy, FPGA/VHDL'),
        info_row(Y[11], 'Languages.Web',          'HTML, CSS, PHP/Laravel, React, Next.js'),
        info_row(Y[12], 'Languages.Spoken',        'English, French, Twi, Ga'),

        blank(Y[13]),

        info_row(Y[14], 'Hobbies.Tech',      'CyberSec, Cloud, DevOps, Hackathons'),
        info_row(Y[15], 'Hobbies.Software',  'Full Stack, Open Source, DB, AI/ML/DS'),
        info_row(Y[16], 'Hobbies.Hardware',  'Embedded Systems, MCUs, PCB, Robotics'),
        info_row(Y[17], 'Hobbies.General',  'Fitness, Travel, Piano, Reading, Gaming'),
        info_row(Y[18], 'Hobbies.Status',   'rm -rf impostor_syndrome && touch grass'),

        blank(Y[19]),

        section_header(Y[20], 'Contact'),
        info_row(Y[21], 'Discord',        'zac.nii'),
        info_row(Y[22], 'Portfolio',      'isaacadjei.me'),
        info_row(Y[23], 'Email.Main',     'hello@isaacadjei.me'),
        info_row(Y[24], 'Email.Work',     'contact@isaacadjei.me'),
        info_row(Y[25], 'LinkedIn',       'linkedin.com/in/isaacadjei'),

        blank(Y[26]),

        section_header(Y[27], 'Git Stats'),
        dual_row(Y[28], 'Followers',      fmt(followers),        'Stars',          fmt(stars)),
        contribs_repos_row(Y[29], 'Contribs', fmt(total_contribs), repos, contributed),
        # Forks and Gists are both 0 right now, I'll bring this row back once I have some.
        # dual_row(Y[30], 'Forks',        fmt(forks),            'Gists',          fmt(gists)),
        dual_row(Y[30], 'Commits',        fmt(commits),          'PRs',            fmt(prs)),
        dual_row(Y[31], 'Issues',         fmt(issues),           'Reviews',        fmt(reviews)),
        dual_row(Y[32], 'Streak.Best',    f'{longest_streak} days', 'Streak.Current', f'{current_streak} days'),
        loc_dual_row(Y[33], loc_total, loc_add, loc_del),
    ]

    ascii_block = '\n'.join(ascii_tspans)
    stats_block = '\n'.join(stats_tspans)

    return f"""<?xml version='1.0' encoding='UTF-8'?>
<svg xmlns="http://www.w3.org/2000/svg"
     font-family="ConsolasFallback,Consolas,monospace"
     width="{SVG_WIDTH}px" height="{SVG_HEIGHT}px"
     font-size="16px">
  <defs><style>{style}  </style></defs>
  <rect width="{SVG_WIDTH}px" height="{SVG_HEIGHT}px" class="bg" rx="15"/>
  <!-- ASCII portrait: 14px so 44-char lines stay inside x={STATS_X} -->
  <text x="{ASCII_X}" y="{ROW_START}" class="fg" font-size="14px"
        xml:space="preserve" style="white-space:pre;">
{ascii_block}
  </text>
  <!-- Stats block -->
  <text x="{STATS_X}" y="{ROW_START}" class="fg" style="white-space:pre;">
{stats_block}
  </text>
</svg>"""

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    token = os.environ.get('ACCESS_TOKEN', '').strip()
    if not token:
        print('ERROR: ACCESS_TOKEN environment variable is not set.', file=sys.stderr)
        sys.exit(1)
    # GitHub's contributionsCollection withholds private-repo detail (commits, reviews, the
    # calendar) from every API caller, even the account owner, unless the token carries the
    # classic read:user scope - no fine-grained permission grants this. CONTRIB_TOKEN is a
    # separate classic PAT scoped to read:user only, with no repo access at all, so I don't have
    # to widen ACCESS_TOKEN's own repo-content permissions just to see my private contributions.
    # Falls back to ACCESS_TOKEN so this still runs (with public-only contribution counts) before
    # the secret exists, or for local testing with a token that already carries read:user.
    contrib_token = os.environ.get('CONTRIB_TOKEN', '').strip() or token
    username = os.environ.get('USER_NAME', USERNAME)  # USER_NAME env var overrides the hardcoded default

    print('Loading ASCII art...')
    ascii_rows = load_ascii_art(ASCII_ART_PATH)

    print('Fetching GitHub stats...')
    try:
        followers, prs, contributed, issues, gists, creation_year = get_user_info(token, username)
    except Exception as e:
        print(f'  Warning: {e}', file=sys.stderr)
        followers, prs, contributed, issues, gists, creation_year = 0, 0, 0, 0, 0, 2022  # safe defaults if the API call fails

    try:
        repos, stars, forks = get_repos_stars_and_forks(token, username)
    except Exception as e:
        print(f'  Warning: {e}', file=sys.stderr)
        repos, stars, forks = 0, 0, 0

    print('  Counting commit and review contributions...')
    try:
        commits, reviews, total_contribs = get_all_contributions(contrib_token, username, creation_year)
    except Exception as e:
        print(f'  Warning: {e}', file=sys.stderr)
        commits, reviews, total_contribs = 0, 0, 0

    print('  Calculating lines of code...')
    try:
        loc_add, loc_del, loc_total = get_loc(token, username)
    except Exception as e:
        print(f'  Warning: {e}', file=sys.stderr)
        loc_add, loc_del, loc_total = 0, 0, 0

    print('  Fetching streak stats...')
    try:
        current_streak, longest_streak = get_streak(contrib_token, username)
    except Exception as e:
        print(f'  Warning: {e}', file=sys.stderr)
        current_streak, longest_streak = 0, 0

    print(f'  Followers: {followers} | Stars: {stars}')
    print(f'  Repos: {repos} | Contributed: {contributed} | Contribs: {total_contribs}')
    print(f'  Forks: {forks} | Gists: {gists}')
    print(f'  Commits: {commits} | PRs: {prs}')
    print(f'  Issues: {issues} | Reviews: {reviews}')
    print(f'  LOC: {fmt(loc_total)} ({fmt(loc_add)}++, {fmt(loc_del)}--)')
    print(f'  Streak: {current_streak} days current, {longest_streak} days best')

    print('Generating profile.svg...')  # one theme-adaptive card that renders on every forge
    svg = build_svg(ascii_rows,
                    repos, contributed, stars, forks,
                    commits, followers, prs, issues, reviews, gists,
                    total_contribs,
                    loc_total, loc_add, loc_del,
                    current_streak, longest_streak)
    with open('profile.svg', 'w', encoding='utf-8') as f:
        f.write(svg)
    print('Done.')


if __name__ == '__main__':
    main()
