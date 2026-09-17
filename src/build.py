# -*- coding: utf-8 -*-
"""
Build ../index.html from template.html + data.py + figures.json, inlining CSS,
JS and the icon sprite.

    python src/build.py          (python3 on macOS / Linux)

The output is a single file. The only things it loads from elsewhere are the
paper teaser images (from arXiv or the authors' sites); each card shows a drawn
placeholder until its image arrives, and keeps it if the image never does.
"""
import html
import json
import re
import sys
import urllib.parse
from pathlib import Path

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent
sys.path.insert(0, str(SRC))

import data as D  # noqa: E402

AWARD_WORDS = ("最佳", "荣誉提名", "亚军")
ALL = D.MODULES + [D.APPS]
# Where each module and relation sits on the overview grid (see style.css .hub).
AREA = {"recon": "a", "organize": "b", "compress": "c", "geometry": "d", "relight": "e", "dynamic": "f"}
REL_AREA = {("recon", "organize"): ("r1", "h"), ("organize", "compress"): ("r2", "h"),
            ("recon", "geometry"): ("r3", "down"), ("geometry", "organize"): ("r4", "diag"),
            ("organize", "relight"): ("r5", "both"), ("geometry", "relight"): ("r6", "h"),
            ("dynamic", "compress"): ("r7", "up")}


def esc(s):
    return html.escape(str(s), quote=True)


def thumb_url(src):
    """720 px WebP served by the images.weserv.nl cache (keeps cards light; originals are often several MB)."""
    return "https://images.weserv.nl/?url=" + urllib.parse.quote(src, safe="") + "&w=720&output=webp&q=70"


def ext_link(href, label, cls=None):
    c = f' class="{cls}"' if cls else ""
    return f'<a{c} href="{esc(href)}" target="_blank" rel="noopener">{esc(label)}</a>'


def url_label(url):
    if "blog" in url:
        return "官方博客"
    if url.endswith(".pdf") or "bitstream" in url:
        return "论文 PDF"
    if "KhronosGroup" in url:
        return "规范"
    return "项目页"


def works_of(section):
    for _, ws in section["groups"]:
        yield from ws
    yield from section["extra"]


def every_work():
    for m in ALL:
        for s in m["sections"]:
            for w in works_of(s):
                yield m, s, w


# ------------------------------------------------------------------ checks

def prepare():
    """Validate data.py, assign anchor ids, sort extras by date."""
    problems, used = [], set()
    for m in ALL:
        names = set()
        for s in m["sections"]:
            s["extra"].sort(key=lambda w: w["date"] if len(w["date"]) == 7 else w["date"] + ".00")
            for w in works_of(s):
                if w["name"] in names:
                    problems.append(f"duplicate work {w['name']} in {m['id']}")
                names.add(w["name"])
                if not re.fullmatch(r"\d{4}(\.\d{2})?", w["date"]):
                    problems.append(f"bad date {w['name']}: {w['date']}")
                if w["arxiv"] and not re.fullmatch(r"\d{4}\.\d{4,5}", w["arxiv"]):
                    problems.append(f"bad arxiv id {w['name']}: {w['arxiv']}")
                if not (w["arxiv"] or w["url"] or w["code"]):
                    problems.append(f"no link for {w['name']}")
                if w["arxiv"] and len(w["date"]) == 7:
                    # the id's month is the announcement month; v1 can be up to two months earlier
                    yy, mm = int(w["arxiv"][:2]), int(w["arxiv"][2:4])
                    y, mo = int(w["date"][2:4]), int(w["date"][5:7])
                    if (yy * 12 + mm) - (y * 12 + mo) not in (0, 1, 2):
                        problems.append(f"date {w['date']} does not match arXiv id {w['arxiv']} ({w['name']})")
                slug = re.sub(r"[^a-z0-9]+", "-", w["name"].lower()).strip("-") or "work"
                cand, i = slug, 2
                while cand in used:
                    cand, i = f"{slug}-{i}", i + 1
                used.add(cand)
                w["_id"] = "p-" + cand
            for h in s["hub"]:
                if h not in {w["name"] for w in works_of(s)}:
                    problems.append(f"hub name {h!r} is not a work in section {s['id']}")
    if problems:
        raise SystemExit("data.py problems:\n  " + "\n  ".join(problems))


def figures():
    p = SRC / "figures.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


# ---------------------------------------------------------------- fragments

def cells():
    groups = [(3, 1), (3, 2), (4, 3), (1, 4), (48, 5)]
    out = []
    for n, g in groups:
        for i in range(n):
            gap = " gap" if i == 0 and g > 1 else ""
            out.append(f'<i class="g{g}{gap}"></i>')
    return "".join(out)


def venue_badge(v):
    cls = "venue award" if any(k in v for k in AWARD_WORDS) else "venue"
    return f'<span class="{cls}">{esc(v)}</span>'


def card(m, s, w, figs):
    primary = f"https://arxiv.org/abs/{w['arxiv']}" if w["arxiv"] else (w["url"] or w["code"])
    fig = figs.get(w["arxiv"] or w["name"]) or {}
    img = w["img"] or fig.get("src")
    search = " ".join(filter(None, [
        w["name"], w["aka"], w["venue"], w["text"], w["arxiv"], w["tag"], w["date"],
        s["name"], m["name"], "里程碑" if w["star"] else "",
    ])).lower()
    links = []
    if w["arxiv"]:
        links.append(ext_link(primary, f"arXiv:{w['arxiv']}"))
    if w["url"]:
        links.append(ext_link(w["url"], url_label(w["url"])))
    if w["code"]:
        links.append(ext_link(w["code"], "代码"))
    tag = f'<span class="tag">{esc(w["tag"])}</span>' if w["tag"] else ""
    aka = f'<p class="aka">{esc(w["aka"])}</p>' if w["aka"] else ""
    star = '<span class="star-mark" title="里程碑">★</span>' if w["star"] else ""
    img_html = (f'<img src="{esc(thumb_url(img))}" data-orig="{esc(img)}" alt="" loading="lazy" decoding="async" '
                f'referrerpolicy="no-referrer">' if img else "")
    source = {"arxiv-html": "图：arXiv 论文", "ar5iv": "图：ar5iv 论文", "og": "图：项目页"}.get(fig.get("from"), "")
    if w["img"]:
        source = "图：项目页"
    return (
        f'<article class="card{" star" if w["star"] else ""}" id="{w["_id"]}" data-mod="{m["id"]}" '
        f'data-star="{1 if w["star"] else 0}" data-search="{esc(search)}">'
        f'<a class="thumb" href="{esc(primary)}" target="_blank" rel="noopener" tabindex="-1" aria-hidden="true"'
        f'{" title=" + chr(34) + esc(source) + chr(34) if source else ""}>'
        f'<span class="fallback"><svg class="fb-ic"><use href="#ic-{s["icon"]}"/></svg>'
        f'<span class="fb-name">{esc(w["name"])}</span><span class="fb-sec">{esc(s["name"])}</span></span>'
        f'{img_html}</a>'
        f'<div class="card-body">'
        f'<div class="card-meta"><span class="date">{esc(w["date"])}</span>{venue_badge(w["venue"])}{tag}</div>'
        f'<h5 class="card-title">{star}<a href="{esc(primary)}" target="_blank" rel="noopener">{esc(w["name"])}</a></h5>'
        f'{aka}<p class="text">{esc(w["text"])}</p>'
        f'<div class="links">{"".join(links)}</div>'
        f'</div></article>'
    )


def section_html(m, s, figs):
    n = sum(1 for _ in works_of(s))
    parts = [
        f'<section class="subsec" id="s-{s["id"]}" aria-labelledby="s-{s["id"]}-h">',
        f'<header class="sub-head"><svg class="sub-ic" aria-hidden="true"><use href="#ic-{s["icon"]}"/></svg>'
        f'<div><h4 id="s-{s["id"]}-h">{esc(s["name"])}</h4><p>{esc(s["tagline"])}</p></div>'
        f'<span class="sub-count">{n} 篇</span></header>',
    ]
    if s["note"]:
        parts.append(f'<p class="sub-note">{esc(s["note"])}</p>')
    for heading, ws in s["groups"]:
        if heading:
            parts.append(f'<p class="group-title">{esc(heading)}</p>')
        parts.append('<div class="cards">' + "".join(card(m, s, w, figs) for w in ws) + "</div>")
    if s["extra"]:
        label = "延伸阅读" if s["groups"] else "论文列表"
        parts.append(
            f'<details class="more"><summary><span>{label}</span><span class="more-n">{len(s["extra"])} 篇</span>'
            f'<span class="more-hint">点开查看</span></summary>'
            '<div class="cards">' + "".join(card(m, s, w, figs) for w in s["extra"]) + "</div></details>"
        )
    parts.append("</section>")
    return "\n".join(parts)


def modules_html(figs):
    out = []
    for m in ALL:
        intro = ""
        if m.get("problem"):
            ideas = "".join(f'<li><b>{esc(t)}</b>{esc(x)}</li>' for t, x in m["ideas"])
            intro = (
                '<div class="mod-intro">'
                f'<p class="problem">{esc(m["problem"])}</p>'
                f'<div><h4 class="mini-h">主流思路</h4><ul class="ideas">{ideas}</ul></div>'
                f'<div class="advice"><span class="label">工程建议</span>{esc(m["advice"])}</div>'
                '</div>'
            )
        n = sum(1 for s in m["sections"] for _ in works_of(s))
        out.append(
            f'<article class="module m-{m["color"]}" id="m-{m["id"]}" data-mod="{m["id"]}" aria-labelledby="m-{m["id"]}-h">'
            f'<header class="mod-head"><span class="mod-no">{esc(m["no"])}</span>'
            f'<h3 id="m-{m["id"]}-h">{esc(m["name"])}<small>{esc(m["sub"])} · {n} 篇</small></h3>'
            f'<p class="q">{esc(m["question"])}</p>'
            f'<a class="mod-back" href="#overview">回到总览</a></header>'
            f'{intro}'
            + "\n".join(section_html(m, s, figs) for s in m["sections"])
            + "</article>"
        )
    return "\n".join(out)


def chips_html():
    total = sum(1 for _ in every_work())
    out = [f'<button type="button" data-mod="all" aria-pressed="true">全部<span class="n">{total}</span></button>']
    for m in ALL:
        n = sum(1 for s in m["sections"] for _ in works_of(s))
        out.append(f'<button type="button" data-mod="{m["id"]}" aria-pressed="false">{esc(m["name"])}<span class="n">{n}</span></button>')
    return "\n".join(out)


def hub_html():
    by_id = {m["id"]: m for m in D.MODULES}
    names = {m["id"]: m["name"] for m in ALL}
    mods = []
    for m in D.MODULES:
        ids = {w["name"]: w["_id"] for s in m["sections"] for w in works_of(s)}
        secs = []
        for s in m["sections"]:
            if not s["hub"]:
                continue
            papers = "".join(f'<a href="#{ids[h]}">{esc(h)}</a>' for h in s["hub"])
            secs.append(
                f'<div class="hub-sec"><a class="hub-sec-link" href="#s-{s["id"]}">'
                f'<svg class="hub-ic" aria-hidden="true"><use href="#ic-{s["icon"]}"/></svg>'
                f'<span><b>{esc(s["name"])}</b><small>{esc(s["tagline"])}</small></span></a>'
                f'<p class="hub-papers">{papers}</p></div>'
            )
        extras = [s for s in m["sections"] if not s["hub"]]
        more = "".join(f'<a class="hub-more" href="#s-{s["id"]}">延伸：{esc(s["name"])}</a>' for s in extras)
        rels = []
        for a, b, label in D.RELATIONS:
            if a == m["id"]:
                rels.append(f'<span>→ <a href="#m-{b}">{esc(names[b])}</a>（{esc(label)}）</span>')
            elif b == m["id"] and a in by_id:
                rels.append(f'<span>← <a href="#m-{a}">{esc(names[a])}</a>（{esc(label)}）</span>')
        n = sum(1 for s in m["sections"] for _ in works_of(s))
        mods.append(
            f'<div class="hub-mod m-{m["color"]}" style="grid-area:{AREA[m["id"]]}">'
            f'<a class="hub-title" href="#m-{m["id"]}"><span class="hub-no">{D.MODULES.index(m) + 1}</span>'
            f'<span class="hub-name">{esc(m["name"])}</span><small>{esc(m["sub"])} · {n} 篇</small></a>'
            + "".join(secs) + more
            + f'<p class="hub-rels">{"".join(rels)}</p></div>'
        )
    rel_cells = []
    for a, b, label in D.RELATIONS:
        area, kind = REL_AREA[(a, b)]
        ca, cb = by_id[a]["color"], by_id[b]["color"]
        if kind == "diag":
            arrow = ('<svg class="rel-diag" viewBox="0 0 76 56" aria-hidden="true"><path d="M8 50 L66 8" '
                     'stroke-dasharray="5 4"/><path d="M56 8 H66 V18" /></svg>')
        else:
            arrow = '<span class="rel-line"></span>'
        rel_cells.append(
            f'<div class="rel rel-{kind}" style="grid-area:{area};--from:var(--c-{ca});--to:var(--c-{cb})" '
            f'title="{esc(names[a])} → {esc(names[b])}">{arrow}<span class="rel-label">{esc(label)}</span></div>'
        )
    return '<div class="hub" role="navigation" aria-label="研究方向总览">' + "".join(mods) + "".join(rel_cells) + "</div>"


def timeline_html():
    names = {m["id"]: m["name"] for m in ALL}
    out = []
    for year, items in D.TIMELINE:
        lis = []
        for it in items:
            if it["mod"] in names:
                chip = f' <a class="chip" href="#m-{it["mod"]}">{esc(names[it["mod"]])}</a>'
            else:
                chip = ' <a class="chip" href="#pipeline">基础</a>'
            link = f' {ext_link("https://arxiv.org/abs/" + it["arxiv"], "arXiv")}' if it.get("arxiv") else ""
            star = " star" if it.get("star") else ""
            lis.append(
                f'<li class="tl-item{star}"><span class="tl-date">{esc(it["date"])}</span>'
                f'<div><h4>{esc(it["name"])}</h4><span class="venue">{esc(it["venue"])}</span>'
                f'<p>{esc(it["text"])}{link}{chip}</p></div></li>'
            )
        out.append(f'<div class="tl-year"><h3>{esc(year)}</h3><ol class="tl-list">{"".join(lis)}</ol></div>')
    return "\n".join(out)


def ecosystem_html():
    rows = []
    for use, name, url, what, lic, level in D.ECOSYSTEM:
        pill = "可商用" if level == "ok" else "注意"
        if lic == "Khronos 规范":
            pill = "开放标准"
        rows.append(
            f'<tr><td>{esc(use)}</td><td>{ext_link(url, name)}</td><td>{esc(what)}</td>'
            f'<td><span class="lic {level}"><span class="pill">{pill}</span><span>{esc(lic)}</span></span></td></tr>'
        )
    return "\n".join(rows)


def caveats_html():
    return "\n".join(f'<div><h4>{esc(t)}</h4><p>{esc(x)}</p></div>' for t, x in D.CAVEATS)


def glossary_html():
    return "\n".join(
        f'<div><dt>{esc(zh)}<span>{esc(en)}</span></dt><dd>{esc(x)}</dd></div>' for zh, en, x in D.GLOSSARY
    )


def errata_html():
    return "\n".join(
        f'<li><b>{esc(t)}</b><p>{esc(x)} {ext_link(url, "来源")}</p></li>' for t, x, url in D.ERRATA
    )


# -------------------------------------------------------------------- main

def main():
    prepare()
    figs = figures()
    works = list(every_work())
    total = len(works)
    core = sum(1 for m in ALL for s in m["sections"] for _, ws in s["groups"] for _ in ws)
    stars = sum(1 for _, _, w in works if w["star"])
    missing = [w["name"] for _, _, w in works if not (w["img"] or (figs.get(w["arxiv"] or w["name"]) or {}).get("src"))]
    js = "\n".join((SRC / f).read_text(encoding="utf-8") for f in ("splat2d.js", "scenes.js", "app.js"))
    if "</script" in js.lower():
        raise SystemExit("inline JS must not contain </script")
    page = (SRC / "template.html").read_text(encoding="utf-8")
    fills = {
        "ICONS": (SRC / "icons.svg").read_text(encoding="utf-8"),
        "HUB": hub_html(),
        "MODULES": modules_html(figs),
        "CHIPS": chips_html(),
        "TIMELINE": timeline_html(),
        "ECOSYSTEM": ecosystem_html(),
        "CAVEATS": caveats_html(),
        "GLOSSARY": glossary_html(),
        "ERRATA": errata_html(),
        "CELLS": cells(),
        "TOTAL": str(total),
        "CORE": str(core),
        "STARS": str(stars),
        "UPDATED": D.UPDATED,
        "STYLE": (SRC / "style.css").read_text(encoding="utf-8"),
        "SCRIPT": js,
    }
    for key, value in fills.items():   # STYLE and SCRIPT last: their text is never scanned for markers
        marker = f"@@{key}@@"
        if marker not in page:
            raise SystemExit(f"template is missing {marker}")
        page = page.replace(marker, value)
    out = ROOT / "index.html"
    out.write_text(page, encoding="utf-8", newline="\n")
    print(f"wrote {out.relative_to(ROOT)}: {len(page.encode('utf-8')) / 1024:.0f} KB, "
          f"{total} works ({core} representative, {stars} milestones), {total - len(missing)} with teaser images")
    if missing:
        print("  no image yet (drawn card is shown): " + ", ".join(missing))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
