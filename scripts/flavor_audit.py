# -*- coding: utf-8 -*-
"""Which layer makes this document read as machine-written?

    python flavor_audit.py 文档.docx
    python flavor_audit.py 文档.docx --tables    # include table cells too

Read-only. It prints the counts and, more usefully, the exact sentences that
carry each pattern, so a human can delete or compress them.

Why this script exists: on the case that produced this skill, a 43-phrase
cliche scan scored 0 hits and sentence-length variance looked human, yet the
document still read AI-written. The giveaway was at the argument layer
(pre-emptive defence, invented mechanism, placeholder algebra) and the
narrative layer (no process), and - in the next round - at the artefact layer
(prose describing curves while the file embedded no figure at all).

Layers
  1 vocabulary   stock model phrases            (weak - 0 hits means little)
  2 argument     defence / meta / mechanism    (reliable)
                 placeholder algebra            (reliable: x% / 4x% is a tell)
  3 rhythm       sentence-length variance       (weak - variance can be high)
  4 narrative    waits, repeats, times, drift   (reliable: 0 is the tell)
  5 files        invisible characters           (mechanical residue)
  6 artefacts    figures/tables the prose needs but the file does not have
                                                (reliable: describing an absent
                                                 graph is the hardest tell)
  7 rhetoric     em-dash pairs, semicolon density, inversion, metaphor,
                 antithesis, essay markers, parenthetical asides, closure
                 sentences, mirrored paragraphs
                                                (reliable on short answers;
                                                 use --genre answer)

Layers 1 and 3 stay weak on purpose. Layer 7 exists because the second case
that produced this skill was seven short physics answers (2-3 marks each) to
which layers 1, 3, 4 and 6 all said PASS: no cliches, healthy sentence-length
variance, no timestamps needed, no figures to embed. What was wrong was
rhetorical - paired em dashes, one inverted clause, a "bridge between X and
the unmeasurable Y" metaphor, two paragraphs built on the same skeleton, and
every paragraph ending with a sentence that closed the argument rather than
reported it. Layers 4 and 6 are n/a on that genre, so they must not be read
as evidence of anything; --genre answer says so out loud.

Not a detector. A "REVIEW" line is a pointer, not a verdict.
"""
import argparse
import io
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

try:
    from docx import Document
    from docx.oxml.ns import qn
    HAVE_PYTHON_DOCX = True
except ImportError:
    # No python-docx (offline machine / locked-down Python): fall back to the
    # stdlib reader so .docx still works, including layers 5 and 6.
    from docxfallback import Document, qn
    HAVE_PYTHON_DOCX = False

from docxfallback import fonts_in_use


# --------------------------------------------------------------------------
# pattern banks
# --------------------------------------------------------------------------
CLICHE_EN = [
    "delve", "crucial", "pivotal", "underscore", "underscores", "moreover",
    "furthermore", "in conclusion", "overall", "it is important", "it is worth",
    "notably", "robust", "comprehensive", "leverage", "seamless", "landscape",
    "testament", "showcase", "foster", "intricate", "nuanced", "meticulous",
    "holistic", "in summary", "this demonstrates", "this highlights",
    "plays a crucial role", "valuable insights", "wide range of",
    "a variety of", "not only", "as well as", "on the other hand",
    "in order to", "due to the fact", "serves as", "utilize",
]
CLICHE_ZH = [
    "综上所述", "总而言之", "值得注意的是", "需要指出的是", "不仅", "而且",
    "奠定了基础", "提供了新的思路", "具有重要意义", "不可或缺", "至关重要",
    "全面", "深入", "赋能", "抓手", "闭环",
]

# A sentence that protects a result instead of reporting it.
DEFENCE = [
    r"so the [^.]{0,70}?(?:cannot|does not|is not)\b",
    r"cannot explain",
    r"no (?:larger|greater) than the (?:reading|uncertainty|scatter|noise)",
    r"cannot separate",
    r"is consistent with the (?:end|expected|reading|uncertainty|scatter)",
    r"rather than a (?:failure|defect|real)",
    r"is (?:therefore )?verified",
    r"does not affect the conclusion",
    r"does not (?:explain|account) for",
]
DEFENCE_ZH = ["说明这并非", "并不影响结论", "可以解释", "与理论相符",
              "验证了", "证明了", "误差在允许范围内", "不构成失败"]

# A sentence about the argument instead of the subject.
META = [
    r"which is the form in which",
    r"in the sense that",
    r"that is to say",
    r"in other words",
    r"the point is that",
    r"it is (?:worth|important) (?:noting|to note)",
    r"as (?:mentioned|noted) (?:above|earlier)",
    r"which is (?:why|how) the",
    # lab-report variants: pointing at artefacts the marker cannot open
    r"of the template",
    r"units of the template",
    r"of (?:the )?(?:calculation )?workbook",
    r"sheet[s]? \d",
    r"that accompanies this",
    r"as required by the (?:template|workbook|manual)",
]
META_ZH = ["也就是说", "换言之", "从某种意义上说", "这正是", "这就是为什么",
           "按模板", "见底稿", "工作簿中"]

# A plausible cause offered in place of a measured one. Each hit is a pointer:
# check it against the tables before keeping it.
MECHANISM = [
    r"\bis the signature of\b",
    r"\b(?:this|the offset|the spread|the scatter) points? to\b",
    r"\bis dominated by\b",
    r"\bcan be (?:attributed|explained|accounted for) by\b",
    r"\bis (?:therefore )?due to\b",
    r"\bbecause\b[^.]{0,90}\d",
    r"\b(?:the|this) (?:likely|probable) (?:cause|reason|explanation)\b",
    r"\barises from\b",
]
MECHANISM_ZH = ["这是因为", "其原因在于", "归因于", "说明这是由"]

# Placeholder algebra: a formula about symbols the document never instantiates.
PLACEHOLDER = [
    r"\bx\s*%", r"\b\d+x\s*%", r"\bfor (?:every|each) x\b", r"\bsome x\b",
    r"\bx\s*times\b", r"\bproportional to x\b", r"\barbitrary (?:x|n)\b",
]

# --- layer 7: rhetoric -----------------------------------------------------
# An inverted clause. "Only under this assumption are V and Stokes' law valid"
# is correct English and almost never written by hand under exam pressure.
INVERSION = [
    # anchored to sentence start or a clause break, and no comma may intervene:
    # "only of order rho*g*r, so the net force is downward" is not an
    # inversion, "Only under this assumption are V ... valid" is
    r"(?:^|[,;:]\s)(?-i:Only)\b[^.,;:]{0,60}?\b(?:is|are|was|were|does|do|did|can|"
    r"will|has|have)\b(?!\s+to\b)",
    r"(?:^|[,;:]\s)(?-i:Not until)\b[^.,;:]{0,60}?\b(?:is|are|was|were|does|do|did|"
    r"can)\b(?!\s+to\b)",
    r"\b(?-i:Rarely|Seldom|Little did|Never before)\b",
]

# A metaphor where a plain predicate would do. "X is the bridge between A and B"
# buys nothing except the sound of it.
METAPHOR = [
    r"\bis the bridge between\b",
    r"\bserves? as (?:a |the )?bridge\b",
    r"\bis the language of\b",
    r"\bis the currency of\b",
    r"\bis the backbone\b",
    r"\bis the engine (?:of|that)\b",
    r"\blies at the heart of\b",
    r"\bopens? the door to\b",
    r"\bis the lens\b",
    r"\bis the only way\b",
    r"\bis the price (?:of|you pay)\b",
]

# Two halves built to face each other. Rhetoric, not content.
ANTITHESIS = [
    r"\b(measurable|visible|known|explicit|macro\w*)\b[^.]{0,60}"
    r"\b(unmeasurable|invisible|unknown|implicit|micro\w*)\b",
    r"\b(\w{4,})\b[^.]{0,40}\bun\1\b",
    r"\bnot only\b[^.]{0,90}\bbut\b",
    r"\b(?:less|more) about\b[^.]{0,60}\bthan about\b",
]

# Essay scaffolding: the writer has decided the shape of the argument before
# answering the question.
ESSAY_MARK = [
    r"\bThe fundamental (?:reason|point|issue)\b",
    r"\bThere are (?:two|three|four|five) (?:main |key |basic )?"
    r"(?:reasons|points|things|forces|cases)\b",
    r"\bIn addition\b",
    r"\bFinally\b",
    r"\bFirst(?:ly)?\b[^.]{0,200}\bSecond(?:ly)?\b",
    r"\bTwo things follow\b",
    r"\bThe key (?:difference|point|idea|thing) (?:is|here is)\b",
    r"\bWhat matters (?:here )?is\b",
    r"\bIt (?:is|seems) (?:therefore )?(?:reasonable|natural|useful) to\b",
]
ESSAY_MARK_ZH = ["首先", "其次", "最后，", "综上", "关键在于", "从根本上说",
                 "究其原因", "由此可见"]

# A short gloss slipped into brackets: "(and hence the charge)", "(which is
# why ...)". The writer is annotating their own sentence.
ASIDE = re.compile(r"\((?=[^)]{0,70}\))[^)]*(?:hence|which|i\.e\.|e\.g\.|即|也就是)[^)]*\)")

# A closing sentence that finishes the argument instead of reporting the
# result: recommendation, necessity claim, or a jump to practical relevance.
CLOSURE = [
    r"\bis (?:therefore |thus )?(?:the )?(?:recommended|preferred|standard)\b",
    r"\bis usually the (?:one|method|version|approach)\b",
    r"\b(?:cannot|should not) be (?:ignored|neglected|omitted)\b",
    r"\bmust be (?:applied|used|included|corrected)\b",
    r"\bit must be\b",
    r"\b(?:which|this) is why\b",
    r"\bin (?:practice|the measurement|the lab)\b",
    r"\bthe (?:manual|handbook|worksheet) therefore\b",
    r"\bfar too (?:small|large|fast|slow) to\b",
    r"\bis what makes\b[^.]{0,60}\b(?:possible|meaningful|measurable)\b",
    r"\bmakes\b[^.]{0,60}\b(?:possible|meaningful|measurable|usable)\b",
    r"\bis (?:essential|indispensable)\b",
    r"\b(?:usually|normally) (?:have|has|need|needs) to be iterated\b",
]
CLOSURE_ZH = ["因此必须", "所以实际", "这是为什么", "必须采用", "不可或缺",
              "才能保证", "实际测量中", "手册要求"]

# Sentence-final give-aways (informational: a conclusion is allowed a verdict).
VERDICT_END = re.compile(
    r"(verif|confirm|agree|valid|consistent|holds|in line with)", re.I)

PROCESS_EN = re.compile(
    r"\b(?:wait(?:ed|ing)?|settl(?:ed|ing)|stabiliz(?:ed|ing)|"
    r"adjust(?:ed|ing)|repeat(?:ed|ing)|re-?scan(?:ned|ning)?|"
    r"re-?measur(?:ed|ing)|drift(?:ed|ing)?|saturat(?:ed|ing)|"
    r"warm(?:ed|ing)?\s+up|saved|recorded|took|re-?took)\b", re.I)
PROCESS_ZH = ["等待", "稳定", "重测", "重扫", "调节", "漂移", "饱和", "记录", "重做"]
TIME_RE = re.compile(r"\b\d{1,2}:\d{2}\b")
DURATION_RE = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:min(?:ute)?s?|s|sec(?:ond)?s?|h|hours?)\b", re.I)

FIG_REF = re.compile(r"(?:\bFig(?:ure)?\.?\s*|图\s*)(\d+)", re.I)
FIG_CAP = re.compile(r"^\s*(?:Fig(?:ure)?\.?\s*|图\s*)(\d+)[.．:：]?", re.I)
TAB_REF = re.compile(r"(?:\bTables?\s+|表\s*)([0-9]+|[A-Z]\d+)", re.I)
TAB_CAP = re.compile(r"^\s*(?:Table\s+|表\s*)([0-9]+|[A-Z]\d+)[.．:：]?", re.I)
CAPTION_LINE = re.compile(r"^\s*(?:Table|Figure|Fig\.?|表|图)\s*[0-9A-Z]", re.I)
CURVE_WORDS = re.compile(
    r"\b(?:curve|curves|plot|plotted|graph|spectrum|spectra)\b", re.I)

INVISIBLE = "\u2060\u200b\u200c\u200d\u200e\u200f\ufeff"

# Which layers say nothing about which genre. Printing "n/a" instead of
# "REVIEW" is the whole point: a term paper has no session clock and is not
# suspicious for it, and a talk script that cites slides does not need to embed
# them. Layer 5 is never skipped - invisible characters are a file problem in
# any genre. All six are student documents; the difference is which layers can
# be read as evidence.
GENRE_NA = {
    "notebook": [],          # lab book        - everything applies
    "report": [],            # lab / intern report
    "answer": [4, 6],        # short exam answer
    "paper": [4],            # term paper, reading report, literature review
    "thesis": [4],           # proposal, dissertation
    "talk": [4, 6],          # presentation / defence script
}
GENRE_HELP = {
    "notebook": "lab book: 0 timestamps is a tell",
    "report": "lab or internship report: may or may not carry a clock",
    "answer": "short exam/coursework answer; layers 4 and 6 do not apply",
    "paper": "term paper / reading report / review: no session clock needed",
    "thesis": "proposal or dissertation: no session clock, but figures apply",
    "talk": "presentation or defence script: no clock, no embedded figures",
}
GENRE_READING = {
    "answer": "on a short answer layers 2 and 7 decide it. Over-answering "
              "(more sentences than the marks justify) is the single strongest "
              "tell; then paired em dashes, then mirrored paragraphs.",
    "paper": "on a term paper layers 2 and 7 decide it; layer 4 does not apply, "
             "but overlap.py does - check the prose against the references, not "
             "just against a classmate's draft.",
    "thesis": "on a proposal or dissertation layer 2, 6 and 7 decide it: "
              "signposting, claims that do not match your own tables, and "
              "rhetoric standing in for an argument.",
    "talk": "on a talk script layer 7 decides it: every sentence is written to "
            "be heard, so triads, punchlines and one uplifting line per section "
            "stand out. There is no clock to check and no figure to embed.",
}


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------
def load(path, with_tables):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".docx":
        if Document is None:
            sys.exit("python-docx is required for .docx")
        doc = Document(path)
        paras = [" ".join(p.text.split()) for p in doc.paragraphs
                 if p.text.strip()]
        tables = []
        if with_tables:
            for t in doc.tables:
                for r in t.rows:
                    for c in r.cells:
                        if c.text.strip():
                            tables.append(" ".join(c.text.split()))
        return paras, tables, doc
    if ext in (".txt", ".md"):
        raw = io.open(path, encoding="utf-8", errors="replace").read()
        return [" ".join(l.split()) for l in raw.splitlines() if l.strip()], [], None
    sys.exit("unsupported file type: %s" % ext)


def bold_leadins(doc):
    """Paragraphs that open with a short bold label followed by plain text --
    the `**1. Adjustment.** ...` shape left behind by markdown conversion.
    A heading (one bold run, nothing after it) does not count."""
    n = 0
    for p in doc.paragraphs:
        if CAPTION_LINE.match(p.text or ""):
            continue
        try:
            runs = [r for r in p.runs if r.text.strip()]
        except Exception:
            continue
        if len(runs) < 2:
            continue
        head, rest = runs[0], runs[1:]
        if not head.bold or len(head.text.strip()) > 60:
            continue
        if any(r.bold for r in rest):
            continue
        if "".join(r.text for r in rest).strip():
            n += 1
    return n


def content_tables(doc):
    """Data tables, not the 1-row borderless tables used to lay out equations."""
    out = []
    for t in doc.tables:
        if len(t.rows) != 1:
            out.append(t)
            continue
        nonempty = sum(1 for c in t.rows[0].cells if c.text.strip())
        if nonempty > 1:
            out.append(t)
    return out


def sentences(text):
    parts = re.split(r"(?<=[.!?])\s+|(?<=[。！？])", text)
    return [s.strip() for s in parts if len(s.strip().split()) >= 4
            or len(re.findall(r"[\u4e00-\u9fff]", s)) >= 8]


def words(text):
    return len(text.split())


def first_person_count(text):
    """English + Chinese first person; a single-person lab group uses 我/I."""
    return len(re.findall(r"\b(?:we|our|my)\b", text, re.I)) + \
           len(re.findall(r"\bI\b", text)) + \
           len(re.findall(r"我(?:们)?", text))


def pct(n, total):
    return 100.0 * n / total if total else 0.0


def art(w):
    return "an" if w[:1].lower() in "aeiou" else "a"


def hits_of(bank, text):
    return [s for s in sentences(text)
            if any(re.search(rx, s, re.I) for rx in bank)]


def raw_sentences(text):
    """Split without the length filter - short clauses still carry rhetoric."""
    parts = re.split(r"(?<=[.!?])\s+|(?<=[。！？])", text)
    return [s.strip() for s in parts if s.strip()]


def para_skeleton(p):
    """First word of each sentence. Two paragraphs with the same skeleton were
    written to the same template, whatever they are about."""
    out = []
    for s in sentences(p):
        w = s.split()
        if w:
            out.append(re.sub(r"[^a-z]", "", w[0].lower()))
    return out


def mirror_pairs(prose):
    """Paragraph pairs whose sentence-initial words line up position by
    position. The giveaway on the Millikan case: 'In the equilibrium method the
    droplet is first ...' / 'In the dynamic method the falling time ...', same
    five-beat skeleton, same closing 'N quantities are needed'."""
    out = []
    sk = []
    for p in prose:
        if re.match(r"^\s*\d+[.、]", p) or CAPTION_LINE.match(p):
            sk.append([])
        else:
            sk.append(para_skeleton(p))
    for i in range(len(sk)):
        for j in range(i + 1, len(sk)):
            a, b = sk[i], sk[j]
            if len(a) < 3 or len(b) < 3 or abs(len(a) - len(b)) > 1:
                continue
            n = min(len(a), len(b))
            same = sum(1 for k in range(n) if a[k] and a[k] == b[k])
            if same >= max(2, int(0.6 * n)):
                out.append((i, j, same, n))
    return out


# --------------------------------------------------------------------------
# audit
# --------------------------------------------------------------------------
def audit(path, with_tables, genre="notebook", marks=None):
    paras, tables, doc = load(path, with_tables)
    na = GENRE_NA.get(genre, [])
    body = "\n".join(paras)
    blob = body + ("\n" + "\n".join(tables) if tables else "")

    prose = [p for p in paras if words(p) >= 15]
    prose_text = " ".join(prose)
    sents = sentences(prose_text)
    lens = [words(s) for s in sents]
    total_words = words(prose_text) or 1
    n_digits = len(re.findall(r"\d", prose_text))

    print("file : %s   genre: %s" % (os.path.basename(path), genre))
    print("words: %d (prose %d)  sentences: %d  prose paragraphs: %d  "
          "digits/100w: %.0f"
          % (words(blob), total_words, len(sents), len(prose),
             pct(n_digits, total_words)))

    # ---- 1 vocabulary -----------------------------------------------------
    low = blob.lower()
    hits = {}
    for w in CLICHE_EN:
        n = low.count(w)
        if n:
            hits[w] = n
    for w in CLICHE_ZH:
        n = blob.count(w)
        if n:
            hits[w] = n
    n_cliche = sum(hits.values())
    print("\n[1] vocabulary   %d hits  (%.1f per 1000 words)   %s"
          % (n_cliche, pct(n_cliche, total_words),
             "weak signal - 0 means little" if not n_cliche else "REVIEW"))
    for w, n in sorted(hits.items(), key=lambda kv: -kv[1])[:12]:
        print("      %-18s x%d" % (w, n))

    # ---- 2 argument -------------------------------------------------------
    defence, meta, verdicts = [], [], []
    for p in prose:
        ps = sentences(p)
        for s in ps:
            if any(re.search(rx, s, re.I) for rx in DEFENCE) or \
               any(z in s for z in DEFENCE_ZH):
                defence.append((p, s))
            if any(re.search(rx, s, re.I) for rx in META) or \
               any(z in s for z in META_ZH):
                meta.append((p, s))
        last = ps[-1] if ps else ""
        if VERDICT_END.search(last):
            verdicts.append((p, last))

    mech = hits_of(MECHANISM, prose_text) + \
        [s for s in sentences(prose_text) if any(z in s for z in MECHANISM_ZH)]
    ph = hits_of(PLACEHOLDER, prose_text)

    n_arg = len(defence) + len(meta)
    print("\n[2] argument     defence %d, meta %d, mechanism %d, "
          "placeholder %d, verdict-ending %d   %s"
          % (len(defence), len(meta), len(mech), len(ph), len(verdicts),
             "REVIEW" if (n_arg or ph) else "PASS"))
    for p, s in defence:
        print("      defence: %s" % s[:150])
    for p, s in meta:
        print("      meta   : %s" % s[:150])
    for s in mech:
        print("      mechanism (check against the tables): %s" % s[:150])
    for s in ph:
        print("      placeholder (a real number belongs here): %s" % s[:150])
    if verdicts:
        print("      (verdict endings are allowed in a conclusion; check that "
              "the body does not end every paragraph this way)")

    # ---- 3 rhythm ---------------------------------------------------------
    if 3 in na:
        print("\n[3] rhythm       n/a (sentence-length variance says nothing "
              "about %s %s)" % (art(genre), genre))
    elif len(lens) >= 8:
        mean = statistics.mean(lens)
        sd = statistics.pstdev(lens)
        burst = sd / mean if mean else 0
        status = "REVIEW" if burst < 0.35 else "PASS"
        print("\n[3] rhythm       mean %.1f words, sd %.1f, sd/mean %.2f   %s"
              % (mean, sd, burst, status))
        print("      paragraph sentence counts: %s"
              % ", ".join(str(len(sentences(p))) for p in prose[:20]))
        print("      (uniform counts + sd/mean < 0.35 = machine rhythm; "
              "variance alone proves nothing)")
    else:
        print("\n[3] rhythm       not enough sentences")

    # ---- 4 narrative ------------------------------------------------------
    fp = first_person_count(body)
    times = len(TIME_RE.findall(body))
    durs = len(DURATION_RE.findall(body))
    procs = len(PROCESS_EN.findall(body)) + sum(body.count(z) for z in PROCESS_ZH)
    n_narr = times + durs
    if 4 in na:
        status = "n/a (%s %s needs no session clock)" % (art(genre), genre)
    elif genre in ("notebook", "report"):
        status = "REVIEW" if (n_narr == 0 and total_words >= 400) else "PASS"
    else:
        status = "INFO (no session clock expected)"
    print("\n[4] narrative    first-person %d, clock %d, durations %d, "
          "process verbs %d   %s"
          % (fp, times, durs, procs, status))
    if status == "REVIEW":
        print("      no process narrative: this reads as a finished report, "
              "not a record. Add real waits / repeats / settings from the "
              "instrument files or lab notes - never invent them.")

    # ---- 5 files ----------------------------------------------------------
    n_inv = sum(body.count(c) for c in INVISIBLE)
    n_inv_tab = sum("".join(t).count(c) for t in tables for c in INVISIBLE) \
        if tables else 0
    print("\n[5] files        invisible chars: body %d%s   %s"
          % (n_inv, (", tables %d" % n_inv_tab) if with_tables else "",
             "CLEAN" if n_inv + n_inv_tab == 0 else "STRIP"))
    if n_inv + n_inv_tab:
        kinds = sorted({"U+%04X" % ord(c) for c in body + "".join(tables)
                        if c in INVISIBLE})
        print("      kinds: %s  (U+2060 also renders as a gap before dashes "
              "in some PDF exports)" % ", ".join(kinds))

    if doc is not None:
        latin = [(k, v) for k, v in fonts_in_use(doc).most_common()
                 if k != "Cambria Math"]
        if latin:
            shown = ", ".join("%s %d" % (k, v) for k, v in latin[:5])
            if len(latin) == 1:
                verdict = "OK (one Latin family)"
            elif len(latin) == 2:
                verdict = ("2 Latin families - heading + body is normal, but "
                           "check the two are not two spliced sources")
            else:
                verdict = ("%d Latin families - a document typed in one sitting "
                           "has one or two; three means a splice" % len(latin))
            print("      fonts: %s   %s" % (shown, verdict))
        n_lead = bold_leadins(doc)
        if n_lead:
            print("      bold lead-ins: %d paragraph(s) open with a bold label "
                  "and continue in plain text (markdown ** survived; drop the "
                  "bold, keep every word)" % n_lead)
        else:
            print("      bold lead-ins: 0")

    # ---- 6 artefacts ------------------------------------------------------
    if doc is None:
        print("\n[6] artefacts    n/a (not a .docx)")
    elif 6 in na:
        print("\n[6] artefacts    n/a (%s %s does not carry figures)"
              % (art(genre), genre))
    else:
        images = len(doc.inline_shapes)
        try:
            drawings = len(doc.element.body.findall(".//" + qn("w:drawing")))
        except Exception:
            drawings = images
        n_images = max(images, drawings)

        fig_refs = sorted({int(m.group(1)) for m in FIG_REF.finditer(body)})
        fig_caps = sorted({int(m.group(1)) for p in paras
                           for m in FIG_CAP.finditer(p)})
        tab_refs = sorted({m.group(1) for m in TAB_REF.finditer(body)})
        tab_caps = sorted({m.group(1) for p in paras
                           for m in TAB_CAP.finditer(p)})
        n_tables = len(content_tables(doc))
        curve_hits = len(CURVE_WORDS.findall(body))

        problems = []
        if fig_refs and n_images == 0:
            problems.append("Figure %s is cited, but the file embeds 0 images"
                            % ", ".join(str(i) for i in fig_refs))
        if fig_caps and n_images == 0:
            problems.append("figure caption present, but the file embeds 0 images")
        if n_images == 0 and not fig_caps and curve_hits >= 3:
            problems.append("no image in the file, yet the prose talks about "
                            "curves/plots %d times" % curve_hits)
        missing_caps = n_tables - len(tab_caps)
        if missing_caps > 1:      # one uncaptioned table is usually the cover
            problems.append("%d tables have no 'Table N.' caption" % missing_caps)
        bad_ref = [k for k in tab_refs if k.isdigit() and int(k) > n_tables]
        if bad_ref:
            problems.append("text cites Table %s, only %d tables exist"
                            % (", ".join(str(k) for k in bad_ref), n_tables))

        print("\n[6] artefacts    images %d, figure refs %d, figure captions %d "
              "| tables %d, table captions %d, table refs %d   %s"
              % (n_images, len(fig_refs), len(fig_caps), n_tables,
                 len(tab_caps), len(tab_refs),
                 "STRIP" if problems else "PASS"))
        for p in problems:
            print("      %s" % p)

    # ---- 7 rhetoric -------------------------------------------------------
    dash_text = body.replace("\u2014\u2014", "\u2014")
    em_pairs = [s for s in raw_sentences(dash_text) if s.count("\u2014") >= 2]
    semis = body.count(";") + body.count("\uff1b")
    inv = hits_of(INVERSION, body)
    meta4 = hits_of(METAPHOR, body)
    anti = hits_of(ANTITHESIS, body)
    essay = hits_of(ESSAY_MARK, body) + \
        [s for s in raw_sentences(body) if any(z in s for z in ESSAY_MARK_ZH)]
    asides = [m.group(0) for m in ASIDE.finditer(body)]

    def _closes(s):
        return any(re.search(rx, s, re.I) for rx in CLOSURE) or \
            any(z in s for z in CLOSURE_ZH)

    # Scanned everywhere, not only at paragraph ends: the "so it matters in
    # practice" tail often sits mid-paragraph.
    closes, para_close = [], []
    for p in prose:
        ps = sentences(p)
        for s in ps:
            if _closes(s):
                closes.append(s)
        if ps and _closes(ps[-1]):
            para_close.append(p)
    # claim -> formula -> number -> "so it matters": all four beats in one
    # paragraph, repeated across paragraphs, is the shape no student writes.
    four_beat = [p for p in para_close
                 if re.search(r"[=\u221d\u2248]", p) and re.search(r"\d", p)]
    mirrors = mirror_pairs(prose)

    n_rh = (len(em_pairs) + len(inv) + len(meta4) + len(anti) + len(essay)
            + len(asides) + len(closes))
    # 0-1 signals is normal English; 2 is worth a look; 3+ or a mirrored pair
    # is the shape no student produces by hand.
    rh_status = ("REVIEW" if n_rh >= 3 or mirrors else
                 ("INFO" if n_rh == 2 else "PASS"))
    print("\n[7] rhetoric    em-dash pairs %d, semicolons %d, inversion %d, "
          "metaphor %d, antithesis %d, essay markers %d, asides %d, "
          "closure %d, mirrored paragraphs %d   %s"
          % (len(em_pairs), semis, len(inv), len(meta4), len(anti),
             len(essay), len(asides), len(closes), len(mirrors), rh_status))
    for s in em_pairs:
        print("      em-dash pair: %s" % s[:140])
    for s in inv:
        print("      inversion  : %s" % s[:140])
    for s in meta4:
        print("      metaphor   : %s" % s[:140])
    for s in anti:
        print("      antithesis : %s" % s[:140])
    for s in essay:
        print("      essay mark : %s" % s[:140])
    for s in asides:
        print("      aside      : %s" % s[:140])
    for s in closes:
        print("      closure    : %s" % s[:140])
    for i, j, same, n in mirrors:
        print("      mirror     : paragraphs %d and %d share %d/%d sentence "
              "openings" % (i + 1, j + 1, same, n))
    if four_beat:
        print("      %d paragraph(s) run claim -> formula -> number -> "
              "'so it matters'; delete the last beat" % len(four_beat))
    if semis and total_words:
        per100 = pct(semis, total_words)
        if per100 >= 1.5:
            print("      semicolons at %.1f per 100 words: rewrite the ones "
                  "that are joining two full sentences" % per100)

    if genre == "answer":
        print("\n      answer length: %d paragraphs, %d sentences, %d words"
              % (len(prose), len(sents), total_words))
        if marks:
            print("      budget: %d marks -> about %d-%d sentences. You have "
                  "%d.%s" % (marks, marks, int(marks * 1.5), len(sents),
                             "" if len(sents) <= marks * 2
                             else "  Cut first, then rewrite."))
    if na:
        one = len(na) == 1
        print("\n      %s %s %s not apply to %s %s; ignore the status."
              % ("layer" if one else "layers",
                 ", ".join(str(k) for k in na),
                 "does" if one else "do", art(genre), genre))

    default = ("reading: layers 2, 4, 6 and 7 are the reliable ones; 1 and 3 "
               "only support them. A fitted figure is often the cheapest way to "
               "fix a document whose prose describes data the reader cannot see.")
    print("\n" + GENRE_READING.get(genre, default))
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("mine", help="document to audit (.docx/.txt/.md)")
    ap.add_argument("--tables", action="store_true",
                    help="include table cells in the corpus")
    ap.add_argument("--genre", choices=sorted(GENRE_NA), default="notebook",
                    help="which student document this is; picks the layers that "
                         "count as evidence. "
                         + " | ".join("%s: %s" % (k, GENRE_HELP[k])
                                      for k in sorted(GENRE_NA)))
    ap.add_argument("--marks", type=int, default=None,
                    help="mark value of the question, to flag over-answering "
                         "(only used with --genre answer)")
    a = ap.parse_args()
    sys.exit(audit(a.mine, a.tables, a.genre, a.marks))
