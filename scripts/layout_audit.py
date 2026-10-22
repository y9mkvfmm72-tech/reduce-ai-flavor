#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""layout_audit.py — 第 8 层：版式体检

回答一个 flavor_audit.py 回答不了的问题：
    这份文件的**排版**像不像模板 / 网页打印 / Markdown 导出的产物？

它不看字句。实测里最容易漏掉的一类：文字七层全 PASS，版式一眼 AI。

用法
    python scripts/layout_audit.py 报告.pdf
    python scripts/layout_audit.py report.html

PDF 需要 pymupdf（python -m pip install pymupdf）；HTML 纯标准库。
docx 请先导出 PDF 再跑——版式问题只有渲染后才看得见。

输出 8.1–8.7，逐项 PASS / REVIEW / STRIP，并把具体数字摊开。
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PASS, REVIEW, STRIP, NA = "PASS", "REVIEW", "STRIP", "n/a"

MATH_FONT = re.compile(
    r"KaTeX|CambriaMath|^Math|Math$|^CM[A-Z]|LatinModern|STIX|XITS|Asana|TeXGyre", re.I)
STYLE_WORDS = {
    "bold", "italic", "oblique", "regular", "medium", "light", "semibold",
    "black", "roman", "book", "bolditalic", "semilight", "thin", "heavy",
}
PAGENO = re.compile(r"^[\s\-–—·|]*\d{1,3}[\s\-–—·|]*$|^\d{1,3}\s*/\s*\d{1,3}$")
FIGCAP = re.compile(r"Figure\s+\d+\s*[.:：]|Fig\.\s*\d+\s*[.:：]|图\s*\d+\s*[.:：]")
FIGREF = re.compile(r"Figure\s+\d+[ab]?|Fig\.\s*\d+[ab]?|图\s*\d+[ab]?")


def strip_subset(name: str) -> str:
    return re.sub(r"^[A-Z]{6}\+", "", name or "")


def family_of(name: str) -> str:
    n = strip_subset(name)
    parts = re.split(r"[-,]", n)
    keep = [parts[0]]
    for p in parts[1:]:
        if p.strip().lower() not in STYLE_WORDS:
            keep.append(p)
    return "-".join(keep) or n


def emit(tag: str, verdict: str, headline: str, details=None) -> None:
    print(f"[{tag}] {headline:<38} {verdict}")
    for d in details or []:
        print(f"      {d}")


# --------------------------------------------------------------------------- PDF

def audit_pdf(path: str) -> None:
    try:
        import pymupdf as fitz
    except ImportError:
        try:
            import fitz
        except ImportError:
            sys.exit("需要 pymupdf：python -m pip install pymupdf")

    doc = fitz.open(path)
    n = doc.page_count
    if n == 0:
        sys.exit("PDF 没有页面")

    char_by_font: Counter = Counter()
    bold_chars = total_chars = 0
    lead_ins = []
    bottoms, tops = [], []
    has_pageno = []
    word_gaps = []
    images = rules = gray_boxes = 0
    chunks = []

    for page in doc:
        H, W = page.rect.height, page.rect.width
        footer_zone = H * 0.92
        blocks = page.get_text("dict")["blocks"]

        page_bottoms, page_tops, pn = [], [], False
        for b in blocks:
            if b.get("type") != 0:
                continue
            lines = b.get("lines", [])
            for line in lines:
                for sp in line["spans"]:
                    t = sp["text"]
                    if not t.strip():
                        continue
                    char_by_font[sp["font"]] += len(t)
                    total_chars += len(t)
                    if (sp["flags"] & 16) or "bold" in sp["font"].lower():
                        bold_chars += len(t)

            for line in lines:
                txt = "".join(sp["text"] for sp in line["spans"]).strip()
                y1 = line["bbox"][3]
                if y1 >= footer_zone:
                    if PAGENO.match(txt):
                        pn = True
                else:
                    page_bottoms.append(y1)
                    page_tops.append(line["bbox"][1])

            if lines:
                first = lines[0]["spans"]
                if first and ((first[0]["flags"] & 16) or "bold" in first[0]["font"].lower()):
                    head = re.sub(r"\s+", " ", "".join(sp["text"] for sp in first)).strip()
                    if 0 < len(head) <= 60 and re.search(r"[.:：]$", head):
                        lead_ins.append(head)

        # 词距：两端对齐又没断词时，行内空格会被拉开
        grouped = {}
        for w in page.get_text("words"):
            x0, y0, x1, y1, txt, blk, ln, _ = w
            grouped.setdefault((blk, ln), []).append((x0, x1, txt))
        for ws in grouped.values():
            if len(ws) < 5:
                continue
            ws.sort()
            alpha = sum(1 for _, _, t in ws if re.search(r"[A-Za-z]{2,}", t))
            if alpha < len(ws) * 0.6:
                continue
            gaps = [ws[i + 1][0] - ws[i][1] for i in range(len(ws) - 1)]
            gaps = [g for g in gaps if g > 0]
            if len(gaps) >= 4:
                word_gaps.append(gaps)

        bottoms.append(max(page_bottoms) if page_bottoms else 0.0)
        tops.append(min(page_tops) if page_tops else 0.0)
        has_pageno.append(pn)
        chunks.append(page.get_text())

        images += len(page.get_images())
        for d in page.get_drawings():
            r = d["rect"]
            fill = d.get("fill")
            if r.height < 2.5 and r.width > W * 0.35:
                rules += 1
            if fill and abs(fill[0] - fill[1]) < 0.03 and abs(fill[1] - fill[2]) < 0.03:
                if 0.78 <= fill[0] <= 0.97 and r.width * r.height > 900:
                    gray_boxes += 1

    body = " ".join(chunks)

    # ---- 8.1 加粗
    ratio = bold_chars / total_chars if total_chars else 0
    v = STRIP if ratio > 0.06 or len(lead_ins) >= 8 else (
        REVIEW if ratio > 0.035 or len(lead_ins) >= 4 else PASS)
    emit("8.1", v, f"加粗 {ratio * 100:.1f}%（{bold_chars}/{total_chars}）",
         [f"段首短加粗标签 {len(lead_ins)} 处" +
          ("：" + " / ".join(lead_ins[:8]) if lead_ins else "")])

    # ---- 8.2 字体
    fam_chars: Counter = Counter()
    type3 = 0
    for f, c in char_by_font.items():
        if f.startswith("Type3"):
            type3 += c
            continue
        fam_chars[family_of(f)] += c
    ranked = fam_chars.most_common()
    math_fams = [f for f, _ in ranked if MATH_FONT.search(f)]
    other_fams = [f for f, _ in ranked if f not in math_fams]
    katex = any(f.startswith("KaTeX") for f in math_fams)
    real_math = [f for f in math_fams if not f.startswith("KaTeX")]

    if katex and not real_math:
        v, note = STRIP, "公式只有 KaTeX（Computer Modern 风格），正文没有同族数学字体 → 网页导出"
    elif katex and real_math:
        v, note = REVIEW, "公式混用 Cambria Math 与 KaTeX（根号/大运算符仍走 CM）"
    elif math_fams:
        v, note = PASS, "公式与正文同族"
    else:
        v, note = PASS, "无公式，或公式字体与正文一致"
    if len(other_fams) >= 3:
        v = STRIP

    details = ["、".join(f"{f}({c})" for f, c in ranked[:6]), note]
    if type3:
        details.append(f"另有 {type3} 字由 Type3 绘制（多为图内 SVG 文字，可印不可选）")
    emit("8.2", v, f"字体家族 {len(ranked)} 个", details)

    # ---- 8.3 分页
    usable = max(bottoms)
    real_tops = [t for t in tops if t]
    base = min(real_tops) if real_tops else 0
    span = usable - base if usable > base else 1
    blanks = [max(0.0, (usable - b) / span) for b in bottoms]
    mid = blanks[:-1] if n >= 3 else blanks
    worst_mid = max(mid) if mid else 0
    last = blanks[-1] if n >= 3 else 0
    v = STRIP if worst_mid > 0.25 or last > 0.75 else (
        REVIEW if worst_mid > 0.15 or last > 0.55 else PASS)
    bad = [(i + 1, round(r * 100)) for i, r in enumerate(blanks) if r > 0.15]
    emit("8.3", v, f"页底留白最大 {max(blanks) * 100:.0f}%",
         ["逐页：" + " ".join(f"p{i + 1}={r * 100:.0f}%" for i, r in enumerate(blanks))]
         + ([f"超过 15% 的页：{bad}"] if bad else [])
         + (["末页只剩不到 1/4 内容 = 尾页塌方"] if last > 0.75 else []))

    # ---- 8.4 页码
    got = sum(has_pageno)
    v = PASS if (n < 5 or got >= n - 1) else STRIP
    emit("8.4", v, f"页码 {got}/{n} 页",
         [] if v == PASS else ["没有页码不是'简洁'，是没做"])

    # ---- 8.5 图
    caps = len(FIGCAP.findall(body))
    refs = len(FIGREF.findall(body))
    figs = max(images, caps)
    if refs >= 2 and figs == 0:
        v, note = STRIP, f"正文提了 {refs} 次图，文件里一张都没有 → 读者看不到你描述的东西"
    elif refs >= 1 and figs == 0:
        v, note = REVIEW, "正文提到图，但没有图"
    else:
        v, note = PASS, f"图 {figs} 个（位图 {images} + 图注 {caps}），正文引用 {refs} 次"
    emit("8.5", v, f"图 {figs} 个", [note])

    # ---- 8.6 词距被拉大（两端对齐 + 未断词）
    flat_gaps = sorted(g for gaps in word_gaps for g in gaps)
    stretched = 0
    worst_word = 0.0
    if flat_gaps:
        ref_gap = flat_gaps[len(flat_gaps) // 2]
        for gaps in word_gaps:
            gs = sorted(gaps)
            med = gs[len(gs) // 2]
            if ref_gap > 0 and med > ref_gap * 2.0:
                stretched += 1
                worst_word = max(worst_word, med / ref_gap)
    share = stretched / len(word_gaps) if word_gaps else 0
    v = STRIP if share > 0.15 else (REVIEW if share > 0.05 else PASS)
    emit("8.6", v, f"词距被拉开 {share * 100:.0f}% 的行",
         [f"{stretched}/{len(word_gaps)} 行的词间距超过正常值的 {worst_word:.1f} 倍"
          " —— 两端对齐没开 hyphens，浏览器只能靠拉空格补满"] if stretched else [])

    # ---- 8.7 模板装饰
    v = STRIP if gray_boxes >= 3 else (REVIEW if gray_boxes >= 1 else PASS)
    emit("8.7", v, f"灰底块 {gray_boxes} 个 / 横线 {rules} 条",
         ["灰底块 = 表头 #efefef 或提示框底色，模板默认样式的标志"] if gray_boxes else
         ["横线多但无灰底：正常表格线，不算问题"] if rules > 12 else [])


# -------------------------------------------------------------------------- HTML

def audit_html(path: str) -> None:
    with open(path, encoding="utf-8", errors="replace") as fh:
        s = fh.read()
    body = s.split("<body>")[1] if "<body>" in s else s
    css = "\n".join(re.findall(r"<style[^>]*>([\s\S]*?)</style>", s))

    bold_tags = len(re.findall(r"<b>|<b\s|<strong", body))
    lead = re.findall(r"<(?:p|li)[^>]*>\s*(?:<b>|<strong>)(.{1,60}?)(?:</b>|</strong>)", body)
    v = STRIP if bold_tags >= 12 or len(lead) >= 6 else (REVIEW if bold_tags >= 5 else PASS)
    emit("8.1", v, f"加粗标签 {bold_tags} 个",
         [f"段首加粗标签 {len(lead)} 处" + ("：" + " / ".join(lead[:8]) if lead else "")])

    fams = re.findall(r"font-family\s*:\s*([^;}]+)", css)
    flat = []
    for f in fams:
        for x in f.split(","):
            x = x.strip().strip("\"'").lower()
            if x and x not in flat and x not in {"serif", "sans-serif", "monospace", "inherit"}:
                flat.append(x)
    katex = "katex" in s.lower()
    override = bool(re.search(r"\.katex[^{]*\{[^}]*font-family", css))
    v = REVIEW if (katex and not override) else PASS
    emit("8.2", v, f"声明字体 {len(flat)} 个",
         ["、".join(flat[:6])]
         + (["KaTeX 未做 font-family 覆盖 → 公式是 Computer Modern，与正文不同族"]
            if katex and not override else []))

    avoid = len(re.findall(r"page-break-inside\s*:\s*avoid", css))
    emit("8.3", NA, f"page-break-inside:avoid × {avoid}",
         ["HTML 看不到实际分页；导出 PDF 后对 PDF 再跑一次"])

    has_footer = bool(re.search(r"@page[^{]*\{[^}]*@(bottom|top)", css)) or "pageNumber" in s
    emit("8.4", PASS if has_footer else NA, "页码 " + ("有" if has_footer else "HTML 里没有"),
         [] if has_footer else ["页码通常由导出器的 header/footer template 给，HTML 里查不到；导出后对 PDF 再跑"])

    figs = len(re.findall(r"<figure", body)) or len(re.findall(r"<img|<svg", body))
    refs = len(FIGREF.findall(body))
    v = STRIP if refs >= 2 and figs == 0 else (REVIEW if refs and not figs else PASS)
    emit("8.5", v, f"图 {figs} 个", [f"正文引用 {refs} 次"])

    justify = css.count("justify")
    hyphens = "hyphens" in css
    v = REVIEW if justify and not hyphens else PASS
    emit("8.6", v, "两端对齐" + ("无断词" if justify and not hyphens else " OK"),
         ["text-align:justify 没开 hyphens → 词距会被拉开"] if v == REVIEW else [])

    h_border = len(re.findall(r"h[1-4][^{]*\{[^}]*border-bottom", css))
    kicker = bool(re.search(r"letter-spacing\s*:\s*[\d.]+px", css)) and "uppercase" in css
    note_box = len(re.findall(r"border-left[^;]*;[^}]*background", css)) + \
        len(re.findall(r"background[^;]*;[^}]*border-left", css))
    gray_th = len(re.findall(r"th[^{]*\{[^}]*background", css))
    score = (h_border > 0) + kicker + (note_box > 0) + (gray_th > 0)
    v = STRIP if score >= 3 else (REVIEW if score >= 2 else PASS)
    emit("8.7", v, f"模板装饰 {score}/4",
         [f"标题下横线 {h_border} 处", f"全大写+字距 kicker：{'有' if kicker else '无'}",
          f"左框+浅底提示块 {note_box} 处", f"表头灰底 {gray_th} 处"])


def main() -> None:
    ap = argparse.ArgumentParser(description="第 8 层：版式体检")
    ap.add_argument("file")
    a = ap.parse_args()

    print(f"file : {a.file}")
    if a.file.lower().endswith((".html", ".htm")):
        audit_html(a.file)
    else:
        audit_pdf(a.file)
    print()
    print("reading: 版式层只回答'像不像模板/网页导出'，不回答'是不是 AI 写的'。")
    print("         8.1/8.2/8.7 修起来不动一个字；8.3 调行距/字号收敛页数；8.4 加页码；8.5 补图；8.6 开 hyphens。")


if __name__ == "__main__":
    main()
