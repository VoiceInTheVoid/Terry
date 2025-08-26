#!/usr/bin/env python3

import time
import json
import re
from pathlib import Path

TOTAL_CHAPTERS = 31
API = "https://bible-api.com/proverbs+{chapter}?translation=kjv"
OUT_TXT = Path("proverbs.txt")
CACHE_JSON = Path("proverbs_kjv_full.json")

def fetch_with_backoff(url, max_retries=8, base_delay=1.5):
    """Simple exponential backoff for HTTP GET without external libs."""
    import urllib.request
    import urllib.error

    attempt = 0
    while True:
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                if resp.status != 200:
                    raise urllib.error.HTTPError(url, resp.status, "HTTP status not OK", resp.headers, None)
                data = resp.read()
                # Try to decode as utf-8
                return data.decode("utf-8")
        except urllib.error.HTTPError as e:
            # 429 or other status: backoff
            attempt += 1
            if attempt > max_retries:
                raise
            sleep_for = base_delay * (2 ** (attempt - 1))
            # Cap to a reasonable bound
            sleep_for = min(sleep_for, 30.0)
            print(f"[warn] HTTP {e.code} for {url}. Retry {attempt}/{max_retries} in {sleep_for:.1f}s ...")
            time.sleep(sleep_for)
        except urllib.error.URLError as e:
            attempt += 1
            if attempt > max_retries:
                raise
            sleep_for = base_delay * (2 ** (attempt - 1))
            sleep_for = min(sleep_for, 30.0)
            print(f"[warn] Network error ({e}). Retry {attempt}/{max_retries} in {sleep_for:.1f}s ...")
            time.sleep(sleep_for)

def load_all_proverbs():
    all_verses = []
    for ch in range(1, TOTAL_CHAPTERS + 1):
        url = API.format(chapter=ch)
        print(f"[info] Fetching {url}")
        text = fetch_with_backoff(url)
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # Some APIs return single quotes; try to repair
            text_fixed = re.sub(r"(?<!\\)'", '"', text)
            data = json.loads(text_fixed)
        verses = data.get("verses", [])
        if not verses:
            raise RuntimeError(f"No verses found for chapter {ch}")
        for v in verses:
            chap = v.get("chapter")
            num = v.get("verse")
            t = (v.get("text") or "").strip()
            t = re.sub(r"\s+", " ", t)
            all_verses.append({"chapter": chap, "verse": num, "text": t})
        # Be polite to the API
        time.sleep(0.8)
    return all_verses

def write_outputs(verses):
    # 1) JSON cache
    CACHE_JSON.write_text(json.dumps(verses, ensure_ascii=False, indent=2), encoding="utf-8")
    # 2) Plain text file, one verse per line: "Proverbs X:Y  Text"
    with OUT_TXT.open("w", encoding="utf-8") as f:
        for v in verses:
            f.write(f"Proverbs {v['chapter']}:{v['verse']}  {v['text']}\n")
    print(f"[ok] Wrote {len(verses)} verses to {OUT_TXT}")
    print(f"[ok] Cached JSON to {CACHE_JSON}")

def main():
    try:
        verses = load_all_proverbs()
        write_outputs(verses)
        print("[done] Complete Proverbs (KJV) saved locally. You can now use proverbs_local.py")
    except Exception as e:
        print("[error]", e)

if __name__ == "__main__":
    main()
