# -*- coding: utf-8 -*-
"""
Build ../index.html from template.html + data.py, inlining CSS and JS.

    python src/build.py          (python3 on macOS / Linux)

The output is a single self-contained file: no fonts, scripts or images are
loaded from anywhere else, so the page opens quickly behind any firewall.
"""
import html
import re
import sys
from collections import OrderedDict
from pathlib import Path

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent
sys.path.insert(0, str(SRC))

import data as D  # noqa: E402

AWARD_WORDS = ("最佳", "荣誉提名", "亚军")


def esc(s):
    return html.escape(str(s), quote=True)


def venue_badge(v):
    cls = "venue award" if any(w in v for w in AWARD_WORDS) else "venue"
    return f'<span class="{cls}">{esc(v)}</span>'


def ext_link(href, label):
    return f'<a href="{esc(href)}" target="_blank" rel="noopener">{esc(label)}</a>'


def url_label(url):
    if "blog" in url:
        return "官方博客"
    if url.endswith(".pdf") or "bitstream" in url:
        return "论文 PDF"
    if "KhronosGroup" in url:
        return "规范"
    return "项目页"


# ------------------------------------------------------------------ checks

def validate():
    problems = []
    seen = set()
    for d in D.DIRECTIONS:
        for w in d["works"]:
            key = (d["id"], w["name"])
            if key in seen:
                problems.append(f"duplicate work {key}")
            seen.add(key)
            if not re.fullmatch(r"\d{4}(\.\d{2})?", w["date"]):
                problems.append(f"bad date {w['name']}: {w['date']}")
            if w["arxiv"] and not re.fullmatch(r"\d{4}\.\d{4,5}", w["arxiv"]):
                problems.append(f"bad arxiv id {w['name']}: {w['arxiv']}")
            if not (w["arxiv"] or w["url"] or w["code"]):
                problems.append(f"no link for {w['name']}")
            if not w["group"]:
                problems.append(f"no group for {w['name']}")
            if w["arxiv"] and len(w["date"]) == 7:
                # the first arXiv version is at most a month before the id's month
                yy, mm = int(w["arxiv"][:2]), int(w["arxiv"][2:4])
                y, m = int(w["date"][2:4]), int(w["date"][5:7])
                gap = (yy * 12 + mm) - (y * 12 + m)
                if gap not in (0, 1):
                    problems.append(f"date {w['date']} does not match arXiv id {w['arxiv']} ({w['name']})")
    if problems:
        raise SystemExit("data.py problems:\n  " + "\n  ".join(problems))


# ---------------------------------------------------------------- fragments

def cells():
    groups = [(3, 1), (3, 2), (4, 3), (1, 4), (48, 5)]
    out = []
    for n, g in groups:
        for i in range(n):
            gap = " gap" if i == 0 and g > 1 else ""
            out.append(f'<i class="g{g}{gap}"></i>')
    return "".join(out)


def work_html(w, d):
    search = " ".join(filter(None, [
        w["name"], w["aka"], w["venue"], w["text"], w["group"], w["arxiv"], w["tag"], w["date"],
        d["name"], d["en"], "里程碑" if w["star"] else "",
    ]))
    links = []
    if w["arxiv"]:
        links.append(ext_link(f"https://arxiv.org/abs/{w['arxiv']}", f"arXiv:{w['arxiv']}"))
    if w["url"]:
        links.append(ext_link(w["url"], url_label(w["url"])))
    if w["code"]:
        links.append(ext_link(w["code"], "代码"))
    title = [f'<span class="name">{esc(w["name"])}</span>']
    if w["star"]:
        title.insert(0, '<span class="star-mark" title="里程碑">★</span>')
    title.append(venue_badge(w["venue"]))
    if w["tag"]:
        title.append(f'<span class="tag">{esc(w["tag"])}</span>')
    aka = f'<div class="aka">{esc(w["aka"])}</div>' if w["aka"] else ""
    star_cls = " star" if w["star"] else ""
    return (
        f'<li class="work{star_cls}" data-dir="{d["id"]}" data-star="{1 if w["star"] else 0}" data-search="{esc(search.lower())}">'
        f'<div class="date">{esc(w["date"])}</div>'
        f'<div><div class="title">{"".join(title)}</div>{aka}'
        f'<p class="text">{esc(w["text"])}</p>'
        f'<div class="links">{"".join(links)}</div></div></li>'
    )


def directions_html():
    parts = []
    for d in D.DIRECTIONS:
        groups = OrderedDict()
        for w in d["works"]:
            groups.setdefault(w["group"], []).append(w)
        for ws in groups.values():
            ws.sort(key=lambda w: w["date"] if len(w["date"]) == 7 else w["date"] + ".00")
        ideas = "".join(f'<li><b>{esc(t)}</b>{esc(x)}</li>' for t, x in d["ideas"])
        ideas_block = f'<div><h4 style="margin-bottom:8px">主流思路</h4><ul class="ideas">{ideas}</ul></div>' if d["ideas"] else ""
        body = [
            f'<article class="dir" id="dir-{d["id"]}" aria-labelledby="dir-{d["id"]}-h">',
            '<div class="dir-head">',
            f'<span class="no">{esc(d["no"])}</span>',
            f'<h3 id="dir-{d["id"]}-h">{esc(d["name"])}<small>{esc(d["en"])} · {len(d["works"])} 项</small></h3>',
            f'<p class="q">{esc(d["question"])}</p>',
            '</div>',
            '<div class="dir-body">',
            f'<p class="problem">{esc(d["problem"])}</p>',
            ideas_block,
            f'<div class="advice"><span class="label">工程建议</span>{esc(d["advice"])}</div>',
            '</div>',
        ]
        for g, ws in groups.items():
            body.append(f'<div class="group"><h4 class="group-title">{esc(g)}</h4><ol class="works">')
            body.extend(work_html(w, d) for w in ws)
            body.append('</ol></div>')
        body.append('</article>')
        parts.append("\n".join(body))
    return "\n".join(parts)


def chips_html():
    total = sum(len(d["works"]) for d in D.DIRECTIONS)
    out = [f'<button type="button" data-dir="all" aria-pressed="true">全部<span class="n">{total}</span></button>']
    for d in D.DIRECTIONS:
        out.append(f'<button type="button" data-dir="{d["id"]}" aria-pressed="false">{esc(d["name"])}<span class="n">{len(d["works"])}</span></button>')
    return "\n".join(out)


def dir_by_id():
    return {d["id"]: d for d in D.DIRECTIONS}


def timeline_html():
    dirs = dir_by_id()
    out = []
    for year, items in D.TIMELINE:
        lis = []
        for it in items:
            chip = ""
            if it["dir"] in dirs:
                chip = f' <a class="chip" href="#dir-{it["dir"]}">{esc(dirs[it["dir"]]["name"])}</a>'
            elif it["dir"] == "base":
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


def map_html():
    dirs = dir_by_id()

    def link(i):
        d = dirs[i]
        return f'<a class="dir-link" href="#dir-{i}">{esc(d["name"])} <small>{len(d["works"])}</small></a>'

    stages = [
        ("1", "拍摄与位姿", "照片或视频 → 相机位姿与稀疏点（COLMAP，或前馈模型）", [link("speed")]),
        ("2", "优化训练", "可微渲染 + 自适应增删，得到数百万个高斯", [link("speed")]),
        ("3", "压缩与传输", "减点、量化、熵编码、LoD，变成能下载的文件", [link("compress")]),
        ("4", "渲染与部署", "网页、引擎、XR 里实时显示，与网格共存", [link("geometry")]),
    ]
    flow = "".join(
        f'<div class="node"><span class="node-no">{no}</span><h4>{esc(t)}</h4><p>{esc(p)}</p><div class="chips">{"".join(ls)}</div></div>'
        for no, t, p, ls in stages
    )
    bars = [
        ("画质主线", "抗锯齿、去模糊、外观变化、稀疏视角：贯穿训练与渲染", link("quality")),
        ("几何主线", "表面、网格、光线追踪：让高斯能碰撞、能投影、能与网格混合", link("geometry")),
    ]
    bar_rows = "".join(
        f'<div class="span-row"><span class="span-note">贯穿第 2–4 步</span><div class="bar"><h4>{esc(t)}</h4><p>{esc(p)}</p>{l}</div></div>'
        for t, p, l in bars
    )
    ext = [
        ("编辑与交互", "选中物体、删除替换、文字编辑、物理仿真", link("edit")),
        ("重光照与材质", "拆出几何、材质和光照，换个光照也能看", link("relight")),
        ("动态与更多应用", "4D 场景、数字人、SLAM、自动驾驶、3D 生成", link("ext")),
    ]
    ext_nodes = "".join(
        f'<div class="node"><h4>{esc(t)}</h4><p>{esc(p)}</p><div class="chips">{l}</div></div>' for t, p, l in ext
    )
    return (
        '<div class="map">'
        '<span class="map-row-label">主流程</span>'
        f'<div class="flow">{flow}</div>'
        '<span class="map-row-label" style="margin-top:10px">两条支撑主线</span>'
        f'{bar_rows}'
        '<span class="map-row-label" style="margin-top:10px">可选扩展</span>'
        f'<div class="ext-row">{ext_nodes}</div>'
        '</div>'
    )


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
    validate()
    total = sum(len(d["works"]) for d in D.DIRECTIONS)
    stars = sum(1 for d in D.DIRECTIONS for w in d["works"] if w["star"])
    js = "\n".join((SRC / f).read_text(encoding="utf-8") for f in ("splat2d.js", "scenes.js", "app.js"))
    if "</script" in js.lower():
        raise SystemExit("inline JS must not contain </script")
    page = (SRC / "template.html").read_text(encoding="utf-8")
    fills = {
        "STYLE": (SRC / "style.css").read_text(encoding="utf-8"),
        "SCRIPT": js,
        "TIMELINE": timeline_html(),
        "MAP": map_html(),
        "CHIPS": chips_html(),
        "DIRECTIONS": directions_html(),
        "ECOSYSTEM": ecosystem_html(),
        "CAVEATS": caveats_html(),
        "GLOSSARY": glossary_html(),
        "ERRATA": errata_html(),
        "CELLS": cells(),
        "TOTAL": str(total),
        "STARS": str(stars),
        "UPDATED": D.UPDATED,
    }
    # STYLE and SCRIPT go last so their contents are never scanned for markers.
    for key in [k for k in fills if k not in ("STYLE", "SCRIPT")] + ["STYLE", "SCRIPT"]:
        marker = f"@@{key}@@"
        if marker not in page:
            raise SystemExit(f"template is missing {marker}")
        page = page.replace(marker, fills[key])
    leftover = re.findall(r"@@[A-Z]+@@", page)
    if leftover:
        raise SystemExit(f"unfilled markers: {leftover}")
    out = ROOT / "index.html"
    out.write_text(page, encoding="utf-8", newline="\n")
    per_dir = ", ".join(f"{d['name']} {len(d['works'])}" for d in D.DIRECTIONS)
    print(f"wrote {out.relative_to(ROOT)}: {len(page.encode('utf-8')) / 1024:.0f} KB, "
          f"{total} works ({stars} milestones) — {per_dir}")


if __name__ == "__main__":
    main()
