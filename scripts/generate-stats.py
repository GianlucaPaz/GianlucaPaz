import requests
import os
from datetime import datetime, timezone, timedelta

USERNAME = os.environ.get('GH_USERNAME', 'gianlucapaz')
TOKEN    = os.environ.get('GITHUB_TOKEN', '')

HEADERS = {
    'Authorization': f'Bearer {TOKEN}',
    'Accept': 'application/vnd.github.v3+json',
}

BRT = timezone(timedelta(hours=-3))

# ─── Fetch ────────────────────────────────────────────────────────────────────

def graphql(query, variables=None):
    resp = requests.post(
        'https://api.github.com/graphql',
        headers={**HEADERS, 'Content-Type': 'application/json'},
        json={'query': query, 'variables': variables or {}},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_stats():
    repos = requests.get(
        f'https://api.github.com/users/{USERNAME}/repos',
        params={'per_page': 100, 'type': 'owner'},
        headers=HEADERS,
        timeout=15,
    ).json()
    total_stars = sum(r.get('stargazers_count', 0) for r in repos if isinstance(r, dict))

    user_info    = requests.get(f'https://api.github.com/users/{USERNAME}', headers=HEADERS, timeout=15).json()
    created_year = int(user_info.get('created_at', '2020-01-01')[:4])
    current_year = datetime.now(BRT).year

    commit_query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          totalCommitContributions
          restrictedContributionsCount
        }
      }
    }
    """
    total_commits = 0
    for year in range(created_year, current_year + 1):
        data = graphql(commit_query, {
            'login': USERNAME,
            'from':  f'{year}-01-01T00:00:00Z',
            'to':    f'{year}-12-31T23:59:59Z',
        })
        cc = data.get('data', {}).get('user', {}).get('contributionsCollection', {})
        total_commits += cc.get('totalCommitContributions', 0) + cc.get('restrictedContributionsCount', 0)

    misc_query = """
    query($login: String!) {
      user(login: $login) {
        pullRequests { totalCount }
        issues       { totalCount }
        repositoriesContributedTo(
          contributionTypes: [COMMIT, ISSUE, PULL_REQUEST, REPOSITORY]
        ) { totalCount }
      }
    }
    """
    misc = graphql(misc_query, {'login': USERNAME}).get('data', {}).get('user', {})

    return {
        'stars':   total_stars,
        'commits': total_commits,
        'prs':     misc.get('pullRequests', {}).get('totalCount', 0),
        'issues':  misc.get('issues',       {}).get('totalCount', 0),
        'contribs':misc.get('repositoriesContributedTo', {}).get('totalCount', 0),
    }


# ─── SVG ──────────────────────────────────────────────────────────────────────

def generate_svg(stats):
    BG      = '#161b22'
    BORDER  = '#e1e4e8'
    TITLE   = '#ffffff'
    LABEL   = '#8b949e'
    VALUE   = '#ffffff'
    DIVIDER = '#21262d'
    FONT    = 'Segoe UI, Ubuntu, sans-serif'

    items = [
        ('⭐', 'Total de Stars',   stats['stars']),
        ('📝', 'Total de Commits', stats['commits']),
        ('🔀', 'Total de PRs',     stats['prs']),
        ('🐛', 'Total de Issues',  stats['issues']),
        ('📦', 'Contribuiu para',  stats['contribs']),
    ]

    # Coluna esquerda: índices 0, 2, 4 | Coluna direita: 1, 3
    left_items  = [items[i] for i in [0, 2, 4]]
    right_items = [items[i] for i in [1, 3]]

    START_Y = 78
    ROW_H   = 36

    rows = ''
    columns = [
        (left_items,  22,  240),
        (right_items, 258, 473),
    ]
    for col_items, x_start, x_val in columns:
        for row_idx, (icon, label, value) in enumerate(col_items):
            y = START_Y + row_idx * ROW_H
            rows += f'''
  <text x="{x_start}" y="{y}" font-family="{FONT}" font-size="13" fill="{LABEL}">{icon}  {label}:</text>
  <text x="{x_val}" y="{y}" font-family="{FONT}" font-size="13" font-weight="700" fill="{VALUE}" text-anchor="end">{value}</text>'''

    now     = datetime.now(BRT)
    updated = now.strftime('%d/%m/%Y %H:%M (BRT)')

    return f'''<svg width="495" height="185" viewBox="0 0 495 185" xmlns="http://www.w3.org/2000/svg">
  <rect x="0.5" y="0.5" width="494" height="184" rx="8" fill="{BG}" stroke="{BORDER}" stroke-width="1"/>

  <text x="22" y="30" font-family="{FONT}" font-size="15" font-weight="700" fill="{TITLE}">Estatísticas do GitHub de {USERNAME}</text>
  <line x1="22" y1="44" x2="473" y2="44" stroke="{DIVIDER}" stroke-width="1"/>

  {rows}

  <text x="473" y="174" font-family="{FONT}" font-size="10" fill="{LABEL}" text-anchor="end">Atualizado em {updated}</text>
</svg>'''


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print(f'Buscando stats de @{USERNAME}...')
    stats = fetch_stats()
    print('Stats:', stats)

    svg = generate_svg(stats)

    os.makedirs('assets', exist_ok=True)
    with open('assets/github-stats.svg', 'w', encoding='utf-8') as f:
        f.write(svg)

    print('✅  assets/github-stats.svg gerado com sucesso!')
