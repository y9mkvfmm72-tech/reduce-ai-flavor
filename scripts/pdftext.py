# -*- coding: utf-8 -*-
"""Extract text from a PDF without third-party libraries.

Handles the case that matters for Word/LibreOffice exports: Identity-H encoded
subset TrueType fonts, where every glyph is written as its own <hex> Tj and the
only way back to Unicode is the font's /ToUnicode CMap.

    python pdftext.py input.pdf [output.txt]

As a module:

    from pdftext import extract_text
    text = extract_text("paper.pdf")
"""
import io
import re
import sys
import zlib


def _load_objects(data):
    objs = {}
    for m in re.finditer(rb"(\d+)\s+0\s+obj\b", data):
        num = int(m.group(1))
        start = m.end()
        end = data.find(b"endobj", start)
        if end < 0:
            continue
        body = data[start:end]
        stream = None
        sm = re.search(rb"stream\r?\n", body)
        if sm:
            head = body[:sm.start()]
            raw = body[sm.end():]
            e = raw.rfind(b"endstream")
            if e > 0:
                raw = raw[:e]
            if b"/FlateDecode" in head:
                try:
                    raw = zlib.decompressobj().decompress(raw)
                except Exception:
                    raw = b""
            stream = raw
            objs[num] = (head, stream)
        else:
            objs[num] = (body, None)
    return objs


def _parse_tounicode(stream):
    cmap = {}
    txt = stream.decode("latin-1", "replace")
    for blk in re.findall(r"beginbfchar(.*?)endbfchar", txt, re.S):
        for src, dst in re.findall(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", blk):
            try:
                cmap[int(src, 16)] = bytes.fromhex(dst).decode("utf-16-be", "replace")
            except Exception:
                pass
    for blk in re.findall(r"beginbfrange(.*?)endbfrange", txt, re.S):
        for lo, hi, dst in re.findall(
                r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", blk):
            lo_i, hi_i = int(lo, 16), int(hi, 16)
            base = int(dst, 16)
            for k in range(lo_i, min(hi_i, lo_i + 65535) + 1):
                try:
                    cmap[k] = chr(base + (k - lo_i))
                except Exception:
                    pass
    return cmap


def _decode(hexs, cmap):
    try:
        b = bytes.fromhex(hexs)
    except Exception:
        return ""
    return "".join(cmap.get((b[i] << 8) | b[i + 1], "") for i in range(0, len(b) - 1, 2))


def extract_pages(path):
    data = open(path, "rb").read()
    objs = _load_objects(data)

    fonts = {}
    for num, (d, _s) in objs.items():
        m = re.search(rb"/Font\s*<<(.*?)>>", d or b"", re.S)
        if not m:
            continue
        for name, onum in re.findall(rb"/([A-Za-z0-9]+)\s+(\d+)\s+0\s+R", m.group(1)):
            fonts[name.decode()] = int(onum)

    cmaps = {}
    for name, onum in fonts.items():
        d, _ = objs.get(onum, (b"", None))
        m = re.search(rb"/ToUnicode\s+(\d+)\s+0\s+R", d or b"")
        if m:
            _hh, st = objs.get(int(m.group(1)), (b"", None))
            if st:
                cmaps[name] = _parse_tounicode(st)

    pages = []
    for num in sorted(objs):
        _d, st = objs[num]
        if st is None or b"BT" not in st:
            continue
        txt = st.decode("latin-1", "replace")
        cur = None
        out = []
        for tok in re.finditer(
                r"/([A-Za-z0-9]+)\s+[\d.]+\s+Tf|<([0-9A-Fa-f]+)>\s*Tj"
                r"|\[(.*?)\]\s*TJ", txt, re.S):
            if tok.group(1):
                cur = tok.group(1)
            elif tok.group(2):
                out.append(_decode(tok.group(2), cmaps.get(cur, {})))
            elif tok.group(3):
                for h in re.findall(r"<([0-9A-Fa-f]+)>", tok.group(3)):
                    out.append(_decode(h, cmaps.get(cur, {})))
        pages.append("".join(out))
    return pages


def extract_text(path):
    """Return the whole document as one string (word gaps are not reconstructed)."""
    return "\n".join(extract_pages(path))


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    pages = extract_pages(sys.argv[1])
    text = "\n".join(pages)
    if len(sys.argv) > 2:
        io.open(sys.argv[2], "w", encoding="utf-8").write(text)
    print("pages: %d  chars: %d" % (len(pages), len(text)))
    print(text[:800])
