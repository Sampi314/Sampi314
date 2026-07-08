"""Generate self-updating SVG cards for the profile README.

Runs in GitHub Actions (see .github/workflows/pin-cards.yml). Fetches live
data from the GitHub API and renders Mission Control themed cards
(bg #0d1117, accent #FF6B00). Output is force-pushed to the `output-cards`
branch, which the README embeds via raw.githubusercontent.com — so every
card recalculates each time the workflow runs.

Two card types:
  - Pin cards, one per entry in REPOS (Featured Work section). Only repos
    with a live GitHub Pages site belong here; the README links each card
    to its Pages site, not the repo.
  - A profile stats card (TELEMETRY section) replacing the paused
    github-readme-stats.vercel.app service.
"""

import datetime
import json
import os
import re
import sys
import urllib.request

ACCENT = "#FF6B00"
BG = "#0d1117"
TEXT = "#ffffff"
MUTED = "#AAAAAA"

STATS_USER = "Sampi314"

# Repos to render as pin cards. `description` overrides the repo description
# (useful when the repo has none). `slug` becomes the output filename.
REPOS = [
    {
        "repo": "Sampi314/Sam-Personal-Profile",
        "slug": "sam-personal-profile",
        "description": "Interactive portfolio — financial modelling, dashboards & automation demos",
    },
    {
        "repo": "Sampi314/Sam-Tools",
        "slug": "sam-tools",
        "description": "Free Excel 365 productivity add-in — compare workbooks cell-by-cell & trace formulas across sheets",
    },
    {
        "repo": "Sampi314/Atelier-Image",
        "slug": "atelier-image",
        "description": "Batch image generator built on Gemini 3 Flash — compose prompts, anchor styles, queue generations",
    },
    {
        "repo": "Sampi314/Cosmic-Arcade",
        "slug": "cosmic-arcade",
        "description": "Five classic browser games in vanilla HTML/CSS/JS — Word Chain, Sudoku, Card Flip, Gomoku & more",
    },
    {
        "repo": "Sampi314/Folio-Library",
        "slug": "folio-library",
        "description": "A personal library that reads itself aloud — EPUBs, PDFs, manga. Local-first, browser-native",
    },
    {
        "repo": "Sampi314/Lexicon-Teochew",
        "slug": "lexicon-teochew",
        "description": "Học Tiếng Triều Châu — interactive Teochew language learning app",
    },
    {
        "repo": "Sampi314/Sieve",
        "slug": "sieve",
        "description": "Checkerboard Number Mesh — interactive number grid visualiser",
    },
    {
        "repo": "Sampi314/Folio-Menu",
        "slug": "folio-menu",
        "description": "Hôm nay ăn gì? — random Vietnamese meal picker for when you can't decide",
    },
]

# GitHub linguist colours for the language bar.
LANG_COLORS = {
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "JavaScript": "#f1e05a",
    "Python": "#3572A5",
    "TypeScript": "#3178c6",
    "VBA": "#867db1",
    "Visual Basic .NET": "#945db7",
    "R": "#198CE7",
    "Jupyter Notebook": "#DA5B0B",
    "PowerShell": "#012456",
    "Astro": "#ff5a03",
}
LANG_FALLBACK = "#8b949e"


def api(path, token):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "pin-card-generator",
        },
    )
    return urllib.request.urlopen(req)


def api_json(path, token):
    with api(path, token) as resp:
        return json.load(resp)


def commit_count(repo, token):
    with api(f"/repos/{repo}/commits?per_page=1", token) as resp:
        link = resp.headers.get("Link", "")
    match = re.search(r'page=(\d+)>; rel="last"', link)
    return int(match.group(1)) if match else 1


def esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def wrap(text, width=58, max_lines=2):
    words, lines, line = text.split(), [], ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if len(candidate) > width and line:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][: width - 1] + "…"
    return lines


def render_card(info, languages, commits, description):
    width, pad = 445, 20
    bar_w = width - 2 * pad
    total = sum(languages.values()) or 1
    shares = [(lang, size / total) for lang, size in
              sorted(languages.items(), key=lambda kv: -kv[1])]

    # Stacked language bar.
    bar, x = [], pad
    for lang, share in shares:
        seg = share * bar_w
        color = LANG_COLORS.get(lang, LANG_FALLBACK)
        bar.append(f'<rect x="{x:.1f}" y="88" width="{seg:.1f}" height="8" fill="{color}" />')
        x += seg

    legend, x = [], pad
    for lang, share in shares[:4]:
        color = LANG_COLORS.get(lang, LANG_FALLBACK)
        label = f"{lang} {share * 100:.1f}%"
        legend.append(
            f'<circle cx="{x + 4}" cy="112" r="4" fill="{color}" />'
            f'<text x="{x + 13}" y="116" class="legend">{esc(label)}</text>'
        )
        x += 13 + len(label) * 6.3 + 16

    desc_lines = "".join(
        f'<tspan x="{pad}" dy="{0 if i == 0 else 15}">{esc(line)}</tspan>'
        for i, line in enumerate(wrap(description))
    )
    updated = info["pushed_at"][:10]

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="150" viewBox="0 0 {width} 150" role="img" aria-label="{esc(info['name'])} live stats">
  <style>
    text {{ font-family: 'JetBrains Mono', 'Segoe UI', Ubuntu, monospace; }}
    .title {{ font-size: 15px; font-weight: 600; fill: {ACCENT}; }}
    .chip {{ font-size: 10px; font-weight: 600; fill: {ACCENT}; letter-spacing: 1px; }}
    .desc {{ font-size: 12px; fill: {TEXT}; }}
    .legend {{ font-size: 11px; fill: {MUTED}; }}
    .stats {{ font-size: 11px; fill: {MUTED}; }}
    .statnum {{ fill: {TEXT}; font-weight: 600; }}
  </style>
  <rect width="{width}" height="150" rx="8" fill="{BG}" />
  <path transform="translate({pad},18)" fill="{ACCENT}" d="M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5Zm10.5-1h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 4.5 9h8ZM5 12.25a.25.25 0 0 1 .25-.25h3.5a.25.25 0 0 1 .25.25v3.25a.25.25 0 0 1-.4.2l-1.45-1.087a.249.249 0 0 0-.3 0L5.4 15.7a.25.25 0 0 1-.4-.2Z"/>
  <text x="{pad + 24}" y="31" class="title">{esc(info['name'])}</text>
  <text x="{width - pad}" y="30" text-anchor="end" class="chip">● LIVE ▸</text>
  <text x="{pad}" y="56" class="desc">{desc_lines}</text>
  {''.join(bar)}
  {''.join(legend)}
  <text x="{pad}" y="138" class="stats">★ <tspan class="statnum">{info['stargazers_count']}</tspan>&#160;&#160;⑂ <tspan class="statnum">{info['forks_count']}</tspan>&#160;&#160;COMMITS <tspan class="statnum">{commits}</tspan></text>
  <text x="{width - pad}" y="138" text-anchor="end" class="stats">UPDATED {updated}</text>
</svg>
"""


def search_count(query, token):
    return api_json(f"/search/{query}", token)["total_count"]


def fetch_profile_stats(token):
    """Each metric degrades to None independently so one API hiccup
    doesn't blank the whole card."""
    year = datetime.date.today().year
    stats = {"year": year}

    def grab(key, fn):
        try:
            stats[key] = fn()
        except Exception as err:
            print(f"warn: could not fetch {key}: {err}", file=sys.stderr)
            stats[key] = None

    def total_stars():
        stars, page = 0, 1
        while True:
            repos = api_json(f"/user/repos?affiliation=owner&per_page=100&page={page}", token)
            stars += sum(r["stargazers_count"] for r in repos)
            if len(repos) < 100:
                return stars
            page += 1

    grab("stars", total_stars)
    grab("commits_year", lambda: search_count(
        f"commits?q=author:{STATS_USER}+author-date:>={year}-01-01", token))
    grab("commits_total", lambda: search_count(f"commits?q=author:{STATS_USER}", token))
    grab("prs", lambda: search_count(f"issues?q=type:pr+author:{STATS_USER}", token))
    grab("issues", lambda: search_count(f"issues?q=type:issue+author:{STATS_USER}", token))
    grab("reviews", lambda: search_count(f"issues?q=type:pr+reviewed-by:{STATS_USER}", token))
    grab("followers", lambda: api_json(f"/users/{STATS_USER}", token)["followers"])
    return stats


def calculate_rank(stats):
    """github-readme-stats rank algorithm (src/calculateRank.js), so the
    letter matches what the original card would have shown."""
    exp_cdf = lambda x: 1 - 2 ** -x
    log_norm_cdf = lambda x: x / (1 + x)

    commits = stats["commits_year"] if stats["commits_year"] is not None else (stats["commits_total"] or 0)
    commits_median = 250 if stats["commits_year"] is not None else 1000
    weighted = (
        2 * exp_cdf(commits / commits_median)
        + 3 * exp_cdf((stats["prs"] or 0) / 50)
        + 1 * exp_cdf((stats["issues"] or 0) / 25)
        + 1 * exp_cdf((stats["reviews"] or 0) / 2)
        + 4 * log_norm_cdf((stats["stars"] or 0) / 50)
        + 1 * log_norm_cdf((stats["followers"] or 0) / 10)
    )
    percentile = (1 - weighted / 12) * 100
    for threshold, level in zip(
        [1, 12.5, 25, 37.5, 50, 62.5, 75, 87.5, 100],
        ["S", "A+", "A", "A-", "B+", "B", "B-", "C+", "C"],
    ):
        if percentile <= threshold:
            return level, percentile
    return "C", percentile


def render_stats_card(stats):
    width, height, pad = 445, 180, 24
    year = stats["year"]

    def fmt(value):
        if value is None:
            return "—"
        return f"{value / 1000:.1f}k" if value >= 1000 else str(value)

    rows = [
        ("★", "TOTAL STARS", stats["stars"]),
        ("↻", f"COMMITS {year}", stats["commits_year"]),
        ("∑", "ALL-TIME COMMITS", stats["commits_total"]),
        ("⇅", "TOTAL PRs", stats["prs"]),
        ("◎", "TOTAL ISSUES", stats["issues"]),
        ("⚉", "FOLLOWERS", stats["followers"]),
    ]
    row_svg = "".join(
        f'<text x="{pad}" y="{62 + i * 19}" class="icon">{icon}</text>'
        f'<text x="{pad + 22}" y="{62 + i * 19}" class="label">{label}</text>'
        f'<text x="{pad + 195}" y="{62 + i * 19}" text-anchor="end" class="value">{fmt(value)}</text>'
        for i, (icon, label, value) in enumerate(rows)
    )

    # Ring showing the github-readme-stats letter rank; fill = score share.
    level, percentile = calculate_rank(stats)
    ring_fill = max(0.04, 1 - percentile / 100)
    ring_x, ring_y, radius = 340, 102, 46
    circumference = 2 * 3.14159 * radius
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{STATS_USER} GitHub stats">
  <style>
    text {{ font-family: 'JetBrains Mono', 'Segoe UI', Ubuntu, monospace; }}
    .title {{ font-size: 15px; font-weight: 600; fill: {ACCENT}; letter-spacing: 1px; }}
    .icon {{ font-size: 12px; fill: {ACCENT}; }}
    .label {{ font-size: 11px; fill: {MUTED}; letter-spacing: 0.5px; }}
    .value {{ font-size: 12px; font-weight: 600; fill: {TEXT}; }}
    .ringnum {{ font-size: 30px; font-weight: 700; fill: {TEXT}; }}
    .ringlabel {{ font-size: 9px; fill: {ACCENT}; letter-spacing: 1px; }}
  </style>
  <rect width="{width}" height="{height}" rx="8" fill="{BG}" />
  <text x="{pad}" y="34" class="title">// GITHUB STATS</text>
  {row_svg}
  <circle cx="{ring_x}" cy="{ring_y}" r="{radius}" fill="none" stroke="#21262d" stroke-width="7" />
  <circle cx="{ring_x}" cy="{ring_y}" r="{radius}" fill="none" stroke="{ACCENT}" stroke-width="7"
          stroke-linecap="round" stroke-dasharray="{circumference * ring_fill:.1f} {circumference:.1f}"
          transform="rotate(-90 {ring_x} {ring_y})" />
  <text x="{ring_x}" y="{ring_y + 8}" text-anchor="middle" class="ringnum">{level}</text>
  <text x="{ring_x}" y="{ring_y + 26}" text-anchor="middle" class="ringlabel">RANK</text>
</svg>
"""


def main():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("GITHUB_TOKEN env var is required (PIN_TOKEN secret in CI).")

    out_dir = sys.argv[1] if len(sys.argv) > 1 else "cards"
    os.makedirs(out_dir, exist_ok=True)

    for entry in REPOS:
        repo = entry["repo"]
        try:
            info = api_json(f"/repos/{repo}", token)
            languages = api_json(f"/repos/{repo}/languages", token)
            commits = commit_count(repo, token)
        except Exception as err:
            sys.exit(
                f"Failed to fetch {repo}: {err}\n"
                "If this repo is private, the PIN_TOKEN secret must be a PAT "
                "with read access to it (see .github/workflows/pin-cards.yml)."
            )
        description = entry.get("description") or info.get("description") or ""
        path = os.path.join(out_dir, f"{entry['slug']}-pin.svg")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(render_card(info, languages, commits, description))
        print(f"wrote {path}")

    stats_path = os.path.join(out_dir, "github-stats.svg")
    with open(stats_path, "w", encoding="utf-8") as fh:
        fh.write(render_stats_card(fetch_profile_stats(token)))
    print(f"wrote {stats_path}")


if __name__ == "__main__":
    main()
