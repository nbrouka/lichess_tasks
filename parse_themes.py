#!/usr/bin/env python3
"""Parse Lichess puzzle themes page into structured JSON."""

import json
import re
from urllib.request import urlopen, Request

from constants import FETCH_TIMEOUT


URL = "https://lichess.org/training/themes"


def fetch_page(url: str) -> str:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=FETCH_TIMEOUT) as resp:
        return resp.read().decode("utf-8")


def clean(text: str) -> str:
    return re.sub(r'<[^>]+>', '', text).strip()


def parse_themes(html: str) -> dict:
    categories = []

    category_blocks = re.split(r'<h2[^>]+id="([^"]+)"[^>]*>(.*?)</h2>', html)
    i = 1
    while i < len(category_blocks) - 2:
        cat_id = category_blocks[i]
        cat_name = clean(category_blocks[i + 1]).split('More »')[0].strip()
        section_html = category_blocks[i + 2]

        themes = []

        theme_blocks = re.findall(
            r'<a[^>]+class="puzzle-(?:themes|openings)__link"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
            section_html,
            re.DOTALL,
        )
        for href, inner in theme_blocks:
            slug = href.rsplit('/', 1)[-1] if href.endswith('/') else href.rsplit('/', 1)[-1]
            if not slug or slug == 'training':
                if href == '/training':
                    slug = 'healthyMix'
                else:
                    slug_match = re.search(r'href="/training/([^"]+)"', inner)
                    if slug_match:
                        slug = slug_match.group(1)
                    else:
                        continue

            h3_match = re.search(r'<h3>(.*?)</h3>', inner, re.DOTALL)
            if not h3_match:
                continue
            h3_html = h3_match.group(1)

            count_match = re.search(r'<em[^>]*>(.*?)</em>', h3_html, re.DOTALL)
            count = clean(count_match.group(1)) if count_match else ""

            name_html = re.sub(r'<em[^>]*>.*?</em>', '', h3_html, flags=re.DOTALL)
            name = clean(name_html)

            desc_match = re.search(r'</h3>\s*<span>(.*?)</span>', inner, re.DOTALL)
            description = clean(desc_match.group(1)) if desc_match else ""

            themes.append({
                "id": slug,
                "name": name,
                "count": count,
                "description": description,
            })

        categories.append({
            "id": cat_id,
            "name": cat_name,
            "themes": themes,
        })
        i += 3

    return {"categories": [c for c in categories if c["id"] != "assets-missing"]}


def main() -> None:
    print("Fetching themes page...")
    html = fetch_page(URL)

    print("Parsing...")
    data = parse_themes(html)

    out_path = "lichess_themes.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Saved {out_path}")
    print(f"Categories: {len(data['categories'])}")
    for cat in data["categories"]:
        print(f"  {cat['name']}: {len(cat['themes'])} themes")


if __name__ == "__main__":
    main()
