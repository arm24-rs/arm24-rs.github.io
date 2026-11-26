#!/usr/bin/env python3
"""Generate the Serbian Cyrillic pages under sr-cyrl/ from the Serbian Latin pages under sr/ (list in PAGES).

Run after every edit of a page under sr/:  python3 scripts/cyrl.py
Self-check only:  python3 scripts/cyrl.py --self-check

Text and the attributes alt, aria-label, content (meta) are transliterated. Kept in Latin:
<script>/<style>, any element with translate="no" or a lang attribute, and words in KEEP
or containing q, w, x or y (product names such as Python, WhatsApp).
Links to /sr/... become /sr-cyrl/..., except a link with lang="sr-Latn" (the language switch).
"""
import os
import re
import sys
from html.parser import HTMLParser
from html import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = ["", "javni-narucioci/"]  # sr/<page>index.html -> sr-cyrl/<page>index.html

DIGRAPHS = {"Lj": "Љ", "LJ": "Љ", "lj": "љ", "Nj": "Њ", "NJ": "Њ", "nj": "њ", "Dž": "Џ", "DŽ": "Џ", "dž": "џ"}
SINGLE = dict(zip("abcčćdđefghijklmnoprsštuvzž", "абцчћдђефгхијклмнопрсштувзж"))
SINGLE.update({k.upper(): v.upper() for k, v in SINGLE.items()})
# Brand, product and technical names that stay Latin in Serbian Cyrillic text.
KEEP = {"ARM24", "API", "AI", "AWS", "CPV", "IP", "Google", "Cloud", "GitHub", "Business", "GmbH", "SPSS", "R",
        "OneTick", "Comcon", "Research"}
# Words where lj, nj or dž are two letters, not a digraph.
SPLIT = {"nadž": 2, "podž": 2, "odž": 1, "predž": 3, "konjunk": 2, "injek": 1}  # substring: offset of the two letters
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
            if k == "href" and v and v.startswith("/sr/") and d.get("lang") != "sr-Latn":
                v = "/sr-cyrl/" + v[4:]
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
        if any(t == tag for t, _ in self.stack):  # ignore stray end tags
            while self.stack.pop()[0] != tag:
                pass
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

    def handle_pi(self, data):
        self.out.append(f"<?{data}>")

    def unknown_decl(self, data):
        self.out.append(f"<![{data}]>")


def swaps(page):
    """(Latin page text, Cyrillic page text): page identity, applied before conversion; each must occur once."""
    lat, cyr = "/sr/" + page, "/sr-cyrl/" + page
    return [
        ('<html lang="sr-Latn">', '<html lang="sr-Cyrl">'),
        # Cyrillic text must not paint in a fallback font and shift when Onest arrives (CLS)
        ('<link rel="preload" href="/fonts/onest-latin-wght-normal.woff2" as="font" type="font/woff2" crossorigin>', '<link rel="preload" href="/fonts/onest-cyrillic-wght-normal.woff2" as="font" type="font/woff2" crossorigin>\n<link rel="preload" href="/fonts/onest-latin-wght-normal.woff2" as="font" type="font/woff2" crossorigin>'),
        (f'<link rel="canonical" href="https://arm24.rs{lat}">', f'<link rel="canonical" href="https://arm24.rs{cyr}">'),
        (f'<meta property="og:url" content="https://arm24.rs{lat}">', f'<meta property="og:url" content="https://arm24.rs{cyr}">'),
        (f'<a href="{lat}" aria-current="page" lang="sr-Latn">Srpski</a> · <a href="{cyr}" lang="sr-Cyrl" hreflang="sr-Cyrl">Српски</a>',
         f'<a href="{lat}" lang="sr-Latn" hreflang="sr-Latn">Srpski</a> · <a href="{cyr}" aria-current="page" lang="sr-Cyrl">Српски</a>'),
    ] + {
        "": [('<a href="/demo/">', '<a href="/demo/?nazad=cyrl">'),
             ('<a href="/demo/povezivanje/">', '<a href="/demo/povezivanje/?nazad=cyrl">'),
             ('location.replace("/sr/javni-narucioci/"', 'location.replace("/sr-cyrl/javni-narucioci/"')],
        "javni-narucioci/": [('<a href="/demo/?nazad=jn">', '<a href="/demo/?nazad=cyrl-jn">')],
    }[page]


def convert(src, page):
    for a, b in swaps(page):
        assert src.count(a) == 1, f"expected once in sr/{page}index.html: {a}"
        src = src.replace(a, b)
    c = Conv()
    c.feed(src)
    c.close()
    return "".join(c.out)


def self_check():
    assert translit("Ljubljana Njegoš džep LJUBAV") == "Љубљана Његош џеп ЉУБАВ"
    assert translit("nadogradnje, Novi Sad.") == "надоградње, Нови Сад."
    assert translit("nadživeti podžanr konjunktura injekcija") == "надживети поджанр конјунктура инјекција"
    assert translit("odžaliti predžetva") == "оджалити преджетва"
    assert translit("API-ja Python WhatsApp ARM24 360dialog artem@arm24.rs") == "API-ја Python WhatsApp ARM24 360dialog artem@arm24.rs"
    assert translit("CPV 72262000 i Google Cloud") == "CPV 72262000 и Google Cloud"
    page = convert('<!doctype html><html lang="sr-Latn"><head><meta name="viewport" content="width=device-width">'
                   '<link rel="preload" href="/fonts/onest-latin-wght-normal.woff2" as="font" type="font/woff2" crossorigin>'
                   '<link rel="canonical" href="https://arm24.rs/sr/">'
                   '<meta property="og:url" content="https://arm24.rs/sr/"><meta name="description" content="Softver po meri">'
                   '<style>a{color:red}</style></head><body><a class="logo" href="/sr/" translate="no">ARM<span>24</span></a>'
                   '<a href="/sr/" aria-current="page" lang="sr-Latn">Srpski</a> · <a href="/sr-cyrl/" lang="sr-Cyrl" hreflang="sr-Cyrl">Српски</a>'
                   '<a href="/demo/">x</a><a href="/demo/povezivanje/">y</a><p>Usluge &amp; podrška</p><td translate="no">ARTEM PR</td><img alt="Slika">'
                   '<script>if(location.hash==="#ponuda")location.replace("/sr/javni-narucioci/"+location.search+"#ponuda")</script>'
                   '<a href="/sr/javni-narucioci/">Za javne naručioce</a></body></html>', "")
    for want in ('content="width=device-width"', 'lang="sr-Cyrl"', 'content="Софтвер по мери"', "a{color:red}", "Услуге &amp; подршка",
                 '<td translate="no">ARTEM PR</td>', 'alt="Слика"', '<a class="logo" href="/sr-cyrl/" translate="no">ARM<span>24</span>',
                 'href="https://arm24.rs/sr-cyrl/"', '<a href="/sr/" lang="sr-Latn" hreflang="sr-Latn">Srpski</a>',
                 'aria-current="page" lang="sr-Cyrl">Српски</a>', 'href="/demo/?nazad=cyrl"', 'href="/demo/povezivanje/?nazad=cyrl"', 'location.replace("/sr-cyrl/javni-narucioci/"+location.search+"#ponuda")',
                 '<a href="/sr-cyrl/javni-narucioci/">За јавне наручиоце</a>', 'href="/fonts/onest-cyrillic-wght-normal.woff2"'):
        assert want in page, want
    page = convert('<html lang="sr-Latn"><link rel="canonical" href="https://arm24.rs/sr/javni-narucioci/">'
                   '<link rel="preload" href="/fonts/onest-latin-wght-normal.woff2" as="font" type="font/woff2" crossorigin>'
                   '<meta property="og:url" content="https://arm24.rs/sr/javni-narucioci/">'
                   '<link rel="alternate" hreflang="sr-Latn" href="https://arm24.rs/sr/javni-narucioci/">'
                   '<a class="logo" href="/sr/" translate="no">ARM<span>24</span></a><a href="/sr/#services">usluge</a>'
                   '<a href="/sr/javni-narucioci/" aria-current="page" lang="sr-Latn">Srpski</a> · '
                   '<a href="/sr-cyrl/javni-narucioci/" lang="sr-Cyrl" hreflang="sr-Cyrl">Српски</a><a href="/demo/?nazad=jn">x</a></html>',
                   "javni-narucioci/")
    for want in ('<link rel="canonical" href="https://arm24.rs/sr-cyrl/javni-narucioci/">', 'content="https://arm24.rs/sr-cyrl/javni-narucioci/"',
                 'hreflang="sr-Latn" href="https://arm24.rs/sr/javni-narucioci/"', '<a class="logo" href="/sr-cyrl/"',
                 '<a href="/sr-cyrl/#services">услуге</a>', '<a href="/sr/javni-narucioci/" lang="sr-Latn" hreflang="sr-Latn">Srpski</a>',
                 '<a href="/sr-cyrl/javni-narucioci/" aria-current="page" lang="sr-Cyrl">Српски</a>', 'href="/demo/?nazad=cyrl-jn"'):
        assert want in page, want
    print("self-check ok")


if __name__ == "__main__":
    self_check()
    for page in [] if "--self-check" in sys.argv else PAGES:
        out = os.path.join(ROOT, "sr-cyrl", page, "index.html")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(os.path.join(ROOT, "sr", page, "index.html"), encoding="utf-8") as f:
            html = convert(f.read(), page)
        with open(out, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"wrote {os.path.relpath(out, ROOT)}")
