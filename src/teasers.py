# -*- coding: utf-8 -*-
"""
Find a teaser image for every work and store its URL in src/figures.json.

    python src/teasers.py            # only works that are not in figures.json yet
    python src/teasers.py --all      # look everything up again
    python src/teasers.py --warm     # fetch every thumbnail once so the image cache is filled

Images are not downloaded or copied into this repository: the page loads them
from arXiv or the authors' own sites, and falls back to a drawn card when that
fails. Order of preference:
  1. Figure 1 of the arXiv HTML version (usually the paper's teaser),
  2. the same figure from ar5iv for papers without an arXiv HTML version,
  3. the og:image of the project page / repository.
Entries with "pin": true are hand-picked and never overwritten.
"""
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

SRC = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC))
import data as D  # noqa: E402

OUT = SRC / "figures.json"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36",
      "Accept": "text/html,application/xhtml+xml"}
DELAY = 2.0


def all_works():
    for m in D.MODULES + [D.APPS]:
        for s in m["sections"]:
            for _, ws in s["groups"]:
                yield from ws
            yield from s["extra"]


def key_of(w):
    return w["arxiv"] or w["name"]


def get(url):
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40)
        return r.geturl(), r.read().decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return None, None


def first_figure(page_url, page):
    """Return (image urls, caption) of the first figure that contains images."""
    best = None
    for cls, body in re.findall(r'<figure[^>]*class="([^"]*)"[^>]*>(.*?)</figure>', page, re.S):
        if "ltx_table" in cls:
            continue
        imgs = re.findall(r'<img[^>]*\ssrc="([^"]+)"', body)
        if not imgs:
            continue
        cap = re.search(r"<figcaption[^>]*>(.*?)</figcaption>", body, re.S)
        caption = " ".join(html.unescape(re.sub(r"<.*?>", " ", cap.group(1))).split())[:160] if cap else ""
        urls = [urllib.parse.urljoin(page_url, u) for u in imgs]
        cand = (urls, caption)
        if "teaser" in cls or re.match(r"(Figure|Fig\.)\s*1\b", caption):
            return cand
        if best is None:
            best = cand
    return best


def og_image(url):
    final, page = get(url)
    if not page:
        return None
    m = (re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', page)
         or re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image', page)
         or re.search(r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)', page))
    if not m:
        return None
    src = urllib.parse.urljoin(final, html.unescape(m.group(1)))
    if "ar5iv_card" in src or "arxiv-logo" in src:
        return None
    return src


def lookup(w):
    if w["arxiv"]:
        for base, kind in ((f"https://arxiv.org/html/{w['arxiv']}", "arxiv-html"),
                           (f"https://ar5iv.labs.arxiv.org/html/{w['arxiv']}", "ar5iv")):
            final, page = get(base)
            time.sleep(DELAY)
            if not page or "No HTML for" in page or "HTML is not available" in page:
                continue
            fig = first_figure(final, page)
            if fig:
                urls, caption = fig
                return {"src": urls[0], "from": kind, "n": len(urls), "caption": caption}
    for url in filter(None, (w["url"], w["code"])):
        src = og_image(url)
        time.sleep(1)
        if src:
            return {"src": src, "from": "og", "n": 1, "caption": ""}
    return None


def warm(figs):
    from build import thumb_url
    urls = sorted({v["src"] for v in figs.values() if v.get("src")})
    bad = []
    for i, src in enumerate(urls, 1):
        try:
            r = urllib.request.urlopen(urllib.request.Request(thumb_url(src), headers=UA), timeout=90)
            size = len(r.read())
            print(f"[{i}/{len(urls)}] {size // 1024} KB  {src}")
        except Exception as e:  # noqa: BLE001
            bad.append(src)
            print(f"[{i}/{len(urls)}] FAILED {e}  {src}")
        time.sleep(1.2)
    print(f"warmed {len(urls) - len(bad)}/{len(urls)}")


def main():
    if "--warm" in sys.argv:
        warm(json.loads(OUT.read_text(encoding="utf-8")))
        return
    redo = "--all" in sys.argv
    figs = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    works = list(all_works())
    todo = [w for w in works if redo and not figs.get(key_of(w), {}).get("pin") or key_of(w) not in figs]
    print(f"{len(works)} works, looking up {len(todo)}")
    for i, w in enumerate(todo, 1):
        found = lookup(w)
        figs[key_of(w)] = found or {"src": None}
        print(f"[{i}/{len(todo)}] {w['name']}: {found['from'] + ' x' + str(found['n']) if found else 'none'}")
        OUT.write_text(json.dumps(dict(sorted(figs.items())), ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
