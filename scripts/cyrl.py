#!/usr/bin/env python3
"""Generate sr-cyrl/index.html (Serbian Cyrillic) from sr/index.html (Serbian Latin).

Run after every edit of sr/index.html:  python3 scripts/cyrl.py
Self-check only:  python3 scripts/cyrl.py --self-check

Text and the attributes alt, aria-label, content (meta) are transliterated. Kept in Latin:
<script>/<style>, any element with translate="no" or a lang attribute, and words in KEEP
or containing q, w, x or y (product names such as Python, WhatsApp).
"""
import os
import re
import sys
from html.parser import HTMLParser
from html import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC, OUT = os.path.join(ROOT, "sr/index.html"), os.path.join(ROOT, "sr-cyrl/index.html")

DIGRAPHS = {"Lj": "Љ", "LJ": "Љ", "lj": "љ", "Nj": "Њ", "NJ": "Њ", "nj": "њ", "Dž": "Џ", "DŽ": "Џ", "dž": "џ"}
SINGLE = dict(zip("abcčćdđefghijklmnoprsštuvzž", "абцчћдђефгхијклмнопрсштувзж"))
SINGLE.update({k.upper(): v.upper() for k, v in SINGLE.items()})
# Brand, product and technical names that stay Latin in Serbian Cyrillic text.
KEEP = {"ARM24", "API", "AI", "AWS", "CI", "CD", "CPV", "SDK", "MCP", "IP", "Google", "Cloud", "Kubernetes",
        "GitHub", "Pages", "Business", "GmbH", "Vue", "js", "SPSS", "R", "OneTick", "Comcon", "Research",
        "backend", "Backend", "cloud", "spoofing", "Gemini", "Claude", "Senior", "Lead", "Software", "Engineer",
        "Analyst", "DinaCard", "LAT"}
# Words where lj, nj or dž are two letters, not a digraph.
SPLIT = {"nadž": 2, "podž": 2, "konjunk": 2, "injek": 1}  # substring: offset of the two letters
WORD = re.compile(r"[A-Za-zČĆŽŠĐčćžšđ]+")


def word(w):
    if w in KEEP or re.search(r"[qwxyQWXY]", w):
        return w
    out, i, low = [], 0, w.lower()
    split = {low.find(p) + off for p, off in SPLIT.items() if p in low}
    while i < len(w):
        if w[i:i + 2] in DIGRAPHS and i not in split:
            out.append(DIGRAPHS[w[i:i + 2]]); i += 2
        else:
            out.append(SINGLE.get(w[i], w[i])); i += 1
    return "".join(out)


def translit(text):
    # Tokens with letters next to digits (ARM24, 360dialog), emails and URLs stay as they are.
    return re.sub(r"\S+", lambda m: m.group(0) if re.search(r"\d[A-Za-z]|[A-Za-z]\d|@|https?:|\.rs\b", m.group(0))
                  else WORD.sub(lambda w: word(w.group(0)), m.group(0)), text)


class Conv(HTMLParser):
    VOID = {"meta", "link", "br", "img", "input", "hr"}

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.out, self.stack = [], []  # stack of (tag, latin?)

    def latin(self):
        return any(l for _, l in self.stack)

    def attrs(self, tag, attrs):
        res, d = [], dict(attrs)
        meta_text = d.get("name") == "description" or d.get("property") in ("og:title", "og:description")
        for k, v in attrs:
            if v is not None and not self.latin() and (k in ("alt", "aria-label") or k == "content" and tag == "meta" and meta_text):
                v = translit(v)
            res.append(k if v is None else f'{k}="{escape(v, quote=True)}"')
        return "".join(" " + r for r in res)

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        self.out.append(f"<{tag}{self.attrs(tag, attrs)}>")
        if tag not in self.VOID:
            self.stack.append((tag, tag in ("script", "style") or d.get("translate") == "no" or "lang" in d and tag != "html"))

    def handle_startendtag(self, tag, attrs):
        self.out.append(f"<{tag}{self.attrs(tag, attrs)}/>")

    def handle_endtag(self, tag):
        while self.stack:
            if self.stack.pop()[0] == tag:
                break
        self.out.append(f"</{tag}>")

    def handle_data(self, data):
        self.out.append(data if self.latin() else translit(data))

    def handle_entityref(self, name):
        self.out.append(f"&{name};")

    def handle_charref(self, name):
        self.out.append(f"&#{name};")

    def handle_decl(self, decl):
        self.out.append(f"<!{decl}>")

    def handle_comment(self, data):
        self.out.append(f"<!--{data}-->")


SWAPS = [  # (Latin page text, Cyrillic page text): page identity, applied before conversion
    ('<html lang="sr-Latn">', '<html lang="sr-Cyrl">'),
    ('<link rel="canonical" href="https://arm24.rs/sr/">', '<link rel="canonical" href="https://arm24.rs/sr-cyrl/">'),
    ('<meta property="og:url" content="https://arm24.rs/sr/">', '<meta property="og:url" content="https://arm24.rs/sr-cyrl/">'),
    ('<a class="logo" href="/sr/" translate="no">', '<a class="logo" href="/sr-cyrl/" translate="no">'),
    ('<a href="/sr/" aria-current="page">SR</a> · <a href="/sr-cyrl/" lang="sr-Cyrl" hreflang="sr-Cyrl">ЋИР</a>',
     '<a href="/sr/" lang="sr-Latn" hreflang="sr-Latn">LAT</a> · <a href="/sr-cyrl/" aria-current="page">ЋИР</a>'),
]


def convert(src):
    for a, b in SWAPS:
        assert src.count(a) == 1, f"expected once in {SRC}: {a}"
        src = src.replace(a, b)
    c = Conv()
    c.feed(src)
    c.close()
    return "".join(c.out)


def self_check():
    assert translit("Ljubljana Njegoš džep LJUBAV") == "Љубљана Његош џеп ЉУБАВ"
    assert translit("nadogradnje, Novi Sad.") == "надоградње, Нови Сад."
    assert translit("nadživeti podžanr konjunktura injekcija") == "надживети поджанр конјунктура инјекција"
    assert translit("API-ja Python WhatsApp ARM24 360dialog artem@arm24.rs") == "API-ја Python WhatsApp ARM24 360dialog artem@arm24.rs"
    assert translit("CPV 72262000 i Google Cloud") == "CPV 72262000 и Google Cloud"
    page = convert('<!doctype html><html lang="sr-Latn"><head><meta name="viewport" content="width=device-width">'
                   '<link rel="canonical" href="https://arm24.rs/sr/">'
                   '<meta property="og:url" content="https://arm24.rs/sr/"><meta name="description" content="Softver po meri">'
                   '<style>a{color:red}</style></head><body><a class="logo" href="/sr/" translate="no">ARM<span>24</span></a>'
                   '<a href="/sr/" aria-current="page">SR</a> · <a href="/sr-cyrl/" lang="sr-Cyrl" hreflang="sr-Cyrl">ЋИР</a>'
                   '<p>Usluge &amp; podrška</p><td translate="no">ARTEM PR</td><img alt="Slika"></body></html>')
    for want in ('content="width=device-width"', 'lang="sr-Cyrl"', 'content="Софтвер по мери"', "a{color:red}", "Услуге &amp; подршка",
                 '<td translate="no">ARTEM PR</td>', 'alt="Слика"', '>ARM<span>24</span>', 'href="https://arm24.rs/sr-cyrl/"', ">LAT</a>"):
        assert want in page, want
    print("self-check ok")


if __name__ == "__main__":
    self_check()
    if "--self-check" not in sys.argv:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(SRC, encoding="utf-8") as f:
            html = convert(f.read())
        with open(OUT, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"wrote {os.path.relpath(OUT, ROOT)}")
