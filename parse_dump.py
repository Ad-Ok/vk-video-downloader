#!/usr/bin/env python3
"""
Extract unique VK Video URLs from a saved HTML page.

Usage:
    python parse_dump.py dump.html                  # print to stdout
    python parse_dump.py dump.html -o urls.txt      # save to file
    python parse_dump.py dump.html --owner 4725344  # only videos from this owner
"""

import argparse
import re
import sys
from pathlib import Path

# Matches: https://vkvideo.ru/video{owner_id}_{video_id}
# owner_id can be negative (group) or positive (user)
VIDEO_RE = re.compile(r'https://vkvideo\.ru/video-?\d+_\d+')


def extract_urls(html: str, owner_filter: str | None = None) -> list[str]:
    """Extract unique video URLs from HTML, preserving first-seen order."""
    urls = VIDEO_RE.findall(html)

    # Deduplicate, preserving order
    seen = set()
    unique = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            if owner_filter:
                # video{owner}_{id} — extract owner part
                match = re.search(r'/video(-?\d+)_', url)
                if match and match.group(1) != owner_filter:
                    continue
            unique.append(url)

    return unique


def main():
    p = argparse.ArgumentParser(description="Extract VK Video URLs from HTML dump")
    p.add_argument("html", type=Path, help="Path to HTML file")
    p.add_argument("-o", "--output", type=Path, help="Output file (default: stdout)")
    p.add_argument("--owner", type=str, help="Filter by owner ID (e.g. 4725344 or -1719791)")
    p.add_argument("--count", action="store_true", help="Only print the count")
    args = p.parse_args()

    if not args.html.exists():
        print(f"Error: {args.html} not found", file=sys.stderr)
        sys.exit(1)

    html = args.html.read_text(encoding="utf-8", errors="ignore")
    urls = extract_urls(html, owner_filter=args.owner)

    if args.count:
        print(len(urls))
        return

    text = "\n".join(urls) + "\n"

    if args.output:
        args.output.write_text(text, encoding="utf-8")
        print(f"Saved {len(urls)} URLs to {args.output}", file=sys.stderr)
    else:
        print(text, end="")
        print(f"\n# Total: {len(urls)} unique videos", file=sys.stderr)


if __name__ == "__main__":
    main()
