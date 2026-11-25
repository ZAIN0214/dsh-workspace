#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识库构建脚本
==============

把仓库里的 Markdown 笔记渲染成静态站点，输出到 ../wiki/。

用法：
    python3 wiki-src/build.py

加一篇新笔记：
    1. 在仓库里写好 .md 文件
    2. 打开本文件，在 NOTES 列表里加一行
    3. 重新跑一次 build.py，然后 git push

依赖：mistune（pip install --user mistune）
"""

import html
import json
import os
import re
import shutil
import sys
from datetime import datetime

try:
    import markdown as md_lib
except ImportError:
    sys.exit("缺少依赖：python3 -m pip install --user markdown")

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

SRC_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_ROOT = os.path.join(SRC_ROOT, "wiki")
# 脱敏后的 Markdown 副本：公开仓库只提交这份，原始笔记留在本地
NOTES_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notes")

SITE_TITLE = "我的知识库"
SITE_DESC = "学习方法、篮球战术、考研政治、英语口播——平时积累的干货，整理成一份能查的笔记。"

# 分类：(id, 显示名, 一句话说明)
CATEGORIES = [
    ("learning", "学习方法", "怎么用 AI、怎么学得更快"),
    ("basketball", "篮球战术", "挡拆、跑位、读防守"),
    ("exam", "考研政治", "史纲重点与高频考点"),
    ("english", "英语口播", "一天一句 · 运动系英语的稿子与拍法"),
]

# 笔记清单：(源文件相对路径, 分类 id, URL 名, 标题, 一句话摘要, 标签)
NOTES = [
    (
        "高效指挥AI助手.md",
        "learning",
        "ai-command",
        "怎么高效地指挥 AI",
        "一个高效请求的 5 个要素：目标、背景、约束、交付形式、验收标准。",
        ["AI", "提示词", "效率"],
    ),
    (
        "bilibili-notes/01-用AI高效学习.md",
        "learning",
        "ai-learning",
        "用 AI 高效学习",
        "先自己产出再让 AI 挑错；动脑的让它纠正，不动脑的让它干。",
        ["AI", "学习法", "费曼技巧"],
    ),
    (
        "bilibili-notes/03-我该怎么干活.md",
        "learning",
        "ai-agent",
        "AI 智能体该怎么干活",
        "提示工程、上下文工程、Agent 工作流的要点，以及给自己定的 3 条底线。",
        ["AI", "Agent", "工作流"],
    ),
    (
        "bilibili-notes/02-挡拆.md",
        "basketball",
        "pick-and-roll",
        "挡拆：从「挡」到「拆」到「读防」",
        "挡拆不是两个人做动作，而是用两个人的动作逼第三、第四个防守人做选择。",
        ["篮球", "战术", "挡拆"],
    ),
    (
        "中国近现代史纲要-重点与高频考点.md",
        "exam",
        "modern-history",
        "中国近现代史纲要 · 重点与高频考点",
        "按 2023 版教材整理，标了【必背】【高频】【了解】三级，附常见问法。",
        ["考研", "史纲", "政治"],
    ),
    (
        "口播-今晚就拍.md",
        "english",
        "oral-shoot-tonight",
        "今晚就拍第一条",
        "15 分钟流程：读 5 遍、架好手机、拍 3 遍、剪三件事、发出去。",
        ["口播", "英语", "实操"],
    ),
    (
        "不露脸-第一条怎么拍.md",
        "english",
        "no-face-video",
        "不露脸 + 校园空镜怎么拍",
        "你拍空镜、你读音频，剪辑配字我出；可持续比好看重要。",
        ["口播", "英语", "拍摄"],
    ),
    (
        "发布文案-01.md",
        "english",
        "publish-copy-01",
        "01 发布文案（复制粘贴用）",
        "标题三选一、正文、置顶评论、标签，直接抄。",
        ["口播", "文案", "抖音"],
    ),
    (
        "稿件-02-第三天就没劲.md",
        "english",
        "script-02-long",
        "02 稿件 · 第三天就没劲（30 秒原版）",
        "10 句 / 59 词 / 约 30 秒。留着做对照，别直接用。",
        ["口播", "稿件", "英语"],
    ),
    (
        "稿件-02-13秒版.md",
        "english",
        "script-02-13s",
        "02 稿件 · 13 秒版",
        "按 01 的完播数据重做的结构，不是删减版。5 句 / 21 词。",
        ["口播", "稿件", "英语"],
    ),
]

def scrub(text):
    """去掉本地绝对路径和个人标识，避免公开页面泄漏本机信息。"""
    # 把 /Users/xxx/.../default-workspace/素材/01/ 之类的路径压成相对写法
    text = re.sub(r"/Users/[^/\s]+/[^\s`'\")]*?(?=素材|成片|工具|audio|shots)/", "", text)
    text = re.sub(r"/Users/[^/\s]+", "~", text)
    for k, v in REDACT.items():
        text = text.replace(k, v)
    return text


# 隐私替换：源文件里出现这些词，构建时会换掉（不公开个人身份信息）
REDACT = {
    "武体大一": "体育专业大一",
    "武体": "体育院校",
    "武术专业": "体育专业",
    "武术与民族传统体育": "体育专业",
    "武术训练科学": "专项训练科学",
    "武术基本功": "专项基本功",
}

# 需要复制进站点的本地图片：(源路径, 站点内文件名)
ASSETS = [
    ("成片/01-封面.png", "cover-01.png"),
]

# ---------------------------------------------------------------------------
# Markdown 渲染
# ---------------------------------------------------------------------------

_md_ext = [
    "tables",
    "fenced_code",
    "sane_lists",
    "attr_list",
]


def slugify(text):
    """给标题生成锚点 id。"""
    text = re.sub(r"<[^>]+>", "", text)
    text = text.strip().lower()
    text = re.sub(r"[^\w\u4e00-\u9fff]+", "-", text)
    return text.strip("-") or "section"


def rewrite_links(md_text, note_url_map):
    """把源文件里的本地链接改成站点内链接；指向不存在资源的降级成纯文本。"""

    def fix(target):
        target = target.strip()
        if target.startswith(("http://", "https://", "mailto:", "#")):
            return target, None
        base = os.path.basename(target)
        if base in note_url_map:
            return "../" + note_url_map[base], None
        for src, out_name in ASSETS:
            if target == src or base == os.path.basename(src):
                return "../assets/" + out_name, None
        # 其他本地文件（视频等）不发布
        return None, os.path.splitext(base)[0]

    def repl_bracket(m):
        label, target = m.group(1), m.group(2)
        new, plain = fix(target)
        if new:
            return "[%s](%s)" % (label, new)
        return "%s（本地文件，未发布）" % (plain or label)

    def repl_angle(m):
        label, target = m.group(1), m.group(2)
        new, plain = fix(target)
        if new:
            return "[%s](%s)" % (label, new)
        return "%s（本地文件，未发布）" % (plain or label)

    md_text = re.sub(r"\[([^\]]*)\]\(<([^>]*)>\)", repl_angle, md_text)
    md_text = re.sub(r"\[([^\]]*)\]\(([^)\s]*)\)", repl_bracket, md_text)
    return md_text


def render(md_text, note_url_map):
    md_text = rewrite_links(md_text, note_url_map)
    body = md_lib.markdown(md_text, extensions=_md_ext)

    # 给 h2/h3 加 id，并收集目录
    toc = []
    counter = {}

    def add_id(m):
        level, attrs, inner = m.group(1), m.group(2), m.group(3)
        text = re.sub(r"<[^>]+>", "", inner).strip()
        base = slugify(text)
        n = counter.get(base, 0)
        counter[base] = n + 1
        hid = base if n == 0 else "%s-%d" % (base, n)
        if level in ("2", "3"):
            toc.append((level, hid, text))
        return '<h%s id="%s"%s>%s</h%s>' % (level, hid, attrs, inner, level)

    body = re.sub(r"<h([1-6])([^>]*)>(.*?)</h\1>", add_id, body, flags=re.S)

    # 外链新窗口打开
    body = re.sub(
        r'<a href="(https?://[^"]+)"',
        r'<a href="\1" target="_blank" rel="noopener"',
        body,
    )
    return body, toc


# ---------------------------------------------------------------------------
# 模板
# ---------------------------------------------------------------------------

def esc(s):
    return html.escape(s, quote=True)


def sidebar_html(notes_meta, current_url=None, rel=""):
    parts = ['<nav class="sidebar-nav">']
    for cid, cname, cdesc in CATEGORIES:
        items = [n for n in notes_meta if n["cat"] == cid]
        if not items:
            continue
        parts.append('<div class="nav-group">')
        parts.append('<div class="nav-group-title">%s</div>' % esc(cname))
        parts.append("<ul>")
        for n in items:
            cls = ' class="active"' if n["url"] == current_url else ""
            parts.append(
                '<li><a href="%s%s"%s>%s</a></li>' % (rel, n["url"], cls, esc(n["title"]))
            )
        parts.append("</ul></div>")
    parts.append("</nav>")
    return "".join(parts)


PAGE_TMPL = """<!doctype html>
<html lang="zh-CN" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{pagetitle}</title>
<meta name="description" content="{desc}">
<link rel="stylesheet" href="{rel}assets/style.css">
</head>
<body>
<header class="topbar">
  <button class="icon-btn" id="menuBtn" aria-label="目录">☰</button>
  <a class="brand" href="{rel}index.html">{site}</a>
  <span class="spacer"></span>
  <a class="icon-btn" href="{rel}index.html#search" aria-label="搜索">🔍</a>
  <button class="icon-btn" id="themeBtn" aria-label="切换主题">🌙</button>
</header>
<div class="layout">
  <aside class="sidebar" id="sidebar">{sidebar}</aside>
  <main class="main">
    <nav class="crumbs">{crumbs}</nav>
    <article class="markdown">{body}</article>
    <nav class="pager">{pager}</nav>
    <footer class="foot">
      <a href="{rel}index.html">← 回到知识库首页</a>
      <span class="dot">·</span>
      <span>更新于 {date}</span>
    </footer>
  </main>
  {toc_aside}
</div>
<script src="{rel}assets/app.js"></script>
</body>
</html>
"""


def page_toc_html(toc):
    if not toc:
        return ""
    parts = ['<aside class="page-toc"><div class="toc-title">本页目录</div><ul>']
    for level, hid, text in toc:
        parts.append(
            '<li class="lv%s"><a href="#%s">%s</a></li>' % (level, hid, esc(text))
        )
    parts.append("</ul></aside>")
    return "".join(parts)


# ---------------------------------------------------------------------------
# 构建
# ---------------------------------------------------------------------------

def build():
    note_url_map = {os.path.basename(n[0]): "%s/%s.html" % (n[1], n[2]) for n in NOTES}

    def source_path(rel, slug):
        """优先用仓库根目录的原稿；没有就用 wiki-src/notes/ 里的脱敏副本。"""
        p = os.path.join(SRC_ROOT, rel)
        if os.path.isfile(p):
            return p
        p2 = os.path.join(NOTES_OUT, slug + ".md")
        if os.path.isfile(p2):
            return p2
        return None

    missing = [n[0] for n in NOTES if source_path(n[0], n[2]) is None]
    if missing:
        sys.exit("这些笔记文件找不到：\n  " + "\n  ".join(missing))

    if os.path.isdir(OUT_ROOT):
        shutil.rmtree(OUT_ROOT)
    os.makedirs(os.path.join(OUT_ROOT, "assets"), exist_ok=True)

    # 复制资源
    for src, out_name in ASSETS:
        p = os.path.join(SRC_ROOT, src)
        if os.path.isfile(p):
            shutil.copy2(p, os.path.join(OUT_ROOT, "assets", out_name))
        else:
            print("  ! 资源缺失，跳过：%s" % src)

    notes_meta = []
    for path, cid, slug, title, desc, tags in NOTES:
        full = source_path(path, slug)
        with open(full, encoding="utf-8") as f:
            raw = f.read()

        raw = scrub(raw)
        body, toc = render(raw, note_url_map)
        mtime = datetime.fromtimestamp(os.path.getmtime(full)).strftime("%Y-%m-%d")
        url = "%s/%s.html" % (cid, slug)

        notes_meta.append(
            {
                "url": url,
                "slug": slug,
                "title": title,
                "desc": desc,
                "cat": cid,
                "tags": tags,
                "date": mtime,
                "file": path,
            }
        )

    # 渲染每篇
    for i, meta in enumerate(notes_meta):
        full = source_path(meta["file"], meta["slug"])
        with open(full, encoding="utf-8") as f:
            raw = f.read()
        raw = scrub(raw)
        body, toc = render(raw, note_url_map)

        cat_name = next(c[1] for c in CATEGORIES if c[0] == meta["cat"])
        crumbs = '<a href="../index.html">首页</a> <span class="sep">/</span> <span>%s</span> <span class="sep">/</span> <span class="cur">%s</span>' % (
            esc(cat_name),
            esc(meta["title"]),
        )

        pager = ""
        if i > 0:
            p = notes_meta[i - 1]
            pager += '<a class="prev" href="../%s"><span>← 上一篇</span>%s</a>' % (
                p["url"],
                esc(p["title"]),
            )
        if i < len(notes_meta) - 1:
            n = notes_meta[i + 1]
            pager += '<a class="next" href="../%s"><span>下一篇 →</span>%s</a>' % (
                n["url"],
                esc(n["title"]),
            )

        out = PAGE_TMPL.format(
            pagetitle=esc(meta["title"]) + " · " + esc(SITE_TITLE),
            title=esc(meta["title"]),
            site=esc(SITE_TITLE),
            desc=esc(meta["desc"]),
            rel="../",
            sidebar=sidebar_html(notes_meta, meta["url"], rel="../"),
            crumbs=crumbs,
            body=body,
            pager=pager,
            date=meta["date"],
            toc_aside=page_toc_html(toc),
        )
        dest = os.path.join(OUT_ROOT, meta["cat"], meta["slug"] + ".html")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            f.write(out)

    # 首页
    cards = []
    for cid, cname, cdesc in CATEGORIES:
        items = [n for n in notes_meta if n["cat"] == cid]
        if not items:
            continue
        lis = "".join(
            '<li><a href="%s"><b>%s</b><span>%s</span></a></li>'
            % (n["url"], esc(n["title"]), esc(n["desc"]))
            for n in items
        )
        cards.append(
            '<section class="cat-card"><h2>%s</h2><p class="cat-desc">%s</p>'
            '<ul class="note-list">%s</ul></section>'
            % (esc(cname), esc(cdesc), lis)
        )

    total = len(notes_meta)
    index_body = """
<div class="hero">
  <h1>{site}</h1>
  <p class="lead">{desc}</p>
  <p class="meta">{total} 篇笔记 · {ncats} 个分类</p>
</div>

<div class="search-box">
  <input id="searchInput" type="search" placeholder="搜索笔记标题、摘要、标签…" autocomplete="off">
  <div id="searchResults" class="search-results"></div>
</div>

<div class="cards">{cards}</div>
""".format(
        site=esc(SITE_TITLE),
        desc=esc(SITE_DESC),
        total=total,
        ncats=len([c for c in CATEGORIES if any(n["cat"] == c[0] for n in notes_meta)]),
        cards="".join(cards),
    )

    index_html = PAGE_TMPL.format(
        pagetitle=esc(SITE_TITLE) + " · 平时积累的干货笔记",
        title=esc(SITE_TITLE),
        site=esc(SITE_TITLE),
        desc=esc(SITE_DESC),
        rel="",
        sidebar=sidebar_html(notes_meta, rel=""),
        crumbs="",
        body=index_body,
        pager="",
        date=datetime.now().strftime("%Y-%m-%d"),
        toc_aside="",
    )
    with open(os.path.join(OUT_ROOT, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    # 搜索索引
    search_data = [
        {
            "t": n["title"],
            "u": n["url"],
            "d": n["desc"],
            "c": next(c[1] for c in CATEGORIES if c[0] == n["cat"]),
            "k": n["tags"],
        }
        for n in notes_meta
    ]
    with open(os.path.join(OUT_ROOT, "assets", "search-index.json"), "w", encoding="utf-8") as f:
        json.dump(search_data, f, ensure_ascii=False, separators=(",", ":"))

    # 脱敏 Markdown 副本（公开仓库提交这份，原稿不进仓库）
    os.makedirs(NOTES_OUT, exist_ok=True)
    for path, cid, slug, title, desc, tags in NOTES:
        src = source_path(path, slug)
        with open(src, encoding="utf-8") as f:
            text = scrub(f.read())
        with open(os.path.join(NOTES_OUT, slug + ".md"), "w", encoding="utf-8") as f:
            f.write(text)

    # 静态资源
    write_assets()

    print("构建完成：%s" % OUT_ROOT)
    print("  %d 篇笔记，%d 个分类" % (total, len(CATEGORIES)))
    print("  脱敏副本：wiki-src/notes/（公开仓库提交这份）")
    print("  本地预览：python3 -m http.server 8080 -d wiki")


def write_assets():
    css = r"""
:root{
  --bg:#fbfaf7; --fg:#1c1b19; --muted:#6b6862; --line:#e6e2da;
  --card:#ffffff; --accent:#c2410c; --accent-soft:#fef3ec;
  --code-bg:#f4f1ea; --side:#f6f3ed;
}
html[data-theme="dark"]{
  --bg:#16171a; --fg:#e8e6e1; --muted:#9a968e; --line:#2c2e33;
  --card:#1d1f23; --accent:#fb923c; --accent-soft:#2a2118;
  --code-bg:#212429; --side:#1a1c20;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{
  margin:0; background:var(--bg); color:var(--fg);
  font:16px/1.75 -apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}

/* 顶栏 */
.topbar{
  position:sticky;top:0;z-index:50;display:flex;align-items:center;gap:10px;
  height:56px;padding:0 16px;background:color-mix(in srgb,var(--bg) 88%,transparent);
  backdrop-filter:blur(12px);border-bottom:1px solid var(--line);
}
.brand{font-weight:700;font-size:15px;color:var(--fg);letter-spacing:.02em}
.brand:hover{text-decoration:none;color:var(--accent)}
.spacer{flex:1}
.icon-btn{
  display:inline-flex;align-items:center;justify-content:center;
  width:34px;height:34px;border-radius:8px;border:1px solid transparent;
  background:transparent;color:var(--fg);font-size:16px;cursor:pointer;line-height:1;
}
.icon-btn:hover{background:var(--side);text-decoration:none}
#menuBtn{display:none}

/* 布局 */
.layout{display:grid;grid-template-columns:250px minmax(0,1fr) 200px;gap:0;align-items:start}
.sidebar{
  position:sticky;top:56px;max-height:calc(100vh - 56px);overflow-y:auto;
  padding:22px 12px 40px 16px;border-right:1px solid var(--line);
}
.main{min-width:0;padding:28px 40px 80px;max-width:860px;margin:0 auto}
.page-toc{
  position:sticky;top:56px;max-height:calc(100vh - 56px);overflow-y:auto;
  padding:22px 16px 40px 0;font-size:13px;
}

/* 侧栏 */
.nav-group{margin-bottom:18px}
.nav-group-title{
  font-size:11px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;
  color:var(--muted);margin:0 0 6px 10px;
}
.sidebar-nav ul{list-style:none;margin:0;padding:0}
.sidebar-nav li{margin:1px 0}
.sidebar-nav a{
  display:block;padding:5px 10px;border-radius:7px;color:var(--fg);
  font-size:14px;line-height:1.45;opacity:.82;
}
.sidebar-nav a:hover{background:var(--side);opacity:1;text-decoration:none}
.sidebar-nav a.active{background:var(--accent-soft);color:var(--accent);font-weight:600;opacity:1}

/* 目录 */
.toc-title{font-size:11px;font-weight:700;letter-spacing:.12em;color:var(--muted);margin-bottom:8px}
.page-toc ul{list-style:none;margin:0;padding:0}
.page-toc li{margin:2px 0;line-height:1.5}
.page-toc a{color:var(--muted);font-size:13px}
.page-toc a:hover{color:var(--accent);text-decoration:none}
.page-toc .lv3{padding-left:12px}

/* 面包屑 */
.crumbs{font-size:13px;color:var(--muted);margin-bottom:18px}
.crumbs a{color:var(--muted)}
.crumbs a:hover{color:var(--accent)}
.crumbs .sep{margin:0 6px;opacity:.5}
.crumbs .cur{color:var(--fg)}

/* 正文排版 */
.markdown{font-size:16.5px}
.markdown h1{font-size:1.9em;line-height:1.3;margin:.2em 0 .8em;letter-spacing:-.01em}
.markdown h2{
  font-size:1.32em;margin:2em 0 .7em;padding-bottom:.35em;
  border-bottom:1px solid var(--line);letter-spacing:-.005em;
}
.markdown h3{font-size:1.12em;margin:1.6em 0 .5em}
.markdown h4{font-size:1em;margin:1.3em 0 .4em;color:var(--muted)}
.markdown p{margin:0 0 1em}
.markdown ul,.markdown ol{margin:0 0 1em;padding-left:1.5em}
.markdown li{margin:.28em 0}
.markdown li>ul,.markdown li>ol{margin:.28em 0}
.markdown blockquote{
  margin:1.2em 0;padding:.7em 1em;border-left:3px solid var(--accent);
  background:var(--accent-soft);border-radius:0 8px 8px 0;color:var(--fg);
}
.markdown blockquote p:last-child{margin-bottom:0}
.markdown code{
  background:var(--code-bg);padding:.15em .4em;border-radius:5px;
  font:.88em/1.5 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
}
.markdown pre{
  background:var(--code-bg);padding:14px 16px;border-radius:10px;overflow-x:auto;
  border:1px solid var(--line);margin:0 0 1.2em;
}
.markdown pre code{background:none;padding:0;font-size:.87em;line-height:1.6}
.markdown table{
  width:100%;border-collapse:collapse;margin:0 0 1.3em;font-size:.94em;
  display:block;overflow-x:auto;
}
.markdown th,.markdown td{border:1px solid var(--line);padding:8px 11px;text-align:left}
.markdown th{background:var(--side);font-weight:600;white-space:nowrap}
.markdown tr:nth-child(even) td{background:color-mix(in srgb,var(--side) 45%,transparent)}
.markdown img{max-width:100%;height:auto;border-radius:10px;border:1px solid var(--line)}
.markdown hr{border:0;border-top:1px solid var(--line);margin:2em 0}
.markdown a{word-break:break-word}

/* 翻页 */
.pager{display:flex;gap:12px;margin-top:56px;padding-top:22px;border-top:1px solid var(--line)}
.pager a{
  flex:1;display:flex;flex-direction:column;gap:3px;padding:12px 14px;
  border:1px solid var(--line);border-radius:10px;color:var(--fg);font-size:14px;
  background:var(--card);
}
.pager a:hover{border-color:var(--accent);text-decoration:none}
.pager a span{font-size:11px;color:var(--muted);letter-spacing:.06em}
.pager .next{text-align:right}

/* 页脚 */
.foot{margin-top:36px;font-size:13px;color:var(--muted)}
.foot a{color:var(--muted)}
.foot .dot{margin:0 8px;opacity:.5}

/* 首页 */
.hero{margin-bottom:32px}
.hero h1{font-size:2.2em;line-height:1.2;margin:0 0 .4em;letter-spacing:-.02em}
.hero .lead{font-size:1.05em;color:var(--muted);margin:0 0 .6em;max-width:38em}
.hero .meta{font-size:13px;color:var(--muted);margin:0}

.search-box{margin-bottom:36px}
.search-box input{
  width:100%;padding:12px 16px;font-size:15px;font-family:inherit;
  border:1px solid var(--line);border-radius:10px;background:var(--card);color:var(--fg);
  outline:none;transition:border-color .15s;
}
.search-box input:focus{border-color:var(--accent)}
.search-results{margin-top:12px}
.sr-item{
  display:block;padding:11px 14px;border:1px solid var(--line);border-radius:9px;
  margin-bottom:8px;background:var(--card);color:var(--fg);
}
.sr-item:hover{border-color:var(--accent);text-decoration:none}
.sr-item b{display:block;font-size:15px;margin-bottom:2px}
.sr-item span{font-size:13px;color:var(--muted);display:block;line-height:1.5}
.sr-item em{
  font-style:normal;font-size:11px;color:var(--accent);background:var(--accent-soft);
  padding:1px 6px;border-radius:4px;margin-right:6px;
}
.sr-empty{color:var(--muted);font-size:14px;padding:8px 2px}

.cards{display:grid;gap:18px}
.cat-card{
  background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px 22px;
}
.cat-card h2{font-size:1.15em;margin:0 0 .25em}
.cat-desc{font-size:13px;color:var(--muted);margin:0 0 14px}
.note-list{list-style:none;margin:0;padding:0}
.note-list li{margin:0}
.note-list a{
  display:block;padding:9px 11px;border-radius:8px;color:var(--fg);
}
.note-list a:hover{background:var(--side);text-decoration:none}
.note-list b{display:block;font-size:15px;font-weight:600;margin-bottom:1px}
.note-list span{display:block;font-size:13px;color:var(--muted);line-height:1.5}

/* 响应式 */
@media (max-width:1200px){
  .layout{grid-template-columns:230px minmax(0,1fr)}
  .page-toc{display:none}
}
@media (max-width:820px){
  #menuBtn{display:inline-flex}
  .layout{grid-template-columns:minmax(0,1fr)}
  .sidebar{
    display:none;position:fixed;top:56px;left:0;bottom:0;width:270px;z-index:40;
    background:var(--bg);border-right:1px solid var(--line);
  }
  .sidebar.open{display:block}
  .main{padding:22px 18px 70px}
  .hero h1{font-size:1.75em}
  .markdown{font-size:16px}
  .pager{flex-direction:column}
  .pager .next{text-align:left}
}
@media print{
  .topbar,.sidebar,.page-toc,.pager,.search-box,.foot{display:none}
  .layout{display:block}
  .main{max-width:none;padding:0}
}
"""

    js = r"""
(function(){
  // 主题
  var root=document.documentElement, btn=document.getElementById('themeBtn');
  var saved=localStorage.getItem('wiki-theme');
  if(saved){root.setAttribute('data-theme',saved);}
  else if(window.matchMedia('(prefers-color-scheme:dark)').matches){root.setAttribute('data-theme','dark');}
  function paint(){
    btn.textContent = root.getAttribute('data-theme')==='dark' ? '☀️' : '🌙';
  }
  paint();
  btn.addEventListener('click',function(){
    var next = root.getAttribute('data-theme')==='dark' ? 'light' : 'dark';
    root.setAttribute('data-theme',next);
    localStorage.setItem('wiki-theme',next);
    paint();
  });

  // 移动端目录
  var menu=document.getElementById('menuBtn'), side=document.getElementById('sidebar');
  if(menu&&side){
    menu.addEventListener('click',function(){side.classList.toggle('open');});
    side.addEventListener('click',function(e){
      if(e.target.tagName==='A'){side.classList.remove('open');}
    });
  }

  // 搜索（仅首页）
  var input=document.getElementById('searchInput');
  if(!input) return;
  var box=document.getElementById('searchResults'), data=null, loading=false;

  function load(cb){
    if(data) return cb();
    if(loading) return;
    loading=true;
    fetch('assets/search-index.json').then(function(r){return r.json();}).then(function(d){
      data=d; cb();
    }).catch(function(){
      box.innerHTML='<div class="sr-empty">搜索索引加载失败（本地直接双击打开文件时会出现，用 http 访问即可）。</div>';
    });
  }

  function esc(s){
    return String(s).replace(/[&<>"]/g,function(c){
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];
    });
  }

  function render(q){
    q=q.trim().toLowerCase();
    if(!q){box.innerHTML='';return;}
    var hits=data.filter(function(n){
      var hay=(n.t+' '+n.d+' '+n.c+' '+(n.k||[]).join(' ')).toLowerCase();
      return hay.indexOf(q)>=0;
    });
    if(!hits.length){box.innerHTML='<div class="sr-empty">没找到「'+esc(q)+'」相关的笔记。</div>';return;}
    box.innerHTML=hits.map(function(n){
      return '<a class="sr-item" href="'+n.u+'"><b>'+esc(n.t)+'</b>'+
        '<span><em>'+esc(n.c)+'</em>'+esc(n.d)+'</span></a>';
    }).join('');
  }

  var timer=null;
  input.addEventListener('input',function(){
    var q=input.value;
    clearTimeout(timer);
    timer=setTimeout(function(){
      load(function(){render(q);});
    },120);
  });

  // 从别的页面带 ?q= 过来时自动搜
  var params=new URLSearchParams(location.search);
  var q0=params.get('q');
  if(q0){input.value=q0;load(function(){render(q0);});}
})();
"""

    with open(os.path.join(OUT_ROOT, "assets", "style.css"), "w", encoding="utf-8") as f:
        f.write(css.strip() + "\n")
    with open(os.path.join(OUT_ROOT, "assets", "app.js"), "w", encoding="utf-8") as f:
        f.write(js.strip() + "\n")


if __name__ == "__main__":
    build()
