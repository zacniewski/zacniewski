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
            f'<text x="24" y="{y}" font-size="18" fill="#374151">{escape_xml(label)}</text>'
            f'<text x="{width - 24}" y="{y}" font-size="14" text-anchor="end" fill="#111827">{escape_xml(value)}</text>'
        )

    return f"""<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"{width}\" height=\"{height}\" viewBox=\"0 0 {width} {height}\" role=\"img\" aria-label=\"{escape_xml(title)}\">
  <defs>
    <linearGradient id=\"bg\" x1=\"0\" y1=\"0\" x2=\"1\" y2=\"1\">
      <stop offset=\"0%\" stop-color=\"#ffffff\"/>
      <stop offset=\"100%\" stop-color=\"#f3f4f6\"/>
    </linearGradient>
  </defs>
  <rect width=\"100%\" height=\"100%\" rx=\"14\" fill=\"url(#bg)\" stroke=\"#d1d5db\"/>
  <text x=\"24\" y=\"38\" font-size=\"18\" font-weight=\"700\" fill=\"#1f2937\">{escape_xml(title)}</text>
  {''.join(row_svg)}
</svg>
"""


def calculate_streaks(contribution_days: list[dict]) -> tuple[int, int, str]:
    today = datetime.now(timezone.utc).date()
    parsed_days = []

    for day in contribution_days:
        day_date = datetime.strptime(day["date"], "%Y-%m-%d").date()
        if day_date <= today:
            parsed_days.append((day_date, day["contributionCount"]))

    if not parsed_days:
        return 0, 0, "n/a"

    parsed_days.sort(key=lambda item: item[0])

    longest_streak = 0
    running = 0
    last_contribution_date = "n/a"
    for day_date, count in parsed_days:
        if count > 0:
            running += 1
            longest_streak = max(longest_streak, running)
            last_contribution_date = day_date.isoformat()
        else:
            running = 0

    current_streak = 0
    index = len(parsed_days) - 1
    if parsed_days[index][0] == today and parsed_days[index][1] == 0:
        index -= 1

    while index >= 0 and parsed_days[index][1] > 0:
        current_streak += 1
        index -= 1

    return current_streak, longest_streak, last_contribution_date


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
            weeks {
              contributionDays {
                date
                contributionCount
              }
            }
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
        contribution_calendar = user["contributionsCollection"]["contributionCalendar"]
        contribs = contribution_calendar["totalContributions"]

        contribution_days = []
        for week in contribution_calendar["weeks"]:
            contribution_days.extend(week["contributionDays"])

        current_streak, longest_streak, last_contribution_date = calculate_streaks(contribution_days)

        lang_repo_counts = {}
        for repo in repos:
            repo_languages = set()
            for edge in repo["languages"]["edges"]:
                lang = edge["node"]["name"]
                repo_languages.add(lang)
            for lang in repo_languages:
                lang_repo_counts[lang] = lang_repo_counts.get(lang, 0) + 1

        top_languages = sorted(lang_repo_counts.items(), key=lambda x: x[1], reverse=True)[:4]

        summary_rows = [
            ("User", user.get("name") or USERNAME),
            ("Public repositories", str(repo_count)),
            ("Total stars", str(stars)),
            ("Followers", str(followers)),
            ("Contributions (year)", str(contribs)),
        ]

        languages_rows = [(f"{idx + 1}. {lang}", f"{count} repos") for idx, (lang, count) in enumerate(top_languages)]
        streak_rows = [
            ("Current streak", f"{current_streak} days"),
            ("Longest streak", f"{longest_streak} days"),
            ("Contributions (year)", str(contribs)),
            ("Last contribution", last_contribution_date),
        ]
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
            ("1. Data unavailable", "0 repos"),
            ("2. Data unavailable", "0 repos"),
            ("3. Data unavailable", "0 repos"),
            ("4. Data unavailable", "0 repos"),
        ]
        streak_rows = [
            ("Current streak", "n/a"),
            ("Longest streak", "n/a"),
            ("Contributions (year)", "n/a"),
            ("Last contribution", "n/a"),
        ]
    while len(languages_rows) < 4:
        languages_rows.append((f"{len(languages_rows) + 1}. -", "0 repos"))

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    summary_rows.append(("Updated", generated_at))
    languages_rows.append(("Updated", generated_at))
    streak_rows.append(("Updated", generated_at))

    os.makedirs("assets", exist_ok=True)
    with open("assets/github-stats.svg", "w", encoding="utf-8") as file:
        file.write(render_card("GitHub Stats", summary_rows, height=200))

    with open("assets/github-languages.svg", "w", encoding="utf-8") as file:
        file.write(render_card("Top Languages by Repos", languages_rows, height=200))

    with open("assets/github-streak.svg", "w", encoding="utf-8") as file:
        file.write(render_card("GitHub Streak", streak_rows, height=200))

    if error_message:
        print(f"Generated fallback cards due to API error: {error_message}")

    print("Generated assets/github-stats.svg, assets/github-languages.svg and assets/github-streak.svg")


if __name__ == "__main__":
    main()
