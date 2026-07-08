"""Generate self-updating pin-card SVGs for the profile README.

Runs in GitHub Actions (see .github/workflows/pin-cards.yml). Fetches live
repo stats from the GitHub API and renders a Mission Control themed card
(bg #0d1117, accent #FF6B00). Output is force-pushed to the `output-cards`
branch, which the README embeds via raw.githubusercontent.com — so the card
recalculates every time the workflow runs.

Only repos with a live GitHub Pages site belong here; the card links out to
the Pages site, not the repo.
"""

import json
import os
import re
import sys
import urllib.request

ACCENT = "#FF6B00"
BG = "#0d1117"
TEXT = "#ffffff"
MUTED = "#AAAAAA"

# Repos to render. `description` overrides the repo description (useful when
# the repo has none). `slug` becomes the output filename.
REPOS = [
    {
        "repo": "Sampi314/Sam-Personal-Profile",
        "slug": "sam-personal-profile",
        "description": "Interactive portfolio — financial modelling, dashboards & automation demos",
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
    "R": "#198CE7",
    "Jupyter Notebook": "#DA5B0B",
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


if __name__ == "__main__":
    main()
