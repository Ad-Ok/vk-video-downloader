#!/usr/bin/env python3
"""
VK Video Mass Downloader
========================
CLI tool for batch-downloading videos from vkvideo.ru / vk.com.
Uses yt-dlp under the hood.

Usage:
    python download.py URL [URL ...]
    python download.py -f urls.txt
    python download.py --help
"""

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yt_dlp
from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.table import Table

import config

console = Console()


# ---------------------------------------------------------------------------
# yt-dlp options builder
# ---------------------------------------------------------------------------

def build_ydl_opts(
    download_dir: Path | None = None,
    format_str: str | None = None,
    cookies_browser: str | None = None,
    cookies_file: Path | None = None,
    archive_file: Path | None = None,
    output_template: str | None = None,
    rate_limit: str | None = None,
    quality: str | None = None,
    no_archive: bool = False,
    quiet: bool = False,
) -> dict:
    """Build yt-dlp options dict from config + overrides."""
    dl_dir = download_dir or config.DOWNLOAD_DIR
    dl_dir.mkdir(parents=True, exist_ok=True)

    fmt = format_str or config.FORMAT
    if quality:
        quality_map = {
            "1080": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
            "720": "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
            "480": "bestvideo[height<=480]+bestaudio/best[height<=480]/best",
            "360": "bestvideo[height<=360]+bestaudio/best[height<=360]/best",
            "best": "bestvideo+bestaudio/best",
            "worst": "worstvideo+worstaudio/worst",
        }
        fmt = quality_map.get(quality, fmt)

    outtmpl = str(dl_dir / (output_template or config.OUTPUT_TEMPLATE))

    opts: dict = {
        "format": fmt,
        "outtmpl": outtmpl,
        "retries": config.RETRIES,
        "fragment_retries": config.FRAGMENT_RETRIES,
        "retry_sleep_functions": {"http": lambda n: config.RETRY_SLEEP},
        "ignoreerrors": True,
        "no_warnings": quiet,
        "quiet": quiet,
        "noprogress": True,  # we use our own progress bar
        "merge_output_format": "mp4",
        "postprocessors": [],
    }

    # --- Cookies ---
    cf = cookies_file or config.COOKIES_FILE
    cb = cookies_browser or config.COOKIES_BROWSER
    if cf and Path(cf).exists():
        opts["cookiefile"] = str(cf)
    elif cb:
        opts["cookiesfrombrowser"] = (cb,)

    # --- Rate limit ---
    rl = rate_limit or config.RATE_LIMIT
    if rl:
        opts["ratelimit"] = rl

    # --- Archive (skip already downloaded) ---
    if not no_archive:
        af = archive_file or config.ARCHIVE_FILE
        opts["download_archive"] = str(af)

    # --- Metadata / thumbnails ---
    if config.WRITE_THUMBNAIL:
        opts["writethumbnail"] = True
        opts["postprocessors"].append({
            "key": "EmbedThumbnail",
            "already_have_thumbnail": False,
        })
    if config.WRITE_DESCRIPTION:
        opts["writedescription"] = True
    if config.EMBED_METADATA:
        opts["postprocessors"].append({"key": "FFmpegMetadata"})

    return opts


# ---------------------------------------------------------------------------
# Single-URL download
# ---------------------------------------------------------------------------

class DownloadResult:
    """Result of downloading a single URL."""

    def __init__(self, url: str):
        self.url = url
        self.success = False
        self.title: str | None = None
        self.filename: str | None = None
        self.error: str | None = None
        self.entries: int = 0  # number of videos (>1 for playlists)


def download_url(url: str, ydl_opts: dict) -> DownloadResult:
    """Download a single URL (may be a video, playlist, or channel)."""
    result = DownloadResult(url)

    class InfoLogger:
        """Capture yt-dlp info messages."""
        def debug(self, msg):
            pass
        def info(self, msg):
            pass
        def warning(self, msg):
            pass
        def error(self, msg):
            result.error = msg

    opts = {**ydl_opts, "logger": InfoLogger()}

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            # Extract info first (no download) to get metadata
            info = ydl.extract_info(url, download=False)
            if info is None:
                result.error = "Could not extract video info"
                return result

            # Check if it's a playlist / channel
            if "entries" in info:
                entries = list(info["entries"])
                result.entries = len(entries)
                result.title = info.get("title", url)
            else:
                result.entries = 1
                result.title = info.get("title", url)

            # Now download
            ydl.download([url])
            result.success = True

    except yt_dlp.utils.DownloadError as e:
        result.error = str(e)
    except Exception as e:
        result.error = str(e)

    return result


# ---------------------------------------------------------------------------
# Batch orchestrator
# ---------------------------------------------------------------------------

def run_batch(urls: list[str], ydl_opts: dict, max_concurrent: int) -> list[DownloadResult]:
    """Download multiple URLs with concurrency and progress display."""
    results: list[DownloadResult] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        overall = progress.add_task("Overall", total=len(urls))

        if max_concurrent <= 1:
            for url in urls:
                progress.update(overall, description=f"Downloading ({urls.index(url)+1}/{len(urls)})")
                r = download_url(url, ydl_opts)
                results.append(r)
                progress.advance(overall)
                if r.success:
                    console.print(f"  [green]✓[/] {r.title} ({r.entries} video(s))")
                else:
                    console.print(f"  [red]✗[/] {url}: {r.error}")
        else:
            with ThreadPoolExecutor(max_workers=max_concurrent) as pool:
                futures = {pool.submit(download_url, u, ydl_opts): u for u in urls}
                for future in as_completed(futures):
                    r = future.result()
                    results.append(r)
                    progress.advance(overall)
                    if r.success:
                        console.print(f"  [green]✓[/] {r.title} ({r.entries} video(s))")
                    else:
                        console.print(f"  [red]✗[/] {r.url}: {r.error}")

    return results


# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------

def print_summary(results: list[DownloadResult]):
    """Print a summary table after all downloads."""
    table = Table(title="Download Summary", show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("Title / URL", max_width=60)
    table.add_column("Videos", justify="right")
    table.add_column("Status")

    ok = 0
    fail = 0
    for i, r in enumerate(results, 1):
        if r.success:
            ok += 1
            status = "[green]OK[/green]"
        else:
            fail += 1
            status = f"[red]FAIL[/red]: {r.error or 'unknown'}"
        table.add_row(
            str(i),
            r.title or r.url,
            str(r.entries),
            status,
        )

    console.print()
    console.print(table)
    console.print(f"\n[bold]Total:[/bold] {ok} succeeded, {fail} failed, {ok + fail} total")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="VK Video Mass Downloader — batch download from vkvideo.ru",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s https://vkvideo.ru/video4725344_14264835
  %(prog)s https://vkvideo.ru/@channel
  %(prog)s https://vkvideo.ru/playlist/-204353299_426
  %(prog)s -f urls.txt --quality 720
  %(prog)s -f urls.txt --cookies-browser firefox --concurrent 5
        """,
    )
    p.add_argument("urls", nargs="*", help="One or more VK video / channel / playlist URLs")
    p.add_argument("-f", "--file", type=Path, help="Text file with URLs (one per line)")
    p.add_argument("-o", "--output-dir", type=Path, help=f"Download directory (default: {config.DOWNLOAD_DIR})")
    p.add_argument("-q", "--quality", choices=["best", "1080", "720", "480", "360", "worst"],
                   default=None, help="Video quality (default: best available)")
    p.add_argument("-c", "--concurrent", type=int, default=config.MAX_CONCURRENT,
                   help=f"Max parallel downloads (default: {config.MAX_CONCURRENT})")
    p.add_argument("--cookies-browser", type=str, default=None,
                   help=f"Browser for cookie extraction (default: {config.COOKIES_BROWSER})")
    p.add_argument("--cookies-file", type=Path, default=None,
                   help="Path to cookies.txt in Netscape format")
    p.add_argument("--no-archive", action="store_true",
                   help="Don't track downloaded videos (re-download everything)")
    p.add_argument("--rate-limit", type=str, default=None,
                   help="Download speed limit, e.g. '5M' for 5 MB/s")
    p.add_argument("--list-formats", action="store_true",
                   help="List available formats for given URLs, don't download")
    p.add_argument("--dry-run", action="store_true",
                   help="Show what would be downloaded without downloading")
    return p.parse_args()


def collect_urls(args: argparse.Namespace) -> list[str]:
    """Collect URLs from CLI args and/or file."""
    urls = list(args.urls or [])

    if args.file:
        if not args.file.exists():
            console.print(f"[red]Error:[/red] File not found: {args.file}")
            sys.exit(1)
        with open(args.file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    urls.append(line)

    if not urls:
        console.print("[red]Error:[/red] No URLs provided. Use positional args or -f FILE.")
        sys.exit(1)

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique.append(u)

    return unique


def list_formats(urls: list[str], ydl_opts: dict):
    """List available formats for each URL."""
    opts = {**ydl_opts, "listformats": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        for url in urls:
            console.print(f"\n[bold]{url}[/bold]")
            try:
                ydl.download([url])
            except Exception:
                pass


def dry_run(urls: list[str], ydl_opts: dict):
    """Extract info without downloading."""
    opts = {**ydl_opts, "quiet": True, "no_warnings": True}
    table = Table(title="Dry Run — Videos to Download")
    table.add_column("#", style="dim", width=4)
    table.add_column("Title", max_width=50)
    table.add_column("Duration", justify="right")
    table.add_column("URL", max_width=50)

    idx = 0
    with yt_dlp.YoutubeDL(opts) as ydl:
        for url in urls:
            try:
                info = ydl.extract_info(url, download=False)
                if info is None:
                    continue
                if "entries" in info:
                    for entry in info["entries"]:
                        if entry is None:
                            continue
                        idx += 1
                        dur = entry.get("duration")
                        dur_str = f"{int(dur//60)}:{int(dur%60):02d}" if dur else "?"
                        table.add_row(str(idx), entry.get("title", "?"), dur_str, entry.get("webpage_url", url))
                else:
                    idx += 1
                    dur = info.get("duration")
                    dur_str = f"{int(dur//60)}:{int(dur%60):02d}" if dur else "?"
                    table.add_row(str(idx), info.get("title", "?"), dur_str, info.get("webpage_url", url))
            except Exception as e:
                idx += 1
                table.add_row(str(idx), f"[red]ERROR[/red]", "-", f"{url} ({e})")

    console.print(table)
    console.print(f"\n[bold]Total:[/bold] {idx} video(s) found")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = parse_args()
    urls = collect_urls(args)

    console.print(f"[bold]VK Video Downloader[/bold]")
    console.print(f"  URLs: {len(urls)}")
    console.print(f"  Output: {args.output_dir or config.DOWNLOAD_DIR}")
    console.print()

    ydl_opts = build_ydl_opts(
        download_dir=args.output_dir,
        cookies_browser=args.cookies_browser,
        cookies_file=args.cookies_file,
        quality=args.quality,
        rate_limit=args.rate_limit,
        no_archive=args.no_archive,
    )

    if args.list_formats:
        list_formats(urls, ydl_opts)
        return

    if args.dry_run:
        dry_run(urls, ydl_opts)
        return

    t0 = time.time()
    results = run_batch(urls, ydl_opts, max_concurrent=args.concurrent)
    elapsed = time.time() - t0

    print_summary(results)
    console.print(f"[dim]Completed in {elapsed:.1f}s[/dim]")


if __name__ == "__main__":
    main()
