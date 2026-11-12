"""Génère les pages gérées par le CMS (réalisations et conseils) à partir de contenu/.

Lancé automatiquement par Netlify à chaque déploiement (voir netlify.toml), ou à la main :
    python outils/build.py

- contenu/realisations/*.json -> realisations.html (liste) + realisation-<fichier>.html (fiches)
- contenu/conseils/*.json     -> conseils.html (liste) + conseils-<fichier>.html (articles)
- photos envoyées via le CMS (img/uploads/) -> versions WebP 700 et 1400 px dans img/gen/
- sitemap.xml régénéré ; les photos de chantier affichées ailleurs mènent à leur fiche.
Les pages realisation-*.html et conseils-*.html sont entièrement générées : ne pas les modifier à la main.
"""
import datetime, hashlib, html, json, math, pathlib, re

import markdown
from PIL import Image, ImageOps

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://www.alphaisolation.be/"
CATS = {"ite": "Isolation & crépi", "renov": "Rénovation & nettoyage"}
MOIS = "janvier février mars avril mai juin juillet août septembre octobre novembre décembre".split()
CAM = ('<svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
       'stroke-linecap="round" stroke-linejoin="round"><path d="M4 8h3l2-3h6l2 3h3v11H4z"></path><circle cx="12" cy="13" r="3.5"></circle></svg>')
e = lambda s: html.escape(str(s), quote=True)


# ---------- contenus ----------
def load(folder):
    items = []
    for f in sorted((ROOT / "contenu" / folder).glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        d["slug"] = f.stem
        items.append(d)
    return items


# ---------- images ----------
def media(path):
    """Renvoie (petite, grande) pour une image du CMS ; crée les versions WebP si besoin."""
    rel = path.lstrip("/")
    src = ROOT / rel
    if not src.exists():
        raise SystemExit(f"Image introuvable : {path}")
    if src.parent == ROOT / "img" / "photos" and (src.parent / "sm" / src.name).exists():
        return f"img/photos/sm/{src.name}", rel
    out = ROOT / "img" / "gen"
    out.mkdir(parents=True, exist_ok=True)
    tag = hashlib.md5(rel.encode()).hexdigest()[:6]
    names = []
    for w in (700, 1400):
        dst = out / f"{src.stem}-{tag}-{w}.webp"
        if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
            with Image.open(src) as im:
                im = ImageOps.exif_transpose(im).convert("RGB")
                im.thumbnail((w, w * 2))
                im.save(dst, "WEBP", quality=78 if w > 700 else 72)
        names.append(f"img/gen/{dst.name}")
    return names[0], names[1]


def img(path, alt, cls="media media-card", sizes="(max-width: 760px) 50vw, 400px", lazy=True):
    sm, lg = media(path)
    return (f'<img class="{cls}" src="{sm}" srcset="{sm} 700w, {lg} 1400w" sizes="{sizes}" alt="{e(alt)}" width="1400" height="1400"'
            + (' loading="lazy"' if lazy else ' fetchpriority="high"') + ">")


def youtube_id(url):
    m = re.search(r"(?:youtu\.be/|v=|shorts/|embed/)([\w-]{11})", url or "")
    return m.group(1) if m else None


# ---------- gabarit commun ----------
def split_page(path):
    s = path.read_text(encoding="utf-8")
    head, rest = s.split("<main>", 1)
    tail = rest.split("</main>", 1)[1]
    return s, head, rest, tail


def set_head(head, title, desc, url, crumbs, og_type="website", extra_ld=None):
    h = re.sub(r"<title>.*?</title>", f"<title>{e(title)}</title>", head, 1)
    for pat, val in ((r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{e(desc)}">'),
                     (r'<meta property="og:description" content="[^"]*">', f'<meta property="og:description" content="{e(desc)}">'),
                     (r'<meta property="og:title" content="[^"]*">', f'<meta property="og:title" content="{e(title)}">'),
                     (r'<meta property="og:type" content="[^"]*">', f'<meta property="og:type" content="{og_type}">'),
                     (r'<link rel="canonical" href="[^"]*">', f'<link rel="canonical" href="{url}">'),
                     (r'<meta property="og:url" content="[^"]*">', f'<meta property="og:url" content="{url}">')):
        h = re.sub(pat, val, h, 1)
    items = [{"@type": "ListItem", "position": i + 1, "name": n, "item": u} for i, (n, u) in enumerate(crumbs)]
    ld = json.dumps({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": items}, ensure_ascii=False)
    if extra_ld:
        ld += '</script>\n<script type="application/ld+json">' + json.dumps(extra_ld, ensure_ascii=False)
    return re.sub(r'<script type="application/ld\+json">\{"@context": "https://schema.org", "@type": "BreadcrumbList".*?</script>',
                  lambda m: f'<script type="application/ld+json">{ld}</script>', h, 1, flags=re.S)


def replace_zone(s, name, content, first_run_pattern):
    start, end = f"<!-- {name}:DEBUT -->", f"<!-- {name}:FIN -->"
    block = f"{start}\n{content}\n{end}"
    if start in s:
        return re.sub(re.escape(start) + ".*?" + re.escape(end), lambda m: block, s, 1, flags=re.S)
    s2 = re.sub(first_run_pattern, lambda m: block, s, 1, flags=re.S)
    if s2 == s:
        raise SystemExit(f"Zone {name} introuvable")
    return s2


# ---------- réalisations ----------
def real_page(c):
    return f"realisation-{c['slug']}.html"


def real_media_count(c):
    return len(c.get("photos") or []) + len(c.get("videos") or []) + len([y for y in c.get("youtube") or [] if youtube_id(y)])


def real_card(c):
    n = real_media_count(c)
    lieu = f'{e(c["commune"])} · ' if c.get("commune") else ""
    return (f'<a class="card real-card" href="{real_page(c)}" data-cat="{c["categorie"]}">' + img(c["photos"][0], c["titre"])
            + f'<div class="card-body"><span class="tag">{lieu}{e(CATS[c["categorie"]])}</span>'
            f'<h2 class="h3 real-title">{e(c["titre"])}</h2><p class="muted small real-resume">{e(c["resume"])}</p>'
            f'<div class="card-foot"><span class="small muted real-count">{CAM} {n} {"média" if n == 1 else "médias"}</span>'
            f'<span class="link-strong">Voir le chantier →</span></div></div></a>')


def real_facts(c):
    rows = [("Travaux", ", ".join(c.get("travaux") or []))]
    for key, label in (("commune", "Commune"), ("annee", "Année"), ("surface", "Surface"), ("duree", "Durée du chantier")):
        if c.get(key):
            rows.append((label, c[key]))
    p = len(c.get("photos") or []); v = real_media_count(c) - p
    rows.append(("Médias", f"{p} photo{'s' if p > 1 else ''}" + (f", {v} vidéo{'s' if v > 1 else ''}" if v else "")))
    return '<dl class="facts" style="margin:0">' + "".join(f"<div><dt>{e(a)}</dt><dd>{e(b)}</dd></div>" for a, b in rows if b) + "</dl>"


def real_detail(c, all_items, cta):
    t = c["titre"]
    items = []
    for i, p in enumerate(c["photos"]):
        _, lg = media(p)
        items.append(f'<figure><a href="{lg}" data-lb data-caption="{e(t)}">{img(p, f"{t} — photo {i + 1}", "media media-sq", "(max-width: 760px) 50vw, 300px")}</a></figure>')
    for v in c.get("videos") or []:
        items.append(f'<figure><a href="{e(v.lstrip("/"))}" data-lb data-video data-caption="{e(t)}" class="lb-video">'
                     f'<video src="{e(v.lstrip("/"))}#t=0.5" preload="metadata" muted playsinline></video><span class="play" aria-hidden="true">▶</span>'
                     f'<span class="sr-only">Lire la vidéo</span></a></figure>')
    for y in c.get("youtube") or []:
        vid = youtube_id(y)
        if vid:
            items.append(f'<figure><a href="https://www.youtube.com/watch?v={vid}" data-lb data-youtube="{vid}" data-caption="{e(t)}" class="lb-video lb-yt">'
                         f'<span class="play" aria-hidden="true">▶</span><span class="yt-label">Vidéo du chantier</span></a></figure>')
    others = [o for o in all_items if o is not c and o["categorie"] == c["categorie"]][:3] or [o for o in all_items if o is not c][:3]
    lieu = f' à {e(c["commune"])}' if c.get("commune") else ""
    return f'''<main>
<section class="page-hero"><div class="wrap">
<ol class="crumbs" aria-label="Fil d'Ariane"><li><a href="index.html">Accueil</a></li><li><a href="realisations.html">Réalisations</a></li><li aria-current="page">{e(t)}</li></ol>
<div class="hero-grid">
<div class="stack" style="gap:22px">
<p class="eyebrow">{e(CATS[c["categorie"]])}{lieu}</p>
<h1 class="h1" style="font-size:clamp(32px,4vw,50px)">{e(t)}</h1>
<p class="lead">{e(c["description"])}</p>
{real_facts(c)}
<div class="btns"><a class="btn btn-primary" href="#devis">Un projet similaire ? Devis gratuit</a><a class="btn btn-outline" href="#photos">Voir les photos</a></div>
</div>
<a class="hero-media" href="{media(c["photos"][0])[1]}" data-lb-open="0">{img(c["photos"][0], t, "media media-hero", "(max-width: 900px) 100vw, 600px", lazy=False)}</a>
</div></div></section>
<section class="section-sm" id="photos"><div class="wrap stack-lg">
<h2 class="h2">Photos du chantier</h2>
<div class="gallery real-gallery">
{chr(10).join(items)}
</div>
</div></section>
<section class="section-sm"><div class="wrap stack-lg">
<div class="row-between"><h2 class="h2">Autres réalisations</h2><a class="link-strong" href="realisations.html">Toutes nos réalisations →</a></div>
<div class="grid swipe">{"".join(real_card(o) for o in others)}</div>
</div></section>
{cta.replace('name="page" value="realisations.html"', f'name="page" value="{real_page(c)}"')}
</main>'''


def build_realisations():
    items = [c for c in load("realisations") if c.get("publie", True) and c.get("photos")]
    items.sort(key=lambda c: (c.get("ordre") or 999, c["titre"]))
    path = ROOT / "realisations.html"
    s = path.read_text(encoding="utf-8")
    chips = ('<div class="chips" role="group" aria-label="Filtrer les réalisations"><button class="chip is-active" type="button" data-filter="all">Tous</button>'
             + "".join(f'<button class="chip" type="button" data-filter="{k}">{e(v)}</button>' for k, v in CATS.items()) + "</div>")
    listing = f'{chips}\n<div class="grid real-grid" id="real-grid">\n' + "\n".join(real_card(c) for c in items) + "\n</div>"
    s = replace_zone(s, "REALISATIONS", listing, r'<div class="chips" role="group" aria-label="Filtrer les réalisations">.*?\n</div>')
    path.write_text(s, encoding="utf-8", newline="")

    _, head, rest, tail = split_page(path)
    tail = re.sub(r"<script>\s*document\.querySelectorAll\('\[data-filter\]'\).*?</script>\n?", "", tail, flags=re.S)
    tail = tail.replace("</body>", '<script src="js/lightbox.js" defer></script>\n</body>', 1)
    cta = re.search(r'<section class="cta-band" id="devis">.*?</section>', rest, re.S).group(0)
    for old in ROOT.glob("realisation-*.html"):
        old.unlink()
    for c in items:
        url = SITE + real_page(c)
        h = set_head(head, f'{c["titre"]} | Réalisation Alpha Isolation',
                     f'{c["resume"]} Photos du chantier réalisé par Alpha Isolation, entreprise familiale de façade dans le Hainaut.',
                     url, [("Accueil", SITE), ("Réalisations", SITE + "realisations.html"), (c["titre"], url)], "article")
        (ROOT / real_page(c)).write_text(h + real_detail(c, items, cta) + tail, encoding="utf-8", newline="")
    return items


# ---------- conseils (blog) ----------
def post_page(a):
    return f"conseils-{a['slug']}.html"


def date_fr(d):
    d = datetime.date.fromisoformat(str(d)[:10])
    return f"{d.day} {MOIS[d.month - 1]} {d.year}"


def post_card(a, tag="h2"):
    live = a.get("statut") == "publie"
    open_, close = (f'<a class="card" href="{post_page(a)}">', "</a>") if live else ('<div class="card" aria-disabled="true">', "</div>")
    soon = "" if live else ' <span class="small muted">· Bientôt</span>'
    foot = '<span class="link-strong">Lire l\'article →</span>' if live else '<span class="small muted">Article à venir</span>'
    pic = img(a["image"], "") if a.get("image") else ""
    return (f'{open_}{pic}<div class="card-body"><span class="tag">{e(a.get("categorie", ""))}{soon}</span>'
            f'<{tag} class="h3" style="font-size:21px">{e(a["titre"])}</{tag}><p class="muted">{e(a.get("resume", ""))}</p>'
            f'<div class="card-foot">{foot}</div></div>{close}')


def render_body(md_text):
    body = markdown.markdown(md_text or "", extensions=["tables", "sane_lists"], output_format="html")
    # espaces insécables entre un nombre et son unité (« 72 h », « 120 €/m² »)
    body = re.sub(r">[^<]*", lambda m: re.sub(r"(\d) (h|ans|m²|€|cm|min|jours?|semaines?)\b", "\\1\u00a0\\2", m.group(0)), body)
    return body.replace("<table>", '<div class="tbl-box"><table>').replace("</table>", "</table></div>")


def post_detail(a, all_items, cta):
    words = len(re.sub(r"<[^>]+>", " ", render_body(a.get("corps"))).split())
    mins = max(1, math.ceil(words / 200))
    fig = ""
    if a.get("image"):
        cap = f'<figcaption class="muted">{e(a["legende"])}</figcaption>' if a.get("legende") else ""
        fig = f'<div class="wrap narrow"><figure>{img(a["image"], a.get("legende") or a["titre"], "media media-wide", "(max-width: 900px) 100vw, 760px", lazy=False)}{cap}</figure></div>'
    others = [o for o in all_items if o is not a][:3]
    autres = "" if not others else (f'<section class="section-sm white"><div class="wrap stack-lg">\n<h2 class="h2">À lire aussi</h2>\n'
                                    f'<div class="grid swipe">{"".join(post_card(o, "h3") for o in others)}</div>\n</div></section>')
    return f'''<main>
<article>
<section class="page-hero" style="padding-bottom:40px"><div class="wrap narrow stack" style="gap:20px">
<ol class="crumbs" aria-label="Fil d'Ariane"><li><a href="index.html">Accueil</a></li><li><a href="conseils.html">Conseils</a></li><li aria-current="page">{e(a["titre"])}</li></ol>
<p class="eyebrow">{e(a.get("categorie", "Conseils"))} · {mins} min de lecture</p>
<h1 class="h1" style="font-size:clamp(34px,4vw,50px)">{e(a["titre"])}</h1>
<p class="lead">{e(a.get("resume", ""))}</p>
<p class="small muted">Par l'équipe Alpha Isolation · Mis à jour le {date_fr(a["date"])}</p>
</div></section>
{fig}
<div class="wrap narrow" style="padding-bottom:72px"><div class="prose">
{render_body(a.get("corps"))}
<div class="btns" style="margin-top:24px"><a class="btn btn-primary" href="contact.html">Demander une visite gratuite</a><a class="btn btn-outline" href="realisations.html">Voir nos réalisations</a></div>
</div></div>
</article>
{autres}
{cta}
</main>'''


def build_conseils():
    items = [a for a in load("conseils") if a.get("statut") in ("publie", "a-venir")]
    items.sort(key=lambda a: (a.get("statut") != "publie", -datetime.date.fromisoformat(str(a["date"])[:10]).toordinal()))
    path = ROOT / "conseils.html"
    s = path.read_text(encoding="utf-8")
    grid = '<div class="grid swipe">' + "".join(post_card(a) for a in items) + "</div>"
    s = replace_zone(s, "CONSEILS", grid, r'<div class="grid swipe">.*?</div>(?=</div></section>)')
    path.write_text(s, encoding="utf-8", newline="")

    _, head, rest, tail = split_page(path)
    cta = re.search(r'<section class="cta-band" id="devis">.*?</section>', rest, re.S).group(0)
    for old in ROOT.glob("conseils-*.html"):
        old.unlink()
    published = [a for a in items if a.get("statut") == "publie"]
    for a in published:
        url = SITE + post_page(a)
        pic = SITE + media(a["image"])[1] if a.get("image") else SITE + "img/og-alpha-isolation.jpg"
        article_ld = {"@context": "https://schema.org", "@type": "Article", "headline": a["titre"], "description": a.get("resume", ""),
                      "image": pic, "datePublished": str(a["date"])[:10], "dateModified": str(a["date"])[:10], "inLanguage": "fr-BE",
                      "author": {"@type": "Organization", "name": "Alpha Isolation", "url": SITE},
                      "publisher": {"@id": SITE + "#entreprise"}, "mainEntityOfPage": url}
        h = set_head(head, f'{a["titre"]} | Alpha Isolation', a.get("resume", ""), url,
                     [("Accueil", SITE), ("Conseils", SITE + "conseils.html"), (a["titre"], url)], "article", article_ld)
        (ROOT / post_page(a)).write_text(h + post_detail(a, items, cta) + tail, encoding="utf-8", newline="")
    return published


# ---------- liens et sitemap ----------
def link_photos_elsewhere(reals):
    owner = {pathlib.Path(p).name: c for c in reals for p in c["photos"] if p.startswith("/img/photos/")}

    def rep(m):
        fig = m.group(0)
        name = re.search(r"img/photos/sm/([a-z0-9-]+\.webp)", fig)
        if not name or name.group(1) not in owner:
            return fig
        c = owner[name.group(1)]
        fig = re.sub(r'<a class="fig-link" href="[^"]*">(<img[^>]*>)</a>', r"\1", fig)
        fig = re.sub(r"(<img[^>]*>)", rf'<a class="fig-link" href="{real_page(c)}">\1</a>', fig, 1)
        return re.sub(r"<figcaption>.*?</figcaption>", f'<figcaption><a href="{real_page(c)}">{e(c["titre"])} →</a></figcaption>', fig, 1, flags=re.S)

    for f in ROOT.glob("*.html"):
        if f.name.startswith(("realisation", "conseils")):
            continue
        t = f.read_text(encoding="utf-8")
        t2 = re.sub(r"<figure>(?:(?!</figure>).)*?</figure>", rep, t, flags=re.S)
        if t2 != t:
            f.write_text(t2, encoding="utf-8", newline="")


def sitemap():
    today = datetime.date.today().isoformat()
    urls = [SITE if f.name == "index.html" else SITE + f.name for f in sorted(ROOT.glob("*.html"))
            if 'name="robots" content="noindex' not in f.read_text(encoding="utf-8")]
    urls.sort(key=lambda u: (u != SITE, u))
    (ROOT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                      + "".join(f"<url><loc>{u}</loc><lastmod>{today}</lastmod></url>\n" for u in urls) + "</urlset>\n",
                                      encoding="utf-8", newline="")
    return len(urls)


if __name__ == "__main__":
    reals = build_realisations()
    posts = build_conseils()
    link_photos_elsewhere(reals)
    print(f"{len(reals)} réalisations, {len(posts)} article(s) publié(s), {sitemap()} URLs dans le sitemap")
