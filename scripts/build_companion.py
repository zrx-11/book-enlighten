#!/usr/bin/env python3
"""book-enlighten: 把 Markdown 学习知识库 + manifest.json 组装成单文件交互 HTML 学习伴侣。

用法：
  python3 build_companion.py --manifest <dir>/manifest.json --out <dir>/<slug>-companion.html

特性：目录导航、全文搜索、进度追踪（localStorage）、测验即时反馈、抽认卡、
术语检索、深色模式、打印友好。输出为无外部依赖的单文件（file:// 可直接打开；
Mermaid 图联网时自动渲染，离线时显示源码并给出说明）。
"""
import argparse
import html as html_mod
import json
import os
import re
import sys

# ----------------------------------------------------------------------------
# 最小 Markdown 渲染器（支持正文常用语法 + 安全 HTML 透传）
# ----------------------------------------------------------------------------

ALLOWED_RAW_TAGS = {
    "div", "span", "svg", "path", "rect", "circle", "line", "polyline",
    "polygon", "g", "text", "tspan", "defs", "lineargradient", "stop",
    "ellipse", "marker", "use", "a", "img", "details", "summary",
    "b", "i", "u", "br", "hr", "strong", "em", "code", "pre",
    "sub", "sup", "table", "thead", "tbody", "tr", "td", "th",
    "ul", "ol", "li", "p", "h1", "h2", "h3", "h4", "h5", "h6",
    "blockquote", "figure", "figcaption", "center",
}


def _escape(text):
    return html_mod.escape(text, quote=True)


def _sanitize_url(url):
    if re.match(r"^(https?://|mailto:|#|/|\.\.?/)", url, re.I):
        return _escape(url)
    return "#"


def _inline(text):
    """处理行内语法：code / **bold** / *italic* / [link](url)。输入为已转义文本。"""
    # `code`
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    # [text](url)
    def _link(m):
        label, url = m.group(1), m.group(2)
        return f'<a href="{_sanitize_url(url)}" target="_blank" rel="noopener">{label}</a>'
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", _link, text)
    # **bold**
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    # *italic*
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    return text


def _is_raw_open(line):
    m = re.match(r"^\s*</?([a-zA-Z0-9]+)", line)
    return m and m.group(1).lower() in ALLOWED_RAW_TAGS


def md_to_html(md_text):
    """把 Markdown 文本渲染为 HTML。输出已转义 + 安全透传。"""
    lines = md_text.replace("\r\n", "\n").split("\n")
    out = []
    i = 0
    n = len(lines)

    def flush_para(buf):
        if buf:
            txt = _inline(_escape(" ".join(buf).strip()))
            if txt:
                out.append(f"<p>{txt}</p>")
            buf.clear()

    para = []
    in_code = False
    code_buf = []
    code_lang = ""
    list_stack = []  # (type, indent)

    def close_lists(min_indent=0):
        while list_stack and list_stack[-1][1] >= min_indent:
            typ, _ = list_stack.pop()
            out.append("</ol>" if typ == "ol" else "</ul>")

    while i < n:
        line = lines[i]

        # 代码块
        if line.lstrip().startswith("```"):
            if in_code:
                lang = code_lang or ""
                cls = f' class="lang-{lang}"' if lang else ""
                if lang.lower() == "mermaid":
                    src = _escape("\n".join(code_buf))
                    out.append(
                        f'<div class="mermaid" data-src="1">{src}</div>'
                        f'<p class="mermaid-hint">↑ Mermaid 图示：联网时自动渲染为图表；离线时请阅读上方源码与正文说明。</p>')
                else:
                    out.append(f"<pre{cls}><code>{_escape(chr(10).join(code_buf))}</code></pre>")
                in_code = False
                code_buf = []
            else:
                flush_para(para)
                close_lists()
                in_code = True
                code_lang = line.lstrip()[3:].strip()
                code_buf = []
            i += 1
            continue
        if in_code:
            code_buf.append(line)
            i += 1
            continue

        # 原始 HTML 透传（安全标签白名单）
        if _is_raw_open(line):
            flush_para(para)
            close_lists()
            raw_buf = [line]
            j = i + 1
            while j < n and _is_raw_open(lines[j]):
                raw_buf.append(lines[j])
                j += 1
            out.append("\n".join(raw_buf))
            i = j
            continue

        stripped = line.strip()

        # 空行
        if not stripped:
            flush_para(para)
            close_lists()
            i += 1
            continue

        # 标题
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            flush_para(para)
            close_lists()
            level = len(m.group(1))
            out.append(f"<h{level}>{_inline(_escape(m.group(2)))}</h{level}>")
            i += 1
            continue

        # 分隔线
        if re.match(r"^(-{3,}|\*{3,}|_{3,})$", stripped):
            flush_para(para)
            close_lists()
            out.append("<hr>")
            i += 1
            continue

        # 引用
        if stripped.startswith(">"):
            flush_para(para)
            quote = _inline(_escape(re.sub(r"^>\s?", "", stripped)))
            out.append(f"<blockquote>{quote}</blockquote>")
            i += 1
            continue

        # 表格
        if stripped.startswith("|") and i + 1 < n and re.match(r"^\s*\|?[\s:\-|]+\|?\s*$", lines[i + 1]):
            flush_para(para)
            close_lists()
            header = [c.strip() for c in stripped.strip("|").split("|")]
            rows = []
            j = i + 2
            while j < n and lines[j].strip().startswith("|"):
                rows.append([c.strip() for c in lines[j].strip().strip("|").split("|")])
                j += 1
            tbl = ["<table><thead><tr>"]
            for c in header:
                tbl.append(f"<th>{_inline(_escape(c))}</th>")
            tbl.append("</tr></thead><tbody>")
            for r in rows:
                tbl.append("<tr>")
                for c in r:
                    tbl.append(f"<td>{_inline(_escape(c))}</td>")
                tbl.append("</tr>")
            tbl.append("</tbody></table>")
            out.append("".join(tbl))
            i = j
            continue

        # 列表
        m = re.match(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$", line)
        if m:
            indent = len(m.group(1).replace("\t", "    "))
            typ = "ol" if re.match(r"\d", m.group(2)) else "ul"
            content = m.group(3)
            if not list_stack or list_stack[-1][1] < indent:
                flush_para(para)
                close_lists(indent)
                if list_stack and list_stack[-1][1] < indent:
                    # 嵌套在上一项内
                    out[-1] = out[-1].rstrip("</li>") + "\n<" + typ + ">\n<li>"
                else:
                    out.append(f"<{typ}><li>")
                list_stack.append((typ, indent))
            elif list_stack[-1][1] == indent and list_stack[-1][0] != typ:
                # 同缩进换列表类型
                close_lists(indent)
                out.append(f"<{typ}><li>")
                list_stack.append((typ, indent))
            else:
                out.append("</li><li>")
            # 处理内容中的嵌套标记
            out.append(_inline(_escape(content)))
            i += 1
            continue

        # 普通段落
        para.append(stripped)
        i += 1

    flush_para(para)
    close_lists()
    return "\n".join(out)


# ----------------------------------------------------------------------------
# 学习伴侣 HTML 组装
# ----------------------------------------------------------------------------

def build_html(data):
    pages = data["pages"]  # {id: {"html": str, "kind": "chapter|concept", "title": str}}
    manifest = data["manifest"]

    # 学习路径页
    path_html = ["<h1>学习路径</h1>", "<p>按推荐顺序学习；每步通过检查点（自测题）后再继续。</p>", "<ol class='path-list'>"]
    for step in manifest.get("learningPath", []):
        chap_links = "、".join(
            f'<a href="#/chapter/{cid}">{_escape(manifest_ch_title(manifest, cid))}</a>'
            for cid in step.get("chapterIds", []))
        checkpoint = step.get("checkpoint", "")
        cp_html = f"<br>检查点：{_escape(checkpoint)}" if checkpoint else ""
        path_html.append(
            f"<li class='path-step' id='path-{step.get('step','')}'><strong>步骤 {step.get('step','')}："
            f"{_escape(step.get('title',''))}</strong><br>阅读：{chap_links}{cp_html}</li>")
    path_html.append("</ol>")
    path_html.append("<p>进度：<span id='path-progress-label'>0/0</span></p>")
    data["pages"]["__path__"] = {"html": "".join(path_html), "kind": "path", "title": "学习路径"}

    # 测验页
    quizzes_by_chapter = {}
    for q in manifest.get("quizzes", []):
        quizzes_by_chapter.setdefault(q.get("chapterId", "__all__"), []).append(q)
    quiz_pages = {}
    for cid, qs in quizzes_by_chapter.items():
        qh = ["<h1>测验" + (f"：{_escape(manifest_ch_title(manifest, cid))}" if cid != "__all__" else "（综合）") + "</h1>"]
        for idx, q in enumerate(qs, 1):
            qh.append(_render_quiz(q, idx))
        qh.append("<p class='quiz-summary'>完成作答后点击「检查答案」查看得分与解析。</p>")
        quiz_pages[cid] = "".join(qh)
    data["pages"]["__quiz_all__"] = {"html": "".join(
        _render_quiz(q, i) for i, q in enumerate(manifest.get("quizzes", []), 1)
        if q.get("chapterId") == "__all__") or "<p>（无综合题）</p>", "kind": "quiz", "title": "综合测验"}
    for cid, html_text in quiz_pages.items():
        if cid != "__all__":
            data["pages"][f"__quiz_{cid}__"] = {"html": html_text, "kind": "quiz", "title": "测验"}

    # 抽认卡页
    cards_html = ["<h1>抽认卡</h1>",
                  "<p>点击卡片翻面；判断「认识 / 不熟」以记录复习状态。</p>",
                  "<div class='card-controls'><label>按章节筛选：<select id='card-filter'><option value=''>全部</option></select></label>"
                  "<span class='card-counts'>认识 <b id='card-known'>0</b> · 不熟 <b id='card-again'>0</b> · 剩余 <b id='card-left'>0</b></span></div>",
                  "<div id='card-stage'><div class='flashcard' id='flashcard'><div class='fc-inner'><div class='fc-front'></div><div class='fc-back'></div></div></div></div>",
                  "<div class='card-actions'><button id='card-again-btn'>不熟</button><button id='card-known-btn'>认识</button></div>"]
    data["pages"]["__cards__"] = {"html": "".join(cards_html), "kind": "cards", "title": "抽认卡"}

    # 术语表页
    glossary_html = ["<h1>术语表</h1>", "<input id='glossary-filter' type='search' placeholder='筛选术语…'>", "<ul id='glossary-list'>"]
    for g in manifest.get("glossary", []):
        ch_ref = ""
        if g.get("chapterId"):
            ch_ref = (f" <span class=glossary-ref>（"
                      f"{_escape(manifest_ch_title(manifest, g.get('chapterId')))}）</span>")
        glossary_html.append(
            f"<li data-term='{_escape(g.get('term', '').lower())}'>{_escape(g.get('term', ''))} — "
            f"{_escape(g.get('def', ''))}{ch_ref}</li>")
    glossary_html.append("</ul>")
    data["pages"]["__glossary__"] = {"html": "".join(glossary_html), "kind": "glossary", "title": "术语表"}

    # 模式库 / 速查表
    for key, label, pid in (("patterns", "模式库", "__patterns__"), ("cheatsheet", "速查表", "__cheatsheet__")):
        f = (manifest.get(key) or {}).get("file")
        if f:
            fp = os.path.join(data["base_dir"], f)
            if os.path.exists(fp):
                with open(fp, "r", encoding="utf-8") as fh:
                    data["pages"][pid] = {"html": md_to_html(fh.read()), "kind": label, "title": label}

    # 侧边栏导航
    nav = [{"label": "学习路径", "href": "#/path"}]
    nav.append({"label": "章节", "children": [
        {"label": c.get("title", c.get("id")), "href": f"#/chapter/{c['id']}"} for c in manifest.get("chapters", [])]})
    if manifest.get("concepts"):
        nav.append({"label": "概念", "children": [
            {"label": c.get("title", c.get("id")), "href": f"#/concept/{c['id']}"} for c in manifest["concepts"]]})
    quiz_children = [{"label": "综合测验", "href": "#/quiz/all"}]
    quiz_children += [{"label": f"测验：{c.get('title', c.get('id'))}", "href": f"#/quiz/{c['id']}"}
                      for c in manifest.get("chapters", [])]
    nav.append({"label": "测验", "children": quiz_children})
    nav.append({"label": "抽认卡", "href": "#/cards"})
    nav.append({"label": "术语表", "href": "#/glossary"})
    if "__patterns__" in data["pages"]:
        nav.append({"label": "模式库", "href": "#/patterns"})
    if "__cheatsheet__" in data["pages"]:
        nav.append({"label": "速查表", "href": "#/cheatsheet"})

    data["nav"] = nav

    # 全部页面就绪后生成渲染快照
    data["rendered"] = {pid: p["html"] for pid, p in pages.items()}

    html_str = _SHELL
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html_str = html_str.replace("__TITLE__", _escape(manifest.get("title", "学习伴侣")))
    html_str = html_str.replace("__SUBTITLE__", _escape(manifest.get("subtitle", "")))
    html_str = html_str.replace("__DATA_JSON__", payload)
    return html_str


def manifest_ch_title(manifest, cid):
    for c in manifest.get("chapters", []):
        if c["id"] == cid:
            return c.get("title", cid)
    return cid or ""


def _render_quiz(q, idx):
    qtype = q.get("type", "single")
    qid = q.get("id", f"q{idx}")
    opts = q.get("options") or []
    question = _inline(_escape(q.get("question", "")))
    parts = [f"<div class='quiz-item' data-qid='{qid}' data-type='{qtype}'>",
             f"<p class='quiz-q'><b>Q{idx}.</b> {question}</p>"]
    if qtype in ("single", "multi"):
        input_type = "radio" if qtype == "single" else "checkbox"
        parts.append("<div class='quiz-opts'>")
        for oi, o in enumerate(opts):
            parts.append(
                f"<label class='quiz-opt'><input type='{input_type}' name='{qid}' value='{oi}'> "
                f"{_inline(_escape(str(o)))}</label>")
        parts.append("</div>")
    elif qtype == "blank":
        parts.append(f"<input class='quiz-blank' type='text' placeholder='填写答案'>")
    parts.append("<div class='quiz-actions'><button class='quiz-check'>检查答案</button>"
                 "<span class='quiz-feedback'></span></div>")
    parts.append("</div>")
    return "".join(parts)


# ----------------------------------------------------------------------------
# HTML 外壳（内嵌 CSS/JS，无外部依赖）
# ----------------------------------------------------------------------------

_SHELL = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root{
  --bg:#f7f7f8; --panel:#ffffff; --text:#1f2328; --muted:#6b7280;
  --accent:#2563eb; --accent-soft:#dbeafe; --border:#e5e7eb;
  --ok:#16a34a; --bad:#dc2626; --code-bg:#f3f4f6;
}
[data-theme="dark"]{
  --bg:#111318; --panel:#1a1d24; --text:#e5e7eb; --muted:#9ca3af;
  --accent:#60a5fa; --accent-soft:#1e3a5f; --border:#2d333d;
  --ok:#4ade80; --bad:#f87171; --code-bg:#20242c;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
  background:var(--bg);color:var(--text);line-height:1.7;font-size:15px}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
.layout{display:flex;min-height:100vh}
.sidebar{width:290px;flex:none;background:var(--panel);border-right:1px solid var(--border);
  padding:14px;position:sticky;top:0;height:100vh;overflow-y:auto}
.sidebar h1{font-size:17px;margin:2px 0 2px}
.sidebar .sub{font-size:12px;color:var(--muted);margin-bottom:10px}
#q{width:100%;padding:7px 10px;border:1px solid var(--border);border-radius:8px;background:var(--bg);color:var(--text);margin-bottom:10px}
.nav-sec{font-size:12px;color:var(--muted);margin:12px 0 4px;text-transform:uppercase;letter-spacing:.4px}
.nav-item{display:block;padding:5px 10px;border-radius:6px;color:var(--text);font-size:14px}
.nav-item:hover{background:var(--accent-soft);text-decoration:none}
.nav-item.active{background:var(--accent-soft);color:var(--accent);font-weight:600}
.nav-item .done{float:right;color:var(--ok);font-size:12px}
#nav-toggle{display:none}
.main{flex:1;min-width:0;padding:28px 40px 80px;max-width:920px}
.page h1{font-size:26px;border-bottom:2px solid var(--border);padding-bottom:8px;margin-top:0}
.page h2{font-size:20px;margin-top:26px}
.page h3{font-size:17px;margin-top:22px}
.page table{border-collapse:collapse;width:100%;margin:12px 0;font-size:14px}
.page th,.page td{border:1px solid var(--border);padding:6px 10px;text-align:left}
.page th{background:var(--code-bg)}
.page code{background:var(--code-bg);padding:2px 5px;border-radius:4px;font-size:.9em}
.page pre{background:var(--code-bg);padding:12px;border-radius:8px;overflow-x:auto;font-size:13px}
.page pre code{background:none;padding:0}
.page blockquote{border-left:4px solid var(--accent);margin:12px 0;padding:6px 14px;background:var(--accent-soft);border-radius:0 6px 6px 0}
.page blockquote blockquote{border-color:var(--muted)}
.page img{max-width:100%}
.mermaid{background:var(--code-bg);padding:14px;border-radius:8px;overflow-x:auto;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12.5px;white-space:pre;color:var(--muted)}
.mermaid-hint{font-size:12px;color:var(--muted);margin:4px 0 14px}
svg{max-width:100%;height:auto}
.quiz-item{border:1px solid var(--border);border-radius:10px;padding:14px 16px;margin:14px 0;background:var(--panel)}
.quiz-q{margin:0 0 8px;font-weight:500}
.quiz-opts label{display:block;padding:4px 0;cursor:pointer}
.quiz-blank{width:60%;padding:6px 10px;border:1px solid var(--border);border-radius:6px;background:var(--bg);color:var(--text)}
.quiz-check{margin-top:10px;padding:6px 16px;border:none;border-radius:6px;background:var(--accent);color:#fff;cursor:pointer}
.quiz-feedback{margin-left:12px;font-size:13px}
.fb-ok{color:var(--ok)}.fb-bad{color:var(--bad)}
.quiz-explain{margin-top:8px;font-size:13px;color:var(--muted);border-top:1px dashed var(--border);padding-top:6px}
.flashcard{perspective:1200px;margin:24px auto;max-width:520px;cursor:pointer;user-select:none}
.fc-inner{position:relative;width:100%;height:240px;transform-style:preserve-3d;transition:transform .5s}
.flashcard.flip .fc-inner{transform:rotateY(180deg)}
.fc-front,.fc-back{position:absolute;inset:0;backface-visibility:hidden;display:flex;align-items:center;justify-content:center;
  padding:22px;border-radius:14px;border:1px solid var(--border);background:var(--panel);font-size:16px;text-align:center}
.fc-back{transform:rotateY(180deg);background:var(--accent-soft);color:var(--text)}
.card-controls{display:flex;gap:14px;align-items:center;margin:12px 0;flex-wrap:wrap}
.card-actions{display:flex;gap:12px;justify-content:center}
.card-actions button{padding:8px 22px;border:none;border-radius:8px;cursor:pointer;font-size:14px}
#card-known-btn{background:var(--ok);color:#fff}
#card-again-btn{background:var(--bad);color:#fff}
.card-counts{color:var(--muted);font-size:13px}
.path-step{margin:8px 0;padding:10px 12px;border:1px solid var(--border);border-radius:8px;background:var(--panel)}
.path-step.passed{border-color:var(--ok)}
#glossary-filter{width:100%;max-width:380px;padding:7px 10px;border:1px solid var(--border);border-radius:8px;background:var(--bg);color:var(--text);margin-bottom:10px}
#glossary-list li{padding:6px 0;border-bottom:1px dashed var(--border)}
.glossary-ref{color:var(--muted);font-size:12px}
.search-hit{margin:10px 0}
.topbar{position:sticky;top:0;background:var(--bg);padding:8px 0;display:flex;justify-content:flex-end;z-index:10}
#theme-btn{border:1px solid var(--border);background:var(--panel);color:var(--text);border-radius:8px;padding:5px 12px;cursor:pointer;white-space:nowrap}
#progress-bar{height:5px;background:var(--border);border-radius:3px;margin:8px 0;overflow:hidden}
#progress-bar>div{height:100%;width:0;background:var(--accent);transition:width .3s}
.empty{color:var(--muted);padding:20px 0}
@media print{.sidebar,.topbar,.quiz-actions,.card-actions,.card-controls{display:none!important}.main{max-width:none;padding:0}}
@media (max-width:760px){.sidebar{width:100%;height:auto;position:static;padding:10px 14px}
  #nav{display:none}.sidebar.open #nav{display:block}
  #nav-toggle{display:block;width:100%;padding:8px 10px;margin:4px 0;border:1px solid var(--border);border-radius:8px;background:var(--bg);color:var(--text);font-size:14px;text-align:left;cursor:pointer}
  .layout{flex-direction:column}.main{padding:16px}}
</style>
</head>
<body>
<div class="layout">
  <aside class="sidebar">
    <h1>__TITLE__</h1>
    <div class="sub">__SUBTITLE__</div>
    <div id="progress-bar"><div id="progress-fill"></div></div>
    <div class="sub" id="progress-label">进度 0%</div>
    <input id="q" type="search" placeholder="搜索章节 / 概念 / 术语 / 全文…">
    <nav id="nav"></nav>
  </aside>
  <main class="main">
    <div class="topbar"><button id="theme-btn">🌙 深色</button></div>
    <div id="view" class="page"></div>
  </main>
</div>
<script>
const DATA = __DATA_JSON__;
const pages = DATA.rendered;
const manifest = DATA.manifest;
const $ = s => document.querySelector(s);
const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const SLUG = manifest.slug || 'book';
const store = {
  get(k){ try{ return JSON.parse(localStorage.getItem(SLUG+':'+k)||'null') }catch(e){ return null } },
  set(k,v){ try{ localStorage.setItem(SLUG+':'+k, JSON.stringify(v)) }catch(e){} }
};
let state = { visited: store.get('visited')||[], quiz: store.get('quiz')||{}, cards: store.get('cards')||{} };

/* ---------- 导航 ---------- */
function renderNav(){
  const nav = $('#nav'); nav.innerHTML='';
  const build = items => items.forEach(it=>{
    if(it.children){
      const sec=document.createElement('div'); sec.className='nav-sec'; sec.textContent=it.label; nav.appendChild(sec);
      it.children.forEach(c=>{
        const a=document.createElement('a'); a.className='nav-item'; a.href=c.href; a.textContent=c.label;
        const id=routeId(c.href);
        if(state.visited.includes(id)) a.innerHTML = esc(c.label)+' <span class="done">✓</span>';
        nav.appendChild(a);
      });
    }else{
      const a=document.createElement('a'); a.className='nav-item'; a.href=it.href; a.textContent=it.label;
      const id=routeId(it.href);
      if(state.visited.includes(id)) a.innerHTML = esc(it.label)+' <span class="done">✓</span>';
      nav.appendChild(a);
    }
  });
  build(DATA.nav);
  updateProgress();
}
function routeId(href){ return href.replace('#/',''); }

/* ---------- 路由 ---------- */
function routeIdFromHash(){
  let h = location.hash.replace(/^#\//,'');
  if(!h) return 'path';
  if(h==='path') return 'path';
  const m = h.match(/^(chapter|concept)\/(.+)$/);
  if(m) return m[1]+'/'+m[2];
  return h; // quiz/all, quiz/ch01, cards, glossary, patterns, cheatsheet
}
function showPage(rid){
  const id = rid==='path' ? '__path__' : rid.startsWith('quiz/') ? '__quiz_'+rid.split('/')[1]+'__' : rid==='cards'?'__cards__':rid==='glossary'?'__glossary__':rid==='patterns'?'__patterns__':rid==='cheatsheet'?'__cheatsheet__':rid.startsWith('chapter/')?rid.split('/')[1]:rid.startsWith('concept/')?rid.split('/')[1]:rid;
  const html = pages[id] || '<div class="empty">页面不存在</div>';
  $('#view').innerHTML = html;
  document.querySelectorAll('.nav-item').forEach(a=>a.classList.toggle('active', routeId(a.getAttribute('href'))===rid));
  if(!state.visited.includes(rid) && (rid.startsWith('chapter/')||rid.startsWith('concept/'))){
    state.visited.push(rid); store.set('visited', state.visited); renderNav();
  }
  window.scrollTo(0,0);
  if(rid==='cards') initCards();
  if(rid==='glossary') initGlossary();
  if(rid.startsWith('quiz')) initQuizzes(rid);
  if(id==='__path__') updatePath();
  renderMermaid();
}

/* ---------- 进度 ---------- */
function updateProgress(){
  const chs = (manifest.chapters||[]).length;
  const done = (manifest.chapters||[]).filter(c=>state.visited.includes('chapter/'+c.id)).length;
  const pct = chs? Math.round(done/chs*100) : 0;
  $('#progress-fill').style.width = pct+'%';
  $('#progress-label').textContent = `进度 ${pct}% · 已学 ${done}/${chs} 章`;
}
function updatePath(){
  document.querySelectorAll('.path-step').forEach(el=>{
    const step = el.id.replace('path-','');
    const s = (manifest.learningPath||[]).find(x=>x.step===step);
    if(s && (s.chapterIds||[]).every(c=>state.visited.includes('chapter/'+c))){
      el.classList.add('passed');
      const lbl = el.querySelector('.checkpoint-ok'); if(!lbl){ const sp=document.createElement('span'); sp.className='done'; sp.textContent=' ✓ 已完成'; el.appendChild(sp); }
    }
  });
}

/* ---------- 测验 ---------- */
function initQuizzes(rid){
  document.querySelectorAll('.quiz-item').forEach(item=>{
    const btn = item.querySelector('.quiz-check');
    if(!btn || item.dataset.inited){ return }
    item.dataset.inited='1';
    btn.addEventListener('click', ()=>{
      const qid = item.dataset.qid; const type = item.dataset.type;
      const q = (manifest.quizzes||[]).find(x=>x.id===qid); if(!q) return;
      let user, correct=false, fb;
      if(type==='single'){
        const sel = item.querySelector('input:checked');
        user = sel? parseInt(sel.value) : null;
        correct = user===q.answer;
        fb = correct?'✓ 正确':'✗ 错误'+(user==null?'（未作答）':'');
      } else if(type==='multi'){
        user = Array.from(item.querySelectorAll('input:checked')).map(i=>parseInt(i.value)).sort();
        const ans = Array.isArray(q.answer)? q.answer.slice().sort(): [q.answer];
        correct = user.length>0 && JSON.stringify(user)===JSON.stringify(ans);
        fb = correct?'✓ 正确':'✗ 错误';
      } else if(type==='blank'){
        const v = (item.querySelector('.quiz-blank').value||'').trim().toLowerCase();
        const a = String(q.answer).trim().toLowerCase();
        correct = v===a;
        fb = correct?'✓ 正确':'✗ 错误'+(v?'':'（未作答）');
      }
      item.querySelectorAll('input:checked').forEach(i=>{
        const val=parseInt(i.value);
        if(Array.isArray(q.answer)? q.answer.includes(val) : val===q.answer) i.parentElement.style.color='var(--ok)';
        else i.parentElement.style.color='var(--bad)';
      });
      const feed = item.querySelector('.quiz-feedback');
      feed.className = 'quiz-feedback '+(correct?'fb-ok':'fb-bad');
      feed.textContent = fb;
      let ex = item.querySelector('.quiz-explain');
      if(!ex){ ex=document.createElement('div'); ex.className='quiz-explain'; item.appendChild(ex); }
      ex.innerHTML = '解析：' + esc(q.explain||'');
      // 记录成绩（按章聚合）
      const ch = q.chapterId||'__all__';
      if(!state.quiz[ch]) state.quiz[ch]={done:0,total:0};
      state.quiz[ch].done = Math.min(state.quiz[ch].total+1, state.quiz[ch].done+1);
      state.quiz[ch].total += 1;
      store.set('quiz', state.quiz);
    });
  });
}

/* ---------- 抽认卡 ---------- */
let cardIdx = 0, cardList = [];
function initCards(){
  const cards = manifest.flashcards||[];
  cardList = cards.slice();
  cardIdx = 0;
  const sel = $('#card-filter');
  sel.innerHTML = '<option value="">全部</option>';
  [...new Set(cards.map(c=>c.chapterId).filter(Boolean))].forEach(c=>{
    const o=document.createElement('option'); o.value=c; o.textContent=manifestChTitle(c); sel.appendChild(o);
  });
  sel.onchange = ()=>{ const v=sel.value; cardList = v? cards.filter(c=>c.chapterId===v): cards.slice(); cardIdx=0; showCard(); };
  $('#flashcard').onclick = ()=>$('#flashcard').classList.toggle('flip');
  $('#card-known-btn').onclick = ()=>{ markCard(true); };
  $('#card-again-btn').onclick = ()=>{ markCard(false); };
  showCard();
}
function showCard(){
  updateCardCounts();
  if(cardIdx>=cardList.length){ $('#card-stage').innerHTML='<div class="empty">本组卡片已全部复习完 🎉</div>'; return; }
  const c = cardList[cardIdx];
  document.querySelector('.fc-front').textContent = c.front;
  document.querySelector('.fc-back').textContent = c.back;
  $('#flashcard').classList.remove('flip');
}
function markCard(known){
  const c = cardList[cardIdx]; if(!c) return;
  state.cards[c.id] = known?'known':'again';
  store.set('cards', state.cards);
  cardIdx++; showCard();
}
function updateCardCounts(){
  const known = Object.values(state.cards).filter(v=>v==='known').length;
  const again = Object.values(state.cards).filter(v=>v==='again').length;
  $('#card-known').textContent = known;
  $('#card-again').textContent = again;
  $('#card-left').textContent = Math.max(0, cardList.length-cardIdx);
}
function manifestChTitle(id){
  const c=(manifest.chapters||[]).find(x=>x.id===id); return c? c.title : id;
}

/* ---------- 术语表 ---------- */
function initGlossary(){
  const input = $('#glossary-filter');
  if(!input || input.dataset.inited) return;
  input.dataset.inited='1';
  input.oninput = ()=>{
    const v = input.value.trim().toLowerCase();
    document.querySelectorAll('#glossary-list li').forEach(li=>{
      li.style.display = (!v || li.dataset.term.includes(v)) ? '' : 'none';
    });
  };
}

/* ---------- 搜索 ---------- */
let searchIndex = null;
function buildSearchIndex(){
  if(searchIndex) return searchIndex;
  searchIndex = [];
  Object.entries(pages).forEach(([id, htmlText])=>{
    if(id.startsWith('__')) return;
    const text = htmlText.replace(/<[^>]+>/g,' ').replace(/\s+/g,' ');
    searchIndex.push({id, text});
  });
  return searchIndex;
}
$('#q').addEventListener('input', e=>{
  const v = e.target.value.trim().toLowerCase();
  if(!v){ showPage(routeIdFromHash()); return; }
  buildSearchIndex();
  const hits = searchIndex.filter(p=>p.text.toLowerCase().includes(v)).slice(0,20);
  const label = id => id.startsWith('chapter/')? ('章节：'+manifestChTitle(id.split('/')[1])) : id.startsWith('concept/')? ('概念：'+id.split('/')[1]) : id;
  $('#view').innerHTML = '<h1>搜索结果：'+esc(v)+'</h1>' +
    (hits.length? hits.map(h=>`<div class="search-hit"><a href="#/${h.id}">${esc(label(h.id))}</a><br><span class="sub">${esc(h.text.slice(0,180))}</span></div>`).join('')
                 : '<div class="empty">未找到相关页面，试试章节名/概念名/术语。</div>');
});

/* ---------- Mermaid 懒加载（联网渲染，离线显示源码） ---------- */
function renderMermaid(){
  if(!document.querySelector('.mermaid')) return;
  const boot=()=>{ try{
    mermaid.initialize({startOnLoad:false, theme: matchMedia('(prefers-color-scheme: dark)').matches?'dark':'default'});
    document.querySelectorAll('.mermaid').forEach(el=>{
      const code=el.textContent;
      mermaid.render('mm'+Math.random().toString(36).slice(2), code)
        .then(({svg})=>{ el.innerHTML=svg; })
        .catch(()=>{ el.textContent=code; });
    });
  }catch(e){} };
  const urls=['https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js',
              'https://unpkg.com/mermaid@10/dist/mermaid.min.js',
              'https://registry.npmmirror.com/mermaid/10/files/dist/mermaid.min.js'];
  let ui=0;
  const tryNext=()=>{
    if(ui>=urls.length) return;
    const s=document.createElement('script');
    s.src=urls[ui++];
    s.onload=boot;
    s.onerror=()=>{ s.remove(); tryNext(); };
    document.head.appendChild(s);
  };
  tryNext();
}

/* ---------- 深色模式 ---------- */
const themeBtn=$('#theme-btn');
themeBtn.onclick=()=>{
  const d = document.body.dataset.theme==='dark';
  document.body.dataset.theme = d? '' : 'dark';
  themeBtn.textContent = d? '🌙 深色' : '☀️ 浅色';
};

/* ---------- 启动 ---------- */
renderNav();
window.addEventListener('hashchange', ()=>showPage(routeIdFromHash()));
(function(){
  const sb=document.querySelector('.sidebar'); if(!sb) return;
  const btn=document.createElement('button'); btn.id='nav-toggle'; btn.textContent='目录（点开选择章节）';
  btn.onclick=()=>sb.classList.toggle('open');
  sb.insertBefore(btn, sb.querySelector('#nav'));
  window.addEventListener('hashchange',()=>{ if(window.innerWidth<=760) sb.classList.remove('open'); });
})();
showPage(routeIdFromHash());
</script>
</body>
</html>
"""


# ----------------------------------------------------------------------------
# 主流程
# ----------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="组装单文件 HTML 学习伴侣")
    ap.add_argument("--manifest", required=True, help="manifest.json 路径")
    ap.add_argument("--out", required=True, help="输出 HTML 路径")
    args = ap.parse_args()

    mdir = os.path.dirname(os.path.abspath(args.manifest))
    with open(args.manifest, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    base = mdir
    pages = {}
    for ch in manifest.get("chapters", []):
        fp = os.path.join(base, ch.get("file", ""))
        if not os.path.exists(fp):
            print(f"错误：章节文件不存在 {fp}", file=sys.stderr)
            return 2
        with open(fp, "r", encoding="utf-8") as f:
            pages[ch["id"]] = {"html": md_to_html(f.read()), "kind": "chapter", "title": ch.get("title", ch["id"])}
    for c in manifest.get("concepts", []):
        fp = os.path.join(base, c.get("file", ""))
        if not os.path.exists(fp):
            print(f"错误：概念文件不存在 {fp}", file=sys.stderr)
            return 2
        with open(fp, "r", encoding="utf-8") as f:
            pages[c["id"]] = {"html": md_to_html(f.read()), "kind": "concept", "title": c.get("title", c["id"])}

    data = {"manifest": manifest, "pages": pages, "base_dir": base}
    html_out = build_html(data)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html_out)

    kb = os.path.getsize(args.out)
    print(f"完成：{args.out}")
    print(f"  章节 {len(manifest.get('chapters', []))} · 概念 {len(manifest.get('concepts', []))} · "
          f"测验 {len(manifest.get('quizzes', []))} · 抽认卡 {len(manifest.get('flashcards', []))} · "
          f"术语 {len(manifest.get('glossary', []))}")
    print(f"  文件大小 {kb/1024:.1f} KB（单文件，可离线打开）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
