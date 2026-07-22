#!/usr/bin/env python3

import json
import os
from pathlib import Path


COUNTER_FILE = Path("assets/profile-views.json")
BADGE_FILE = Path("assets/profile-views.svg")


def load_counter() -> int:
    if not COUNTER_FILE.exists():
        initial = int(os.environ.get("PROFILE_VIEWS_INITIAL", "0"))
        return max(initial, 0)

    data = json.loads(COUNTER_FILE.read_text(encoding="utf-8"))
    return max(int(data.get("count", 0)), 0)


def save_counter(count: int) -> None:
    COUNTER_FILE.write_text(json.dumps({"count": count}, indent=2) + "\n", encoding="utf-8")


def render_badge(count: int) -> str:
    return f"""<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"210\" height=\"20\" role=\"img\" aria-label=\"Profile views: {count}\">
  <title>Profile views: {count}</title>
  <linearGradient id=\"smooth\" x2=\"0\" y2=\"100%\">
    <stop offset=\"0\" stop-color=\"#fff\" stop-opacity=\".7\"/>
    <stop offset=\".1\" stop-color=\"#aaa\" stop-opacity=\".1\"/>
    <stop offset=\".9\" stop-color=\"#000\" stop-opacity=\".3\"/>
    <stop offset=\"1\" stop-color=\"#000\" stop-opacity=\".5\"/>
  </linearGradient>
  <clipPath id=\"round\">
    <rect width=\"210\" height=\"20\" rx=\"3\" fill=\"#fff\"/>
  </clipPath>
  <g clip-path=\"url(#round)\">
    <rect width=\"100\" height=\"20\" fill=\"#555\"/>
    <rect x=\"100\" width=\"110\" height=\"20\" fill=\"#0e75b6\"/>
    <rect width=\"210\" height=\"20\" fill=\"url(#smooth)\"/>
  </g>
  <g fill=\"#fff\" text-anchor=\"middle\" font-family=\"Verdana,Geneva,DejaVu Sans,sans-serif\" text-rendering=\"geometricPrecision\" font-size=\"11\">
    <text x=\"51\" y=\"15\" fill=\"#010101\" fill-opacity=\".3\">Profile views</text>
    <text x=\"51\" y=\"14\">Profile views</text>
    <text x=\"154\" y=\"15\" fill=\"#010101\" fill-opacity=\".3\">{count}</text>
    <text x=\"154\" y=\"14\">{count}</text>
  </g>
</svg>
"""


def main() -> None:
    count = load_counter() + 1
    save_counter(count)
    BADGE_FILE.write_text(render_badge(count), encoding="utf-8")
    print(f"Updated profile views badge: {count}")


if __name__ == "__main__":
    main()