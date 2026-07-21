#!/usr/bin/env python3

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone


USERNAME = os.environ.get("GITHUB_USERNAME", "zacniewski")
TOKEN = os.environ.get("GITHUB_TOKEN", "")


def graphql_query(query: str, variables: dict) -> dict:
    payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {TOKEN}" if TOKEN else "",
            "User-Agent": "github-stats-generator",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub GraphQL request failed: {err.code} {body}") from err


def escape_xml(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def render_card(title: str, rows: list[tuple[str, str]], width: int = 460, height: int = 170) -> str:
    line_start = 68
    line_step = 26
    row_svg = []

    for i, (label, value) in enumerate(rows):
        y = line_start + i * line_step
        row_svg.append(
            f'<text x="24" y="{y}" font-size="14" fill="#c9d1d9">{escape_xml(label)}</text>'
            f'<text x="{width - 24}" y="{y}" font-size="14" text-anchor="end" fill="#f0f6fc">{escape_xml(value)}</text>'
        )

    return f"""<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"{width}\" height=\"{height}\" viewBox=\"0 0 {width} {height}\" role=\"img\" aria-label=\"{escape_xml(title)}\">
  <defs>
    <linearGradient id=\"bg\" x1=\"0\" y1=\"0\" x2=\"1\" y2=\"1\">
      <stop offset=\"0%\" stop-color=\"#0d1117\"/>
      <stop offset=\"100%\" stop-color=\"#161b22\"/>
    </linearGradient>
  </defs>
  <rect width=\"100%\" height=\"100%\" rx=\"14\" fill=\"url(#bg)\" stroke=\"#30363d\"/>
  <text x=\"24\" y=\"38\" font-size=\"18\" font-weight=\"700\" fill=\"#58a6ff\">{escape_xml(title)}</text>
  {''.join(row_svg)}
</svg>
"""


def main() -> None:
    query = """
    query($login: String!) {
      user(login: $login) {
        name
        followers { totalCount }
        repositories(ownerAffiliations: OWNER, isFork: false, first: 100) {
          totalCount
          nodes {
            stargazerCount
            languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
              edges {
                size
                node { name }
              }
            }
          }
        }
        contributionsCollection {
          contributionCalendar {
            totalContributions
          }
        }
      }
    }
    """

    error_message = None
    try:
        data = graphql_query(query, {"login": USERNAME})
        if "errors" in data:
            raise RuntimeError(f"GraphQL errors: {data['errors']}")

        user = data["data"]["user"]
        repos = user["repositories"]["nodes"]

        stars = sum(repo["stargazerCount"] for repo in repos)
        repo_count = user["repositories"]["totalCount"]
        followers = user["followers"]["totalCount"]
        contribs = user["contributionsCollection"]["contributionCalendar"]["totalContributions"]

        lang_sizes = {}
        for repo in repos:
            for edge in repo["languages"]["edges"]:
                lang = edge["node"]["name"]
                lang_sizes[lang] = lang_sizes.get(lang, 0) + edge["size"]

        top_languages = sorted(lang_sizes.items(), key=lambda x: x[1], reverse=True)[:4]

        summary_rows = [
            ("User", user.get("name") or USERNAME),
            ("Public repositories", str(repo_count)),
            ("Total stars", str(stars)),
            ("Followers", str(followers)),
            ("Contributions (year)", str(contribs)),
        ]

        languages_rows = [(f"{idx + 1}. {lang}", f"{size:,} bytes") for idx, (lang, size) in enumerate(top_languages)]
    except Exception as err:  # noqa: BLE001
        error_message = str(err)
        summary_rows = [
            ("User", USERNAME),
            ("Public repositories", "n/a"),
            ("Total stars", "n/a"),
            ("Followers", "n/a"),
            ("Contributions (year)", "n/a"),
        ]
        languages_rows = [
            ("1. Data unavailable", "0 bytes"),
            ("2. Data unavailable", "0 bytes"),
            ("3. Data unavailable", "0 bytes"),
            ("4. Data unavailable", "0 bytes"),
        ]
    while len(languages_rows) < 4:
        languages_rows.append((f"{len(languages_rows) + 1}. -", "0 bytes"))

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    summary_rows.append(("Updated", generated_at))
    languages_rows.append(("Updated", generated_at))

    os.makedirs("assets", exist_ok=True)
    with open("assets/github-stats.svg", "w", encoding="utf-8") as file:
        file.write(render_card("GitHub Stats", summary_rows, height=200))

    with open("assets/github-languages.svg", "w", encoding="utf-8") as file:
        file.write(render_card("Top Languages by Size", languages_rows, height=200))

    if error_message:
        print(f"Generated fallback cards due to API error: {error_message}")

    print("Generated assets/github-stats.svg and assets/github-languages.svg")


if __name__ == "__main__":
    main()
