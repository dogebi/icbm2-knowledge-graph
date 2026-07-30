#!/usr/bin/env python3
"""Build GitHub repos dashboard page with live data from GitHub API."""
import json
import subprocess
import os
import sys
import base64
import time
import re
import argparse
from datetime import datetime, timedelta

REPO_DIR = os.environ.get("GITHUB_WORKSPACE", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMPLATE = os.path.join(REPO_DIR, "dashboard", "github-repos-template.html")
OUTPUT = os.path.join(REPO_DIR, "dashboard", "github-repos.html")
DATA_DIR = os.path.join(REPO_DIR, "data")
CACHE_FILE = os.path.join(DATA_DIR, "github_repos_cache.json")
NEW_REPOS_FILE = os.path.join(DATA_DIR, "github_repos_new.json")

os.makedirs(DATA_DIR, exist_ok=True)

parser = argparse.ArgumentParser(description="Build GitHub repos dashboard page with live data from GitHub API.")
parser.add_argument("--fast", action="store_true", help="Reuse cached commit and README details.")
parser.add_argument("--owner", default=os.environ.get("GITHUB_REPO_OWNER"), help="GitHub owner login to include, for example dogebi.")
args = parser.parse_args()
OWNER = args.owner

# Category mapping
CATEGORY_MAP = {}
cat_items = {
    "🔧 ICBM/에이전트": [
        "hermes_bot", "icbm2-workspace", "icbm-workspace", "icbm2-knowledge-graph",
        "icbm2-skills-marketplace", "icbm2-intelligence-hub", "hermes-landing",
        "ubob_pro_mcp", "ubob_a2a"
    ],
    "📖 재무": ["bookk", "upbit"],
    "🛠 개발 도구": [
        "prompt-advisor", "ccusage-json", "yt-download", "pdf_to_me",
        "ConvertFormat", "rzweb", "repo-dna-analyzer", "git-constellation"
    ],
    "📊 데이터 시각화": [
        "github-board", "github-board2", "cli-board", "hitel-board", "sys8-board",
        "win11-board", "winxp-board", "ubuntu-board", "mac-board", "steam-board",
        "space-board", "commodity-dashboard", "air-management", "world-bank-board",
        "satellite-board", "co2-board", "ip-board", "youtube-board", "token-meter",
        "tech-stack", "tech-toolkit-hub", "code-map", "json-flow", "ai-flowchart",
        "codeviz-ai", "insight-pick", "fire-tribe-base", "ai-agent-radar",
        "skill-worldmap", "dev-trend-oracle", "earthquake"
    ],
    "🎮 게임": [
        "2048", "candy-crush-saga", "gostop", "one-card-game", "poker-king", "liquid-sort",
        "number-connect", "number-link-merge", "wordle", "ladder-game", "watermelon",
        "sand-blast", "castle-breaker", "core-breaker", "wobbly-tower", "diablock",
        "kingdoms3-tradewar", "age-of-exploration-lite", "xcom-lite", "democracy4-lite",
        "block-simCity", "gamedev-lite", "rpg-adv-at", "rpg-adv-bt", "rpg-script-editor",
        "terrarium", "world-box", "mount-and-blade", "department-tycoon", "pixel-farm-story",
        "dungeon-story", "real-estate-king", "capitalism-web", "grand-prix", "convenience24",
        "juice-tycoon", "3d-physics-lab", "predator", "iron-dome", "lightning-strike",
        "stonks-9800", "ai-buy-sell", "decision-genie", "core-video-editor",
        "pixedit", "3d-fractal", "svg-converter", "core-image-converter", "text-sync-check",
        "make-app-wiz", "google-script-wizard", "appscript_board",
        "core-markdown-editor", "relationship-visualizer",
        "lifeGame", "geoPoly", "Tetris-am3d", "enterprise_ceo", "royal_secretary",
        "Idle_RPG", "FootballClub", "Kingdoms3Lite", "ChampionMaker", "FireworksMaster",
        "deckbuilder-adventure", "super-robot-lite", "kbo-manager", "3d-block-world-edit",
        "stock-game", "stock-invest-game", "World_War_Simulator"
    ],
    "📱 iOS/macOS": ["ios_hyperclovax", "ubob_pro_lite"],
    "🌐 웹 프로젝트": [
        "ubobtest", "KakaoSplit", "keyword_fighter", "DevCanvas", "pages", "blog",
        "astrocartography", "terrain", "world-data-map", "github-portfolio",
        "artseedjs"
    ],
    "📋 기타": ["ai-image-generator", "jiah_ai1"]
}
for cat, names in cat_items.items():
    for name in names:
        CATEGORY_MAP[name] = cat

# Keyword-based auto category recommendation
KEYWORD_MAP = {
    "🎮 게임": ["game", "게임", "rpg", "simulator", "시뮬레이션"],
    "📊 데이터 시각화": ["board", "dashboard", "chart", "시각화", "visualization", "radar", "map"],
    "🛠 개발 도구": ["tool", "editor", "converter", "도구", "analyzer"],
    "🔧 ICBM/에이전트": ["icbm", "hermes", "에이전트"],
    "📖 재무": ["bookk", "finance", "accounting", "재무", "stock", "주식"],
    "📱 iOS/macOS": ["ios", "swift", "macos", "ipad", "iphone"],
}

def suggest_category(repo_name, repo_desc=""):
    """Suggest category based on keywords for uncategorized repos."""
    text = (repo_name + " " + (repo_desc or "")).lower()
    for cat, keywords in KEYWORD_MAP.items():
        for kw in keywords:
            if kw in text:
                return cat
    return "📋 기타"

def run_gh_json(args):
    """Run gh CLI command and return parsed JSON."""
    result = subprocess.run(
        ['gh', 'api'] + args,
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None

def run_gh_raw(args):
    """Run gh CLI command and return raw stdout."""
    result = subprocess.run(
        ['gh', 'api'] + args,
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()

# ─── Step 1: Fetch ALL repos via REST API ───
print("📦 Fetching repos from GitHub API...")
repos_raw = []
page = 1
while True:
    batch = run_gh_json([f'user/repos?per_page=100&sort=updated&page={page}'])
    if not batch or not isinstance(batch, list) or len(batch) == 0:
        break
    repos_raw.extend(batch)
    print(f"  Page {page}: {len(batch)} repos")
    page += 1
    if len(batch) < 100:
        break

print(f"Total repos fetched: {len(repos_raw)}")
if OWNER:
    repos_raw = [
        r for r in repos_raw
        if (r.get('owner') or {}).get('login', '').lower() == OWNER.lower()
    ]
    print(f"Repos for owner {OWNER}: {len(repos_raw)}")

# ─── Step 2: Normalize repo data ───
repos = []
for r in repos_raw:
    owner = (r.get('owner') or {}).get('login') or OWNER or ''
    repo = {
        'name': r.get('name'),
        'repo_name': r.get('name'),
        'owner': owner,
        'full_name': r.get('full_name') or f"{owner}/{r.get('name')}",
        'description': r.get('description'),
        'url': r.get('html_url', ''),
        'homepageUrl': r.get('homepage', ''),
        'stargazerCount': r.get('stargazers_count', 0),
        'forkCount': r.get('forks_count', 0),
        'isPrivate': r.get('private', False),
        'createdAt': r.get('created_at'),
        'updatedAt': r.get('updated_at'),
        'pushed_at': r.get('pushed_at'),
        'open_issues_count': r.get('open_issues_count', 0),
        'has_pages': r.get('has_pages', False),
        'size': r.get('size', 0),
        'visibility': r.get('visibility', 'private'),
        'default_branch': r.get('default_branch', 'main'),
        'topics': r.get('topics', []),
        'license_spdx_id': r.get('license', {}).get('spdx_id') if r.get('license') else None,
        'language': r.get('language'),  # REST API returns string directly
    }
    repos.append(repo)

# ─── Step 3: Detect stale repos (pushed_at > 6 months ago) ───
six_months_ago = datetime.now() - timedelta(days=180)
for repo in repos:
    pushed = repo.get('pushed_at')
    if pushed:
        try:
            pushed_date = datetime.strptime(pushed, "%Y-%m-%dT%H:%M:%SZ")
            repo['is_stale'] = pushed_date < six_months_ago
        except ValueError:
            repo['is_stale'] = False
    else:
        repo['is_stale'] = True

# ─── Step 4: Fetch recent commit + README for each repo ───
# Support --fast flag to skip commit/README fetching (use cached data)
FAST_MODE = args.fast

if FAST_MODE and os.path.exists(CACHE_FILE):
    print("⚡ Fast mode: loading commits/READMEs from cache...")
    try:
        with open(CACHE_FILE, 'r') as f:
            cached_repos = {(r.get('full_name') or r['name']): r for r in json.load(f)}
        for repo in repos:
            cached = cached_repos.get(repo['full_name']) or cached_repos.get(repo['name'])
            if cached:
                repo['last_commit_sha'] = cached.get('last_commit_sha')
                repo['last_commit_msg'] = cached.get('last_commit_msg')
                repo['last_commit_date'] = cached.get('last_commit_date')
                repo['readme_preview'] = cached.get('readme_preview')
            else:
                repo['last_commit_sha'] = None
                repo['last_commit_msg'] = None
                repo['last_commit_date'] = None
                repo['readme_preview'] = None
        print(f"  Loaded from cache ({len(cached_repos)} repos)")
    except Exception as e:
        print(f"  Cache error: {e}, falling back to full fetch")
        FAST_MODE = False

if not FAST_MODE:
    print("🔄 Fetching commits and READMEs...")
    for i, repo in enumerate(repos):
        full_name = f"repos/{repo['full_name']}"

        # Fetch latest commit
        commit_data = run_gh_json([f"{full_name}/commits?per_page=1"])
        if commit_data and isinstance(commit_data, list) and len(commit_data) > 0:
            c = commit_data[0]
            repo['last_commit_sha'] = c['sha'][:7]
            repo['last_commit_msg'] = c['commit']['message'].split('\n')[0]
            repo['last_commit_date'] = c['commit']['committer']['date']
        else:
            repo['last_commit_sha'] = None
            repo['last_commit_msg'] = None
            repo['last_commit_date'] = None

        # Fetch README
        readme_raw = run_gh_raw([f"{full_name}/readme", '--jq', '.content'])
        if readme_raw:
            try:
                readme_text = base64.b64decode(readme_raw).decode('utf-8', errors='replace')
                repo['readme_preview'] = readme_text[:500]
            except Exception:
                repo['readme_preview'] = None
        else:
            repo['readme_preview'] = None

        if (i + 1) % 10 == 0 or i == len(repos) - 1:
            print(f"  Progress: {i+1}/{len(repos)} repos")

        time.sleep(0.5)  # Rate limit safety

    print("✅ Commits and READMEs fetched")

# ─── Step 5: Load previous cache and detect new repos ───
prev_names = set()
if os.path.exists(CACHE_FILE):
    try:
        with open(CACHE_FILE, 'r') as f:
            prev_cache = json.load(f)
            prev_names = {r['name'] for r in prev_cache}
        print(f"📋 Previous cache: {len(prev_names)} repos")
    except Exception as e:
        print(f"  WARNING: Could not load cache: {e}")

new_repos = []
for repo in repos:
    is_new = repo['name'] not in prev_names
    repo['new_repo'] = is_new
    if is_new:
        suggested = suggest_category(repo['name'], repo.get('description', ''))
        if repo['name'] in CATEGORY_MAP:
            repo['suggested_category'] = CATEGORY_MAP[repo['name']]
        else:
            repo['suggested_category'] = suggested
        new_repos.append({
            'name': repo['name'],
            'repo_name': repo.get('repo_name'),
            'owner': repo.get('owner'),
            'full_name': repo.get('full_name'),
            'description': repo.get('description'),
            'url': repo['url'],
            'suggested_category': repo['suggested_category'],
            'isPrivate': repo.get('isPrivate'),
            'language': repo.get('language'),
        })

if new_repos:
    print(f"🆕 New repos detected: {len(new_repos)}")
    for nr in new_repos:
        print(f"  + {nr['name']} → {nr['suggested_category']}")
else:
    print("ℹ️ No new repos detected")

# ─── Step 6: Assign categories ───
for repo in repos:
    if repo['name'] in CATEGORY_MAP:
        repo['category'] = CATEGORY_MAP[repo['name']]
    elif repo.get('new_repo'):
        repo['category'] = repo.get('suggested_category', '📋 기타')
    else:
        repo['category'] = suggest_category(repo['name'], repo.get('description', ''))

# Sort by category then stars
repos.sort(key=lambda r: (r['category'], -(r['stargazerCount'] or 0), r['name']))

LANGUAGE_COLORS = {
    'TypeScript': '#3178c6',
    'JavaScript': '#f7df1e',
    'Python': '#3776ab',
    'Swift': '#f05138',
    'CSS': '#663399',
    'HTML': '#e34c26',
}

def graph_node(repo, idx):
    stars = repo.get('stargazerCount') or 0
    size = min(22, 8 + stars * 2 + (2 if repo.get('new_repo') else 0))
    language = repo.get('language') or repo.get('visibility') or 'Repository'
    return {
        **repo,
        'id': idx,
        'title': repo['name'],
        'display_name': repo['full_name'],
        'entity_type': language,
        'size': size,
        'color': LANGUAGE_COLORS.get(repo.get('language'), '#60a5fa'),
        'date': repo.get('pushed_at') or repo.get('updatedAt') or repo.get('createdAt'),
        'is_entity': repo.get('isPrivate', False),
    }

graph_nodes = [graph_node(repo, idx) for idx, repo in enumerate(repos)]

STOPWORDS = {
    'app', 'api', 'web', 'test', 'demo', 'main', 'code', 'data', 'repo',
    'with', 'for', 'the', 'and', 'new', 'old', 'version', 'project',
}

def repo_tokens(repo):
    text = f"{repo.get('name') or ''} {repo.get('description') or ''}".lower()
    return {
        token for token in re.split(r'[^a-z0-9]+', text)
        if len(token) >= 3 and token not in STOPWORDS
    }

def build_graph_links(nodes, max_degree=5, max_links=650):
    token_sets = [repo_tokens(node) for node in nodes]
    candidates = []

    # ponytail: O(n^2) is fine for a few hundred repos; index tokens if this grows past a few thousand.
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            a, b = nodes[i], nodes[j]
            score = 0
            link_type = 'same_category'

            if a.get('category') == b.get('category'):
                score += 2
            if a.get('language') and a.get('language') == b.get('language'):
                score += 1

            shared_topics = set(a.get('topics') or []) & set(b.get('topics') or [])
            if shared_topics:
                score += min(6, len(shared_topics) * 3)
                link_type = 'mentions'

            shared_words = token_sets[i] & token_sets[j]
            if shared_words:
                score += min(3, len(shared_words))
                link_type = 'co_occurrence'

            if score >= 3:
                candidates.append((-score, i, j, link_type))

    degree = [0] * len(nodes)
    links = []
    for neg_score, source, target, link_type in sorted(candidates):
        if degree[source] >= max_degree or degree[target] >= max_degree:
            continue
        links.append({
            'source': source,
            'target': target,
            'type': link_type,
            'weight': -neg_score,
        })
        degree[source] += 1
        degree[target] += 1
        if len(links) >= max_links:
            break
    return links

graph_links = build_graph_links(graph_nodes)

# ─── Step 7: Save cache ───
cache_data = []
for repo in repos:
    cache_data.append({
        'name': repo['name'],
        'repo_name': repo.get('repo_name'),
        'owner': repo.get('owner'),
        'full_name': repo.get('full_name'),
        'description': repo.get('description'),
        'url': repo['url'],
        'homepageUrl': repo.get('homepageUrl'),
        'stargazerCount': repo.get('stargazerCount', 0),
        'forkCount': repo.get('forkCount', 0),
        'isPrivate': repo.get('isPrivate', False),
        'createdAt': repo.get('createdAt'),
        'updatedAt': repo.get('updatedAt'),
        'pushed_at': repo.get('pushed_at'),
        'language': repo.get('language'),
        'category': repo['category'],
    })

with open(CACHE_FILE, 'w', encoding='utf-8') as f:
    json.dump(cache_data, f, ensure_ascii=False)
print(f"💾 Cache saved: {CACHE_FILE}")

# Save new repos list
with open(NEW_REPOS_FILE, 'w', encoding='utf-8') as f:
    json.dump(new_repos, f, ensure_ascii=False, indent=2)
print(f"💾 New repos saved: {NEW_REPOS_FILE}")

# ─── Step 8: Build output HTML ───
print("🏗️ Building dashboard HTML...")

with open(TEMPLATE, 'r', encoding='utf-8') as f:
    html = f.read()

if '__REPOS_PLACEHOLDER__' not in html:
    print("ERROR: __REPOS_PLACEHOLDER__ not found in template!")
    sys.exit(1)

# Use separators to minimize JSON (no newlines that could break inline JS)
repos_json = json.dumps(graph_nodes, ensure_ascii=False, separators=(',', ':'))
links_json = json.dumps(graph_links, ensure_ascii=False, separators=(',', ':'))
html = html.replace('__REPOS_PLACEHOLDER__', repos_json)
html = re.sub(
    r'const links = \[.*?\];',
    f'const links = {links_json};',
    html,
    count=1,
    flags=re.DOTALL,
)

# Inject build timestamp
build_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
html = html.replace('__BUILD_TIME__', build_time)
html = re.sub(r'<span>📊 노드 \d+개</span>', f'<span>📊 노드 {len(graph_nodes)}개</span>', html, count=1)
html = re.sub(r'<span>🔗 연결 \d+개</span>', f'<span>🔗 연결 {len(graph_links)}개</span>', html, count=1)
html = re.sub(r'<span>📅 \d{4}-\d{2}-\d{2}</span>', f'<span>📅 {datetime.now():%Y-%m-%d}</span>', html, count=1)

with open(OUTPUT, 'w', encoding='utf-8') as f:
    f.write(html)

# Verify placeholder is gone
with open(OUTPUT, 'r', encoding='utf-8') as f:
    output = f.read()
if '__REPOS_PLACEHOLDER__' in output:
    print("ERROR: Placeholder still present in output!")
    sys.exit(1)

print(f"✅ Built: {OUTPUT}")
print(f"   Output size: {len(output):,} bytes")
print(f"   Repos injected: {len(graph_nodes)}")
print(f"   Links injected: {len(graph_links)}")
print(f"   New repos: {len(new_repos)}")
print(f"   Stale repos: {sum(1 for r in repos if r.get('is_stale'))}")
print("🎉 Done!")
