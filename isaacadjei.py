#!/usr/bin/env python3
"""
isaacadjei.py — my GitHub profile README SVG generator.

I generate dark_mode.svg and light_mode.svg, each with:
  - Left column:  my ASCII art portrait (44 cols x 28 rows, loaded from ascii_final.txt)
  - Right column: neofetch-style info block + live GitHub stats pulled from the API

To run locally I need my ACCESS_TOKEN set as an environment variable:
    export ACCESS_TOKEN=<fine-grained-PAT>
    python isaacadjei.py
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

ASCII_ART_PATH = os.path.join(os.path.dirname(__file__), 'assets', 'ascii_final.txt')  # path to ASCII portrait file
GRAPHQL_URL    = 'https://api.github.com/graphql'  # GitHub GraphQL endpoint

# Portrait dimensions (rows must match ascii_final.txt line count)
ASCII_ROWS = 28  # must match the line count of ascii_final.txt

SVG_WIDTH  = 985  # total canvas width in pixels
ROW_STEP   = 20   # vertical gap between rows in pixels
ROW_START  = 30   # y-coordinate of the first row

# Right column char width: dots are calculated so every value ends here.
LINE_WIDTH = 60   # character budget for the right column; dots fill to this width exactly

ASCII_X = 15   # left edge of the ASCII portrait column
STATS_X = 390  # left edge of the stats column

# Stats rows: content goes to row 30 (y=630); SVG height adds bottom margin.
STATS_ROWS = 31                                                        # total number of rows in the stats block
SVG_HEIGHT = ROW_START + (STATS_ROWS - 1) * ROW_STEP + ROW_STEP + 20  # 650px total canvas height

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
    """Return ASCII_ROWS strings of 44 chars each from ascii_final.txt."""
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


def get_user_info(token: str, username: str) -> tuple[int, int, int, int, int]:
    """Return (followers, prs, contributed_repos, issues, creation_year)."""
    data = graphql(token, """
        query ($login: String!) {
            user(login: $login) {
                followers { totalCount }
                pullRequests { totalCount }
                issues { totalCount }
                repositoriesContributedTo(
                    first: 1
                    contributionTypes: [COMMIT, PULL_REQUEST, ISSUE, REPOSITORY]
                    includeUserRepositories: false
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
        int(u.get('createdAt', '2022-01-01T00:00:00Z')[:4]),  # slice the year from the ISO timestamp
    )


def get_repos_and_stars(token: str, username: str) -> tuple[int, int]:
    """Return (total_owned_repos, total_stars)."""
    query = """
        query ($login: String!, $cursor: String) {
            user(login: $login) {
                repositories(first: 100, after: $cursor, ownerAffiliations: OWNER,
                             orderBy: {field: UPDATED_AT, direction: DESC}) {
                    nodes { stargazerCount }
                    pageInfo { hasNextPage endCursor }
                    totalCount
                }
            }
        }"""
    stars, total, cursor, first = 0, 0, None, True
    while True:
        r = graphql(token, query, {'login': username, 'cursor': cursor})
        r = r.get('user', {}).get('repositories', {})
        if first:
            total, first = r.get('totalCount', 0), False  # capture total count from the first page only
        stars += sum(n.get('stargazerCount', 0) for n in r.get('nodes', []))
        page = r.get('pageInfo', {})
        if not page.get('hasNextPage'):
            break
        cursor = page.get('endCursor')
    return total, stars


def get_commits_for_year(token: str, username: str, year: int) -> int:
    data = graphql(token, """
        query ($login: String!, $from: DateTime!, $to: DateTime!) {
            user(login: $login) {
                contributionsCollection(from: $from, to: $to) {
                    contributionCalendar { totalContributions }
                }
            }
        }""", {'login': username,
               'from': f'{year}-01-01T00:00:00Z',
               'to':   f'{year}-12-31T23:59:59Z'})
    return (data.get('user', {})
               .get('contributionsCollection', {})
               .get('contributionCalendar', {})
               .get('totalContributions', 0))


def get_all_commits(token: str, username: str, creation_year: int) -> int:
    total = 0
    for year in range(creation_year, datetime.datetime.utcnow().year + 1):  # walk every year from account creation to today
        try:
            total += get_commits_for_year(token, username, year)
        except Exception as e:
            print(f'  Warning (commits {year}): {e}', file=sys.stderr)
    return total


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
                                 ownerAffiliations: OWNER, isFork: false) {
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
                                    additions deletions
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
                    login = ((c.get('author') or {}).get('user') or {}).get('login', '')
                    # count commits with no linked GitHub user (terminal pushes) and own linked commits
                    if not login or login.lower() == username.lower():
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

def dual_row(y: int, lbl1: str, v1: str, lbl2: str, v2: str) -> str:
    """Two key-value pairs on one line, dots split evenly between both sides."""
    total = max(3, LINE_WIDTH - 2 - len(lbl1) - 2 - 1 - len(v1)
                - 3 - len(lbl2) - 2 - 1 - len(v2))
    d1 = total // 2   # first half of the dot run
    d2 = total - d1   # second half absorbs any odd remainder
    return trow(y,
        cc('. ') + key(lbl1) + cc(f': {"."*d1} ') + val(v1) +
        cc(' | ') + key(lbl2) + cc(f': {"."*d2} ') + val(v2))

def repos_row(y: int, repos: int, contributed: int, stars: int) -> str:
    """Repos row with contributed count in braces alongside stars."""
    v1 = f'{fmt(repos)} {{Contributed: {fmt(contributed)}}}'
    return dual_row(y, 'Repos', v1, 'Stars', fmt(stars))

def loc_row(y: int, total: int, add: int, delete: int) -> str:
    """Lines of Code with coloured add/del; dots calculated from full text."""
    full_text = f'{fmt(total)} ( {fmt(add)}++, {fmt(delete)}-- )'
    d = pad_dots('Lines of Code', full_text)
    body = (f'<tspan class="value">{esc(fmt(total))} ( '
            f'<tspan class="addColor">{esc(fmt(add))}</tspan>++, '
            f'<tspan class="delColor">{esc(fmt(delete))}</tspan>-- )'
            f'</tspan>')
    return trow(y, cc('. ') + key('Lines of Code') + cc(f': {d} ') + body)

# ---------------------------------------------------------------------------
# SVG builder
# ---------------------------------------------------------------------------

def build_svg(
    ascii_rows: list[str],
    repos: int, contributed: int, stars: int,
    commits: int, followers: int,
    prs: int, issues: int,
    loc_total: int, loc_add: int, loc_del: int,
    colors: dict,
) -> str:

    style = f"""
      @font-face {{
        src: local('Consolas'), local('Consolas Bold');
        font-family: 'ConsolasFallback';
        font-display: swap;
        size-adjust: 109%;
      }}
      .key      {{ fill: {colors['key']};    }}
      .value    {{ fill: {colors['value']};  }}
      .addColor {{ fill: {colors['add']};    }}
      .delColor {{ fill: {colors['delete']}; }}
      .cc       {{ fill: {colors['dots']};   }}
      text, tspan {{ white-space: pre; }}
    """

    # ASCII art at 14px: keeps 44-char lines clear of the stats column at x={STATS_X}
    ascii_tspans = [
        f'    <tspan x="{ASCII_X}" y="{ROW_START + ROW_STEP + 10 + i * ROW_STEP}">{esc(line)}</tspan>'
        for i, line in enumerate(ascii_rows)
    ]

    Y = [ROW_START + i * ROW_STEP for i in range(STATS_ROWS)]

    header_dashes = '-' * (LINE_WIDTH - len('isaac@adjei ') - 1)

    stats_tspans = [
        trow(Y[0],  f'isaac@adjei {header_dashes}'),

        info_row(Y[1],  'Host',     'Aston University'),
        info_row(Y[2],  'Location', 'Birmingham & London, UK'),
        info_row(Y[3],  'Mode',     'Electronic Engineering and Computer Science'),
        info_row(Y[4],  'Kernel',   'Sleep deprived but functional'),
        info_row(Y[5],  'OS',       'Windows, macOS, Ubuntu, Linux'),
        info_row(Y[6],  'IDE',      'JetBrains, VS Code, Visual/Microchip Studio'),

        blank(Y[7]),

        info_row(Y[8],  'Languages.Programming', 'C, C++, Python, TypeScript, Rust'),
        info_row(Y[9],  'Languages.Web',         'HTML, CSS, React, Next.js, Node.js'),
        info_row(Y[10], 'Languages.Hardware',    'Embedded C, MATLAB, Assembly'),
        info_row(Y[11], 'Languages.Real',        'English, French, Twi, Ga'),

        blank(Y[12]),

        info_row(Y[13], 'Hobbies.Software', 'Web Dev, Open Source, Microcontrollers'),
        info_row(Y[14], 'Hobbies.Hardware', 'Embedded Systems, PCB Design'),
        info_row(Y[15], 'Hobbies.Tech',     'Cyber Security, AI/ML, DevOps, SQL'),
        info_row(Y[16], 'Hobbies.General',  'Piano, Running, Gym, Cycling, Gaming'),

        blank(Y[17]),

        section_header(Y[18], 'Contact'),
        info_row(Y[19], 'Portfolio',      'isaacadjei.me'),
        info_row(Y[20], 'Email.Personal', 'hello@isaacadjei.me'),
        info_row(Y[21], 'Email.Work',     'contact@isaacadjei.me'),
        info_row(Y[22], 'LinkedIn',       'linkedin.com/in/isaacadjei'),
        info_row(Y[23], 'Discord',        'zac.nii'),

        blank(Y[24]),

        section_header(Y[25], 'GitHub Stats'),
        repos_row(Y[26], repos, contributed, stars),
        dual_row(Y[27],  'Commits',  fmt(commits),   'Followers', fmt(followers)),
        dual_row(Y[28],  'PRs',      fmt(prs),        'Issues',    fmt(issues)),
        loc_row(Y[29],   loc_total, loc_add, loc_del),
        info_row(Y[30],  'Status',   'One bug away from greatness'),
    ]

    ascii_block = '\n'.join(ascii_tspans)
    stats_block = '\n'.join(stats_tspans)

    return f"""<?xml version='1.0' encoding='UTF-8'?>
<svg xmlns="http://www.w3.org/2000/svg"
     font-family="ConsolasFallback,Consolas,monospace"
     width="{SVG_WIDTH}px" height="{SVG_HEIGHT}px"
     font-size="16px">
  <defs><style>{style}  </style></defs>
  <rect width="{SVG_WIDTH}px" height="{SVG_HEIGHT}px" fill="{colors['bg']}" rx="15"/>
  <!-- ASCII portrait: 14px so 44-char lines stay inside x={STATS_X} -->
  <text x="{ASCII_X}" y="{ROW_START}" fill="{colors['text']}" font-size="14px"
        xml:space="preserve" style="white-space:pre;">
{ascii_block}
  </text>
  <!-- Stats block -->
  <text x="{STATS_X}" y="{ROW_START}" fill="{colors['text']}" style="white-space:pre;">
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
    username = os.environ.get('USER_NAME', USERNAME)  # USER_NAME env var overrides the hardcoded default

    print('Loading ASCII art...')
    ascii_rows = load_ascii_art(ASCII_ART_PATH)

    print('Fetching GitHub stats...')
    try:
        followers, prs, contributed, issues, creation_year = get_user_info(token, username)
    except Exception as e:
        print(f'  Warning: {e}', file=sys.stderr)
        followers, prs, contributed, issues, creation_year = 0, 0, 0, 0, 2022  # safe defaults if the API call fails

    try:
        repos, stars = get_repos_and_stars(token, username)
    except Exception as e:
        print(f'  Warning: {e}', file=sys.stderr)
        repos, stars = 0, 0

    print('  Counting commits...')
    try:
        commits = get_all_commits(token, username, creation_year)
    except Exception as e:
        print(f'  Warning: {e}', file=sys.stderr)
        commits = 0

    print('  Calculating lines of code...')
    try:
        loc_add, loc_del, loc_total = get_loc(token, username)
    except Exception as e:
        print(f'  Warning: {e}', file=sys.stderr)
        loc_add, loc_del, loc_total = 0, 0, 0

    print(f'  Repos: {repos} (Contributed: {contributed}) | Stars: {stars}')
    print(f'  Commits: {commits} | Followers: {followers}')
    print(f'  PRs: {prs} | Issues: {issues}')
    print(f'  LOC: {fmt(loc_total)} ({fmt(loc_add)}++, {fmt(loc_del)}--)')

    for colors, fname in [(DARK, 'dark_mode.svg'), (LIGHT, 'light_mode.svg')]:  # generate both colour theme variants
        print(f'Generating {fname}...')
        svg = build_svg(ascii_rows,
                        repos, contributed, stars,
                        commits, followers, prs, issues,
                        loc_total, loc_add, loc_del, colors)
        with open(fname, 'w', encoding='utf-8') as f:
            f.write(svg)
    print('Done.')


if __name__ == '__main__':
    main()
