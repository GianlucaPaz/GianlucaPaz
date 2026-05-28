import requests
import os
from datetime import datetime

USERNAME = os.environ.get('GH_USERNAME', 'gianlucapaz')
TOKEN    = os.environ.get('GITHUB_TOKEN', '')

HEADERS = {
    'Authorization': f'Bearer {TOKEN}',
    'Accept': 'application/vnd.github.v3+json',
}

# ─── Fetch ───────────────────────────────────────────────────────────────────

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
    # ── Stars (repos do próprio usuário) ──────────────────────────────────
    repos = requests.get(
        f'https://api.github.com/users/{USERNAME}/repos',
        params={'per_page': 100, 'type': 'owner'},
        headers=HEADERS,
        timeout=15,
    ).json()
    total_stars = sum(r.get('stargazers_count', 0) for r in repos if isinstance(r, dict))

    # ── Ano de criação da conta ────────────────────────────────────────────
    user_info   = requests.get(f'https://api.github.com/users/{USERNAME}', headers=HEADERS, timeout=15).json()
    created_year = int(user_info.get('created_at', '2020-01-01')[:4])
    current_year = datetime.now().year

    # ── Commits (todos os anos, incluindo repositórios privados) ──────────
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

    # ── PRs, Issues, Contribuiu para ──────────────────────────────────────
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


# ─── SVG ─────────────────────────────────────────────────────────────────────

def generate_svg(stats):
    BG     = '#0d1117'
    BORDER = '#30363d'
    TITLE  = '#e6edf3'
    LABEL  = '#8b949e'
    VALUE  = '#e6edf3'
    FONT   = 'Segoe UI, Ubuntu, sans-serif'

    items = [
        ('⭐', 'Total de Stars',    stats['stars']),
        ('📝', 'Total de Commits',  stats['commits']),
        ('🔀', 'Total de PRs',      stats['prs']),
        ('🐛', 'Total de Issues',   stats['issues']),
        ('📦', 'Contribuiu para',   stats['contribs']),
    ]

    # Layout: coluna esquerda → índices 0, 2, 4 | coluna direita → 1, 3
    left_items  = [items[i] for i in [0, 2, 4]]
    right_items = [items[i] for i in [1, 3]]

    COL_LEFT  = 30
    COL_RIGHT = 260
    COL_W     = 195   # largura de cada coluna (label + valor)
    START_Y   = 88
    ROW_H     = 38

    rows = ''
    for col_x, col in [(COL_LEFT, left_items), (COL_RIGHT, right_items)]:
        for row_idx, (icon, label, value) in enumerate(col):
            y = START_Y + row_idx * ROW_H
            rows += f'''
  <text x="{col_x}" y="{y}" font-family="{FONT}" font-size="13" fill="{LABEL}">{icon}  {label}:</text>
  <text x="{col_x + COL_W}" y="{y}" font-family="{FONT}" font-size="13" font-weight="700" fill="{VALUE}" text-anchor="end">{value}</text>'''

    updated = datetime.utcnow().strftime('%d/%m/%Y %H:%M UTC')

    return f'''<svg width="495" height="195" viewBox="0 0 495 195" xmlns="http://www.w3.org/2000/svg">
  <rect width="495" height="195" rx="4.5" fill="{BG}" stroke="{BORDER}" stroke-width="1"/>

  <!-- Título -->
  <text x="25" y="35" font-family="{FONT}" font-size="14" font-weight="700" fill="{TITLE}">📊 Estatísticas do GitHub de {USERNAME}</text>
  <line x1="25" y1="50" x2="470" y2="50" stroke="{BORDER}" stroke-width="1"/>

  <!-- Stats -->
  {rows}

  <!-- Rodapé -->
  <text x="470" y="185" font-family="{FONT}" font-size="10" fill="{LABEL}" text-anchor="end">Atualizado em {updated}</text>
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
