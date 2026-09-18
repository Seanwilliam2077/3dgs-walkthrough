# -*- coding: utf-8 -*-
"""
Build the site from shell.html + home.html + refs.html + data.py + figures.json,
inlining CSS, JS and the icon sprite.

    python src/build.py          (python3 on macOS / Linux)

Output (all in the repo root, no assets besides the pages themselves):

    index.html      科普：总览关系图、直觉、原理小实验、时间线
    <module>.html   每个方向一页（recon / organize / compress / geometry / relight / dynamic / apps）
    refs.html       工程生态与许可、读数字的口径、术语表、参考与勘误

The only things a page loads from elsewhere are the display font and the paper
teaser images (from arXiv or the authors' sites); each card shows a drawn
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
# Short labels for the top bar (the full names are too long for a nav row).
SHORT = {"recon": "重建", "organize": "组织编辑", "compress": "压缩渲染", "geometry": "几何网格",
         "relight": "材质光照", "dynamic": "动态交互", "apps": "更多应用"}
HOME = "index.html"


def page_of(mod_id):
    return f"{mod_id}.html"


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


def count_of(m):
    return sum(1 for s in m["sections"] for _ in works_of(s))


def every_work():
    for m in ALL:
        for s in m["sections"]:
            for w in works_of(s):
                yield m, s, w


# ------------------------------------------------------------------ checks

def prepare():
    """Validate data.py, assign anchor ids, sort extras by date."""
    problems, used = [], set()
    SECTION_PAGE.update({s["id"]: page_of(m["id"]) for m in ALL for s in m["sections"]})
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
                w["_page"] = page_of(m["id"])
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
        f'<article class="card{" star" if w["star"] else ""}" id="{w["_id"]}" data-mod="{s["id"]}" '
        f'data-star="{1 if w["star"] else 0}" data-search="{esc(search)}">'
        f'<a class="thumb" href="{esc(primary)}" target="_blank" rel="noopener" tabindex="-1" aria-hidden="true"'
        f'{" title=" + chr(34) + esc(source) + chr(34) if source else ""}>'
        f'<span class="fallback"><svg class="fb-ic"><use href="#ic-{s["icon"]}"/></svg>'
        f'<span class="fb-name">{esc(w["name"])}</span><span class="fb-sec">{esc(s["name"])}</span></span>'
        f'{img_html}</a>'
        f'<div class="card-body">'
        f'<div class="card-meta"><span class="date">{esc(w["date"])}</span>{venue_badge(w["venue"])}{tag}</div>'
        f'<h3 class="card-title">{star}<a href="{esc(primary)}" target="_blank" rel="noopener">{esc(w["name"])}</a></h3>'
        f'{aka}<p class="text">{esc(w["text"])}</p>'
        f'<div class="links">{"".join(links)}</div>'
        f'</div></article>'
    )


def section_html(m, s, figs):
    n = sum(1 for _ in works_of(s))
    parts = [
        f'<section class="subsec" id="s-{s["id"]}" aria-labelledby="s-{s["id"]}-h">',
        f'<header class="sub-head"><svg class="sub-ic" aria-hidden="true"><use href="#ic-{s["icon"]}"/></svg>'
        f'<div><h2 id="s-{s["id"]}-h">{esc(s["name"])}</h2><p>{esc(s["tagline"])}</p></div>'
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


def chips_html(m):
    """Filter chips on a module page: one per sub-section."""
    out = [f'<button type="button" data-mod="all" aria-pressed="true">全部<span class="n">{count_of(m)}</span></button>']
    for s in m["sections"]:
        n = sum(1 for _ in works_of(s))
        out.append(f'<button type="button" data-mod="{s["id"]}" aria-pressed="false">{esc(s["name"])}'
                   f'<span class="n">{n}</span></button>')
    return "\n".join(out)


def rel_links(m):
    """「和其他方向的关系」 chips on a module page."""
    names = {x["id"]: x["name"] for x in ALL}
    out = []
    for a, b, label in D.RELATIONS:
        if a == m["id"]:
            out.append(f'<a class="chip" href="{page_of(b)}">→ {esc(names[b])}<span>（{esc(label)}）</span></a>')
        elif b == m["id"]:
            out.append(f'<a class="chip" href="{page_of(a)}">← {esc(names[a])}<span>（{esc(label)}）</span></a>')
    if not out:
        return ""
    return ('<p class="modrels"><span class="modrels-label">和其他方向的关系</span>' + "".join(out)
            + f'<a class="chip" href="{HOME}#overview">看总览图</a></p>')


# -------------------------------------------------------------------- pages

SECTION_PAGE = {}


def fix_links(body):
    """Rewrite the in-page anchors the home text still uses into cross-page links."""
    def sec(mt):
        sid = mt.group(1)
        if sid not in SECTION_PAGE:
            raise SystemExit(f"unknown section anchor #s-{sid}")
        return f'href="{SECTION_PAGE[sid]}#s-{sid}"'
    body = re.sub(r'href="#s-([a-z0-9-]+)"', sec, body)
    body = re.sub(r'href="#m-([a-z0-9-]+)"', lambda mt: f'href="{page_of(mt.group(1))}"', body)
    for name in ("ecosystem", "caveats", "glossary", "errata"):
        body = body.replace(f'href="#{name}"', f'href="refs.html#{name}"')
    return body


def nav_html(active):
    links = [(HOME, "首页")] + [(page_of(m["id"]), SHORT[m["id"]]) for m in ALL] + [("refs.html", "资料")]
    out = ['<nav class="toc" aria-label="站内导航">']
    for href, label in links:
        cur = ' aria-current="page"' if href == active else ""
        out.append(f'<a href="{href}"{cur}>{esc(label)}</a>')
    out.append("</nav>")
    return "\n".join(out)


def module_body(m, figs, prev, nxt):
    intro = ""
    if m.get("problem"):
        ideas = "".join(f'<li><b>{esc(t)}</b>{esc(x)}</li>' for t, x in m["ideas"])
        intro = (
            '<div class="mod-intro">'
            f'<p class="problem">{esc(m["problem"])}</p>'
            f'<div><h2 class="mini-h">主流思路</h2><ul class="ideas">{ideas}</ul></div>'
            f'<div class="advice"><span class="label">工程建议</span>{esc(m["advice"])}</div>'
            '</div>'
        )
    n = count_of(m)
    steps = []
    if prev:
        steps.append(f'<a class="pn prev" href="{page_of(prev["id"])}"><span>上一个方向</span><b>{esc(prev["name"])}</b></a>')
    steps.append(f'<a class="pn home" href="{HOME}#overview"><span>回到总览</span><b>六个方向的关系图</b></a>')
    if nxt:
        steps.append(f'<a class="pn next" href="{page_of(nxt["id"])}"><span>下一个方向</span><b>{esc(nxt["name"])}</b></a>')
    return (
        f'<section id="modules" class="modpage m-{m["color"]}">\n<div class="wrap">\n'
        f'<nav class="crumbs" aria-label="面包屑"><a href="{HOME}">首页</a><span aria-hidden="true">›</span>'
        f'<span>{esc(m["no"])} · {esc(m["name"])}</span></nav>\n'
        f'<article class="module solo m-{m["color"]}" id="m-{m["id"]}" data-mod="{m["id"]}" aria-labelledby="m-{m["id"]}-h">\n'
        f'<header class="mod-head solo"><span class="mod-no">{esc(m["no"])}</span>'
        f'<h1 id="m-{m["id"]}-h">{esc(m["name"])}<small>{esc(m["sub"])} · {n} 篇</small></h1>'
        f'<p class="q">{esc(m["question"])}</p></header>\n'
        f'{intro}\n{rel_links(m)}\n'
        '<div class="filters">\n<div class="filter-row">\n<div class="search">'
        '<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="7" cy="7" r="4.5" fill="none" stroke="currentColor" stroke-width="1.6"/>'
        '<path d="M10.5 10.5 L14 14" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>'
        f'<input id="q" type="search" placeholder="在「{esc(m["name"])}」里搜索名称、会议或关键词" aria-label="搜索本方向的论文" autocomplete="off">'
        '</div>\n<label class="switch"><input type="checkbox" id="only-star"> 只看里程碑 ★</label>\n'
        '<span class="count" id="count" aria-live="polite"></span>\n</div>\n'
        f'<div class="dir-chips" role="group" aria-label="按子方向筛选">\n{chips_html(m)}\n</div>\n</div>\n'
        + "\n".join(section_html(m, s, figs) for s in m["sections"])
        + '\n</article>\n<p class="empty" id="empty" hidden>没有匹配的论文。换个关键词，或关掉「只看里程碑」。</p>\n'
        + '<nav class="pagenav" aria-label="上下方向">' + "".join(steps) + "</nav>\n"
        + "</div>\n</section>\n"
    )


def hub_html():
    by_id = {m["id"]: m for m in D.MODULES}
    names = {m["id"]: m["name"] for m in ALL}
    mods = []
    for m in D.MODULES:
        page = page_of(m["id"])
        ids = {w["name"]: w["_id"] for s in m["sections"] for w in works_of(s)}
        secs = []
        for s in m["sections"]:
            if not s["hub"]:
                continue
            papers = "".join(f'<a href="{page}#{ids[h]}">{esc(h)}</a>' for h in s["hub"])
            secs.append(
                f'<div class="hub-sec"><a class="hub-sec-link" href="{page}#s-{s["id"]}">'
                f'<svg class="hub-ic" aria-hidden="true"><use href="#ic-{s["icon"]}"/></svg>'
                f'<span><b>{esc(s["name"])}</b><small>{esc(s["tagline"])}</small></span></a>'
                f'<p class="hub-papers">{papers}</p></div>'
            )
        extras = [s for s in m["sections"] if not s["hub"]]
        more = "".join(f'<a class="hub-more" href="{page}#s-{s["id"]}">延伸：{esc(s["name"])}</a>' for s in extras)
        rels = []
        for a, b, label in D.RELATIONS:
            if a == m["id"]:
                rels.append(f'<span>→ <a href="{page_of(b)}">{esc(names[b])}</a>（{esc(label)}）</span>')
            elif b == m["id"] and a in by_id:
                rels.append(f'<span>← <a href="{page_of(a)}">{esc(names[a])}</a>（{esc(label)}）</span>')
        mods.append(
            f'<div class="hub-mod m-{m["color"]}" style="grid-area:{AREA[m["id"]]}">'
            f'<a class="hub-title" href="{page}"><span class="hub-no">{D.MODULES.index(m) + 1}</span>'
            f'<span class="hub-name">{esc(m["name"])}</span><small>{esc(m["sub"])} · {count_of(m)} 篇</small></a>'
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


def dirlist_html():
    """The list of module pages at the foot of the home page."""
    out = []
    for m in ALL:
        page = page_of(m["id"])
        subs = "、".join(s["name"] for s in m["sections"])
        out.append(
            f'<a class="dircard m-{m["color"]}" href="{page}">'
            f'<span class="dc-no">{esc(m["no"])}</span>'
            f'<b class="dc-name">{esc(m["name"])}</b>'
            f'<span class="dc-sub">{esc(m["question"] if m.get("question") else m["sub"])}</span>'
            f'<span class="dc-secs">{esc(subs)}</span>'
            f'<span class="dc-n">{count_of(m)} 篇</span></a>'
        )
    return '<div class="dirlist">' + "".join(out) + "</div>"


def timeline_html():
    names = {m["id"]: m["name"] for m in ALL}
    out = []
    for year, items in D.TIMELINE:
        lis = []
        for it in items:
            if it["mod"] in names:
                chip = f' <a class="chip" href="{page_of(it["mod"])}">{esc(names[it["mod"]])}</a>'
            else:
                chip = ' <a class="chip" href="#pipeline">基础</a>'
            link = f' {ext_link("https://arxiv.org/abs/" + it["arxiv"], "arXiv")}' if it.get("arxiv") else ""
            star = " star" if it.get("star") else ""
            lis.append(
                f'<li class="tl-item{star}"><span class="tl-date">{esc(it["date"])}</span>'
                f'<div><h3>{esc(it["name"])}</h3><span class="venue">{esc(it["venue"])}</span>'
                f'<p>{esc(it["text"])}{link}{chip}</p></div></li>'
            )
        out.append(f'<div class="tl-year"><h2>{esc(year)}</h2><ol class="tl-list">{"".join(lis)}</ol></div>')
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
    return "\n".join(f'<div><h3>{esc(t)}</h3><p>{esc(x)}</p></div>' for t, x in D.CAVEATS)


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
    app = (SRC / "app.js").read_text(encoding="utf-8")
    # only the home page runs the canvas demos, so the other pages leave the trainer out
    js_home = "\n".join((SRC / f).read_text(encoding="utf-8") for f in ("splat2d.js", "scenes.js", "app.js"))
    if "</script" in js_home.lower():
        raise SystemExit("inline JS must not contain </script")
    shell = (SRC / "shell.html").read_text(encoding="utf-8")
    common = {
        "ICONS": (SRC / "icons.svg").read_text(encoding="utf-8"),
        "TOTAL": str(total),
        "CORE": str(core),
        "STARS": str(stars),
        "UPDATED": D.UPDATED,
        "HOME": HOME,
    }

    pages = []
    home = (SRC / "home.html").read_text(encoding="utf-8")
    pages.append(dict(
        file=HOME, active=HOME,
        title="3DGS 漫游指南", totop="#overview", totop_label="回到总览",
        desc=f"3D Gaussian Splatting 通俗导读：一张可点击的研究方向总览图，三个可以动手的原理小实验，"
             f"以及分成六个方向的 {total} 篇论文。",
        body=fix_links(home), extra={"HUB": hub_html(), "TIMELINE": timeline_html(), "CELLS": cells(), "DIRLIST": dirlist_html()},
    ))
    for i, m in enumerate(ALL):
        prev = ALL[i - 1] if i else None
        nxt = ALL[i + 1] if i + 1 < len(ALL) else None
        pages.append(dict(
            file=page_of(m["id"]), active=page_of(m["id"]),
            title=f'{m["name"]} · 3DGS 漫游指南', totop="#modules", totop_label="回到顶部",
            desc=f'3DGS {m["name"]}（{m["sub"]}）：{m.get("question") or ""}{count_of(m)} 篇论文与工具的配图卡片。',
            body=module_body(m, figs, prev, nxt), extra={},
        ))
    pages.append(dict(
        file="refs.html", active="refs.html",
        title="资料与勘误 · 3DGS 漫游指南", totop="#ecosystem", totop_label="回到顶部",
        desc="3DGS 工程生态与许可对照、论文数字的口径、术语表，以及参考来源与勘误。",
        body=(SRC / "refs.html").read_text(encoding="utf-8"),
        extra={"ECOSYSTEM": ecosystem_html(), "CAVEATS": caveats_html(),
               "GLOSSARY": glossary_html(), "ERRATA": errata_html()},
    ))

    written = []
    for p in pages:
        fills = dict(common, **p["extra"])
        fills.update({"TITLE": p["title"], "DESC": p["desc"], "NAV": nav_html(p["active"]),
                      "TOTOP": p["totop"], "TOTOP_LABEL": p["totop_label"]})
        body = p["body"]
        for key, value in fills.items():
            body = body.replace(f"@@{key}@@", value)
        page = shell.replace("@@BODY@@", body)
        for key, value in fills.items():
            page = page.replace(f"@@{key}@@", value)
        # STYLE and SCRIPT last: their text is never scanned for markers
        page = page.replace("@@STYLE@@", (SRC / "style.css").read_text(encoding="utf-8"))
        page = page.replace("@@SCRIPT@@", js_home if p["file"] == HOME else app)
        left = set(re.findall(r"@@[A-Z_]+@@", page))
        if left:
            raise SystemExit(f"{p['file']}: unfilled markers {sorted(left)}")
        out = ROOT / p["file"]
        out.write_text(page, encoding="utf-8", newline="\n")
        written.append((p["file"], len(page.encode("utf-8")) / 1024))

    print(f"wrote {len(written)} pages, {total} works ({core} representative, {stars} milestones), "
          f"{total - len(missing)} with teaser images")
    for name, kb in written:
        print(f"  {name:<16} {kb:6.0f} KB")
    if missing:
        print("  no image yet (drawn card is shown): " + ", ".join(missing))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
