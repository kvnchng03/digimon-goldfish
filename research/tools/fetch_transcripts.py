"""Fetch YouTube transcripts for the research notes, or convert downloaded VTT subtitles.

    python3 research/tools/fetch_transcripts.py fetch VIDEO_ID ... [--out research/transcripts/tx] [--meta]
    python3 research/tools/fetch_transcripts.py vtt FILE.vtt ...

`fetch` needs `pip install youtube-transcript-api`; `--meta` also saves title, channel,
date and chapters via `yt-dlp` (must be on PATH). Already-fetched videos are skipped.
Output: `<out>/<id>.txt`, one `[mm:ss] text` line per caption, after a `# lang=...` header.
`vtt` writes `<name>.txt` next to each VTT, deduplicating YouTube's rolling captions and
stamping `[m:ss]` about every 30 seconds.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENGLISH = ["en", "en-US", "en-GB"]


def save_meta(vid: str, out: Path) -> str | None:
    proc = subprocess.run(["yt-dlp", "--skip-download", "-J", f"https://www.youtube.com/watch?v={vid}"],
                          capture_output=True, text=True)
    try:
        j = json.loads(proc.stdout)
        info = {k: j.get(k) for k in ("title", "channel", "upload_date", "duration", "description", "chapters")}
    except json.JSONDecodeError:
        info = {"err": proc.stderr[-300:]}
    (out / f"{vid}.meta.json").write_text(json.dumps(info, indent=1))
    return info.get("title")


def fetch(vids: list[str], out: Path, meta: bool) -> int:
    from youtube_transcript_api import YouTubeTranscriptApi

    api = YouTubeTranscriptApi()
    out.mkdir(parents=True, exist_ok=True)
    failures = 0
    for vid in vids:
        title = save_meta(vid, out) if meta else None
        target = out / f"{vid}.txt"
        if target.exists():
            print(vid, "cached")
            continue
        try:
            tl = api.list(vid)
            langs = [(t.language_code, t.is_generated) for t in tl]
            try:
                t = tl.find_transcript(ENGLISH)
            except Exception:  # any failure: fall back to the first language offered
                t = next(iter(tl))
            data = t.fetch()
            lines = [f"# lang={t.language_code} gen={t.is_generated} avail={langs}"]
            lines += [f"[{int(s.start) // 60:02d}:{int(s.start) % 60:02d}] {s.text}" for s in data]
            target.write_text("\n".join(lines) + "\n")
            print(vid, "OK", t.language_code, len(data), title or "", flush=True)
        except Exception as e:  # report and keep going; YouTube throttles often
            failures += 1
            print(vid, "FAIL", type(e).__name__, str(e)[:150].replace("\n", " "), flush=True)
    return 1 if failures else 0


def vtt_to_text(path: Path) -> str:
    out, last, stamp, last_stamp = [], "", None, -999
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"(\d+):(\d+):(\d+)\.\d+ -->", line)
        if m:
            stamp = int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3])
            continue
        if not line.strip() or line.startswith(("WEBVTT", "Kind:", "Language:")) or "-->" in line:
            continue
        text = re.sub(r"<[^>]+>", "", line).strip()
        if not text or text == last:
            continue
        last = text
        if stamp is not None and stamp - last_stamp >= 30:
            out.append(f"\n[{stamp // 60}:{stamp % 60:02d}] ")
            last_stamp = stamp
        out.append(text + " ")
    return "".join(out)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help="fetch transcripts by video ID")
    f.add_argument("vids", nargs="+")
    f.add_argument("--out", type=Path, default=ROOT / "research" / "transcripts" / "tx")
    f.add_argument("--meta", action="store_true", help="also save yt-dlp metadata (title, chapters)")
    v = sub.add_parser("vtt", help="convert VTT subtitle files to stamped text")
    v.add_argument("files", nargs="+", type=Path)
    args = ap.parse_args(argv)
    if args.cmd == "fetch":
        return fetch(args.vids, args.out, args.meta)
    for path in args.files:
        text = vtt_to_text(path)
        target = path.with_name(path.name.split(".")[0] + ".txt")
        target.write_text(text)
        print(path, "->", target, len(text))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
