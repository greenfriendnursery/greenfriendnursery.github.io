# -*- coding: utf-8 -*-
"""Generate static SEO product pages for the Green Friend website.

Reads the live catalogue from Supabase and writes one HTML page per product
into docs/product/<slug>.html, plus docs/sitemap.xml and docs/robots.txt.
"""
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import date

SUPABASE = "https://thiqwyltfgtluxizsaee.supabase.co"
KEY = "sb_publishable_5QySg5h9PeB_uROILAiSww_hfkEk12B"
SITE = "https://greenfriendnursery.github.io/"
OLD_HOSTS = [
    "https://greenfriend9563.github.io/green-friend-app/",
    "https://greenfriendnursery.github.io/greenfriendnursery/",
]
ROOT = os.environ.get("GF_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
OUT = os.path.join(DOCS, "product")
WA = "919563205299"
TODAY = date.today().isoformat()

HEADERS = {"apikey": KEY, "Authorization": "Bearer " + KEY}
CAT_EN = {
    "ফুল": "Flower plants",
    "ফল": "Fruit plants",
    "ইনডোর গাছ": "Indoor plants",
    "টব": "Pots",
    "অর্গানিক কেয়ার": "Organic care",
    "কম্বো প্যাক": "Combo pack",
}
CAT_BN = {
    "ফুল": "ফুলের গাছ",
    "ফল": "ফলের গাছ",
    "ইনডোর গাছ": "ইনডোর গাছ",
    "টব": "টব",
    "অর্গানিক কেয়ার": "অর্গানিক কেয়ার",
    "কম্বো প্যাক": "কম্বো প্যাক",
}


def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode("utf-8"))


def esc(s):
    return (str("" if s is None else s)
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#39;"))


def slugify(name):
    s = str(name).lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "plant"


def money(n):
    return "\u20b9" + format(int(round(float(n))), ",").replace(",", ",")


def fix(url):
    s = str(url or "")
    for host in OLD_HOSTS:
        s = s.replace(host, SITE)
    return s


def thumb(url):
    u = fix(url)
    if u.startswith(SITE + "products/") and "/products/thumbs/" not in u:
        return u.replace(SITE + "products/", SITE + "products/thumbs/")
    return u


def photos_of(p):
    urls = p.get("image_urls") or []
    if not isinstance(urls, list):
        urls = []
    urls = [u for u in urls if u]
    if not urls and p.get("image_url"):
        urls = [p["image_url"]]
    return [fix(u) for u in urls]


def sizes_of(p):
    out = []
    for s in (p.get("sizes") or []):
        try:
            if s and s.get("label") and float(s.get("price") or 0) > 0:
                out.append({"label": str(s["label"]), "price": float(s["price"])})
        except Exception:
            pass
    return out[:3]


def main():
    cols = "id,name,bn,category,price,offer_price,sizes,image_url,image_urls,note,note_bn,stock_quantity,seller_id"
    products = get(SUPABASE + "/rest/v1/products?select=" + cols +
                   "&is_active=eq.true&order=created_at.desc&limit=300")
    products = [p for p in products if p.get("name")]
    try:
        sellers = get(SUPABASE + "/rest/v1/seller_public?select=id,shop_name,city")
    except Exception:
        sellers = []
    shop_by_id = {s["id"]: s for s in (sellers or []) if s.get("id")}
    for p in products:
        srow = shop_by_id.get(p.get("seller_id") or "")
        p["_shop"] = (srow or {}).get("shop_name") or "Green Friend"
        p["_shop_id"] = (srow or {}).get("id") or "greenfriend"

    os.makedirs(OUT, exist_ok=True)

    # unique slugs
    used = {}
    for p in products:
        base = slugify(p["name"])
        slug = base
        n = 2
        while slug in used:
            slug = base + "-" + str(n)
            n += 1
        used[slug] = p["id"]
        p["_slug"] = slug

    by_cat = {}
    for p in products:
        by_cat.setdefault((p.get("category") or "").strip(), []).append(p)

    urls = []
    for p in products:
        name = p["name"]
        bn = (p.get("bn") or "").strip()
        cat = (p.get("category") or "").strip()
        cat_en = CAT_EN.get(cat, cat or "Plants")
        cat_bn = CAT_BN.get(cat, cat or "গাছ")
        sizes = sizes_of(p)
        prices = [s["price"] for s in sizes] or [float(p.get("price") or 0)]
        low, high = min(prices), max(prices)
        stock = p.get("stock_quantity")
        out_of_stock = stock == 0
        pics = photos_of(p)
        main_pic = pics[0] if pics else ""
        url = SITE + "product/" + p["_slug"] + ".html"
        urls.append((url, TODAY))

        title = "%s \u2014 %s | Green Friend, Malda" % (name, cat_en)
        if cat in ("ফল",):
            title = "%s \u2014 Mango & fruit plants from Malda | Green Friend" % name
        desc_core = "Buy %s online from Green Friend, Malda." % name
        if len(sizes) > 1:
            desc_core += " %d sizes from %s, up to 8 ft." % (len(sizes), money(low))
        else:
            desc_core += " Up to 8 ft, from %s." % money(low)
        desc_extra = " Free delivery above \u20b91000. COD/UPI."
        description = desc_core + desc_extra
        # Google shows roughly 155-160 characters; keep the important part only.
        if len(description) > 158:
            description = desc_core if len(desc_core) <= 158 else (desc_core[:155] + "...")

        note = (p.get("note") or "").strip()
        note_bn = (p.get("note_bn") or "").strip()

        size_rows = "".join(
            '<li data-label="%s" data-price="%s"><span>%s</span><b>%s</b></li>'
            % (esc(s["label"]), esc(money(s["price"])), esc(s["label"]), money(s["price"]))
            for s in sizes
        ) or '<li data-label="Standard" data-price="%s"><span>Standard</span><b>%s</b></li>' % (esc(money(low)), money(low))

        gallery = ""
        if pics:
            gallery = ('<div class="gal"><img class="hero" src="%s" alt="%s" width="640" height="640">'
                       % (esc(pics[0]), esc(name)))
            if len(pics) > 1:
                gallery += '<div class="thumbs">' + "".join(
                    '<img src="%s" alt="%s photo %d" loading="lazy">' % (esc(thumb(u)), esc(name), i + 1)
                    for i, u in enumerate(pics[:5])) + "</div>"
            gallery += "</div>"
        else:
            gallery = '<div class="gal"><div class="ph">%s</div></div>' % esc(p.get("emoji") or "\U0001f331")

        related = [r for r in by_cat.get(cat, []) if r["id"] != p["id"]][:3]
        rel_html = ""
        if related:
            rel_html = '<section class="wrap rel"><h2>More %s</h2><div class="relgrid">' % esc(cat_en.lower())
            for r in related:
                rp = photos_of(r)
                rs = sizes_of(r)
                rprices = [s["price"] for s in rs] or [float(r.get("price") or 0)]
                rel_html += ('<a class="relcard" href="%s.html"><img src="%s" alt="%s" loading="lazy">'
                             '<b>%s</b><span>from %s</span></a>'
                             % (esc(r["_slug"]), esc(thumb(rp[0]) if rp else ""),
                                esc(r["name"]), esc(r["name"]), money(min(rprices))))
            rel_html += "</div></section>"

        offers = {
            "@type": "AggregateOffer",
            "priceCurrency": "INR",
            "lowPrice": int(round(low)),
            "highPrice": int(round(high)),
            "offerCount": max(1, len(sizes)),
            "availability": "https://schema.org/OutOfStock" if out_of_stock else "https://schema.org/InStock",
            "url": url,
        }
        if main_pic:
            offers["image"] = main_pic
        ld = {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": name,
            "description": (note or description),
            "category": cat_en,
            "brand": {"@type": "Brand", "name": "Green Friend"},
            "offers": offers,
        }
        if main_pic:
            ld["image"] = pics
        breadcrumb = {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE},
                {"@type": "ListItem", "position": 2, "name": cat_en, "item": SITE + "#plants"},
                {"@type": "ListItem", "position": 3, "name": name, "item": url},
            ],
        }

        sold_line = '<p class="soldby">Sold By : <a href="../index.html?shop=%s">%s</a></p>' % (
            esc(p["_shop_id"]), esc(p["_shop"]))
        bn_line = ""
        if bn:
            bn_line = '<p class="bn">%s \u2014 %s</p>' % (esc(bn), esc(cat_bn))

        html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="product">
<meta property="og:title" content="{name} \u2014 Green Friend">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{url}">
{og_image}
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#232820">
<script type="application/ld+json">{ld}</script>
<script type="application/ld+json">{bc}</script>
<style>
:root{{--green:#232820;--green2:#333A2E;--green3:#F1F3ED;--gold:#A9741C;--ink:#1B1F1A;--muted:#6C7268;--line:#E5E7E0}}
*{{box-sizing:border-box}}
body{{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;color:var(--ink);background:#fff;-webkit-tap-highlight-color:transparent}}
a{{color:inherit;text-decoration:none}}
header{{background:#fff;border-bottom:1px solid var(--line);position:sticky;top:0;z-index:5}}
.bar{{max-width:980px;margin:0 auto;display:flex;align-items:center;gap:10px;padding:10px 14px}}
.bar img{{height:38px;width:auto;display:block}}
.bar .sp{{flex:1}}
.bar a.shop{{background:var(--green);color:#fff;font-weight:800;font-size:12.5px;padding:8px 13px;border-radius:10px}}
.wrap{{max-width:980px;margin:0 auto;padding:0 14px}}
.crumb{{font-size:12px;color:var(--muted);padding:12px 0 0}}
.crumb a{{text-decoration:underline}}
.top{{display:grid;gap:16px;margin:12px 0 22px}}
@media(min-width:760px){{.top{{grid-template-columns:1fr 1fr;align-items:start}}}}
.gal{{background:#fff;border:1px solid var(--line);border-radius:18px;overflow:hidden}}
.gal .hero{{width:100%;aspect-ratio:1/1;object-fit:contain;background:#fff;display:block}}
.gal .ph{{aspect-ratio:1/1;display:flex;align-items:center;justify-content:center;font-size:80px;background:var(--green3)}}
.thumbs{{display:flex;gap:6px;padding:8px;overflow-x:auto}}
.thumbs img{{width:56px;height:56px;object-fit:cover;border-radius:8px;border:1px solid var(--line);flex:0 0 auto}}
h1{{font-size:23px;line-height:1.2;margin:0 0 4px;letter-spacing:-.4px}}
.bn{{color:var(--muted);font-size:14px;margin:0 0 8px}}
.soldby{{font-size:12.5px;color:var(--muted);margin:0 0 8px}}
.soldby a{{color:var(--gold);text-decoration:underline}}
.cat{{display:inline-block;background:#FDF3DF;color:#8A5E12;font-weight:800;font-size:11.5px;padding:4px 9px;border-radius:999px;margin-bottom:8px}}
.price{{font-size:24px;font-weight:900;color:var(--gold);margin:6px 0 2px}}
.price small{{font-size:12px;color:var(--muted);font-weight:700}}
.sizes{{list-style:none;display:grid;gap:6px;margin:10px 0 0;padding:0}}
.sizes li{{display:flex;justify-content:space-between;align-items:center;background:#fff;border:1px solid var(--line);border-radius:10px;padding:9px 12px;font-size:13.5px;cursor:pointer;transition:border-color .15s,background .15s}}
.sizes li.on{{border-color:#A9741C;background:#FFFBF2;box-shadow:0 0 0 1px #A9741C inset}}
.sizes li.on span{{font-weight:800}}
.sizes b{{color:var(--gold)}}
.btn{{display:block;text-align:center;font-weight:900;font-size:15px;padding:14px;border-radius:14px;margin-top:10px}}
.solid{{background:linear-gradient(135deg,#F5C766,#E3A62E);color:#2A2210;box-shadow:0 8px 20px rgba(200,145,35,.22)}}
.line{{background:#fff;border:1.5px solid #232820;color:#232820}}
.dark{{background:#232820;color:#FFF6E2;box-shadow:0 8px 20px rgba(20,24,16,.18)}}
.specs{{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:16px 0 0;padding:0;list-style:none}}
.specs li{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:10px;font-size:12px;line-height:1.4}}
.specs b{{display:block;color:var(--gold);font-size:12.5px;margin-bottom:1px}}
.desc{{background:#fff;border:1px solid var(--line);border-radius:14px;padding:14px;font-size:13.5px;line-height:1.7;margin:16px 0 0}}
.desc h2{{font-size:14.5px;margin:0 0 6px;color:var(--ink)}}
.rel{{margin:26px auto 30px}}
.rel h2{{font-size:16px;margin:0 0 10px}}
.relgrid{{display:grid;grid-template-columns:repeat(3,1fr);gap:9px}}
.relcard{{background:#fff;border:1px solid var(--line);border-radius:12px;overflow:hidden;font-size:11.5px}}
.relcard img{{width:100%;aspect-ratio:1/1;object-fit:cover;display:block;background:var(--green3)}}
.relcard b{{display:block;padding:6px 7px 0;line-height:1.3}}
.relcard span{{display:block;padding:2px 7px 7px;color:var(--muted)}}
footer{{background:#fff;border-top:1px solid var(--line);padding:16px 14px 26px;font-size:12px;color:var(--muted);text-align:center;line-height:1.7}}
footer a{{text-decoration:underline}}
.trust{{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px}}
.trust span{{background:#FDF3DF;color:#8A5E12;font-size:11px;font-weight:800;padding:5px 9px;border-radius:999px}}
</style>
</head>
<body>
<header><div class="bar">
  <a href="../index.html"><img src="../logo.png" alt="Green Friend"></a>
  <div class="sp"></div>
  <a class="shop" href="../all-plants.html">All plants</a>
</div></header>

<main class="wrap">
  <div class="crumb"><a href="../index.html">Home</a> \u203a <a href="../index.html#plants">{cat_en}</a> \u203a {name}</div>
  <div class="top">
    {gallery}
    <div class="info">
      <span class="cat">{cat_en}</span>
      <h1>{name}</h1>
      {bn_line}
      {sold_line}
      <div class="price"><span id="priceNow">{price}</span> <small>{sizes_note}</small></div>
      <ul class="sizes">{size_rows}</ul>
      <a class="btn solid" id="addBtn" href="../index.html?add={pid}" data-add="{pid}">{add_text}</a>
      <a class="btn dark" id="buyBtn" href="../index.html?add={pid}&amp;buy=1" data-add="{pid}">Buy now \u00b7 pay on delivery</a>
      <a class="btn line" href="https://wa.me/{wa}?text={wa_text}">{wa_label}</a>
      <ul class="specs">
        <li><b>Height</b>Up to 8 ft</li>
        <li><b>Guarantee</b>100% original</li>
        <li><b>Delivery</b>2\u20133 days in Malda &amp; Murshidabad</li>
        <li><b>Payment</b>COD \u00b7 UPI \u00b7 Bank</li>
      </ul>
      <div class="trust"><span>\U0001f69a Free delivery above \u20b91000</span><span>\u2705 Replacement within 24 hours</span><span>\U0001f331 Own nursery, Malda</span></div>
    </div>
  </div>

  <section class="desc">
    <h2>About {name}</h2>
    <p>{note_html}</p>
    <p>\u09ac\u09be\u0982\u09b2\u09be\u09af\u09bc: {bn_desc}</p>
  </section>
</main>

{rel_html}

<footer>
  Green Friend \u00b7 Malda &amp; Murshidabad, West Bengal \u00b7 <a href="../index.html">Shop all plants</a> \u00b7 <a href="../photo-credits.html">Photo credits</a><br>
  Prices include all taxes. Delivery is free on orders above \u20b91000.
</footer>
<script>
(function () {{
  var rows = document.querySelectorAll('.sizes li');
  var btn = document.getElementById('addBtn');
  var buy = document.getElementById('buyBtn');
  var priceEl = document.getElementById('priceNow');
  if (!rows.length || !btn) return;
  function pick(li) {{
    for (var i = 0; i < rows.length; i++) rows[i].classList.remove('on');
    li.classList.add('on');
    var label = li.getAttribute('data-label') || '';
    var base = '../index.html?add=' + btn.getAttribute('data-add') + '&size=' + encodeURIComponent(label);
    btn.setAttribute('href', base);
    if (buy) buy.setAttribute('href', base + '&buy=1');
    if (priceEl) priceEl.textContent = li.getAttribute('data-price') || priceEl.textContent;
  }}
  for (var i = 0; i < rows.length; i++) {{
    rows[i].addEventListener('click', (function (li) {{ return function () {{ pick(li); }}; }})(rows[i]));
  }}
  pick(rows[0]);
}})();
</script>
</body>
</html>
""".format(
            title=esc(title),
            description=esc(description),
            url=esc(url),
            name=esc(name),
            og_image=('<meta property="og:image" content="%s">' % esc(main_pic)) if main_pic else "",
            ld=json.dumps(ld, ensure_ascii=False),
            bc=json.dumps(breadcrumb, ensure_ascii=False),
            cat_en=esc(cat_en),
            gallery=gallery,
            bn_line=bn_line,
            sold_line=sold_line,
            price=("%s \u2013 %s" % (money(low), money(high))) if len(prices) > 1 and high > low else money(low),
            sizes_note=("%d sizes" % len(sizes)) if sizes else "standard size",
            size_rows=size_rows,
            pid=esc(p["id"]),
            add_text="Add to cart",
            wa=WA,
            wa_text=esc(urllib.parse.quote("Hello! I would like this plant: %s" % name)),
            wa_label="\U0001f4ac Order on WhatsApp",
            note_html=esc(note or ("%s from our own nursery in Malda. Grown with care, packed safely and delivered to your door." % name)),
            bn_desc=esc(note_bn or ("%s \u2014 \u09ae\u09be\u09b2\u09a6\u09be \u0993 \u09ae\u09c1\u09b0\u09cd\u09b6\u09bf\u09a6\u09be\u09ac\u09be\u09a6\u09c7\u09b0 \u09a8\u09bf\u099c\u09c7\u09b0 \u09ac\u09be\u0997\u09be\u09a8 \u09a5\u09c7\u0995\u09c7\u0964 \u09e7\u09e6\u09e6%% \u0985\u09b0\u09bf\u099c\u09bf\u09a8\u09be\u09b2, \u09e8\u09ea \u0998\u09a3\u09cd\u099f\u09be\u09af\u09bc \u09b0\u09bf\u09aa\u09cd\u09b2\u09c7\u09b8\u09ae\u09c7\u09a8\u09cd\u099f, \u20b9\u09e7\u09e6\u09e6\u09e6+ \u0985\u09b0\u09cd\u09a1\u09be\u09b0\u09c7 \u09a1\u09c7\u09b2\u09bf\u09ad\u09be\u09b0\u09bf \u09ab\u09cd\u09b0\u09bf\u0964" % name)),
            rel_html=rel_html,
        )

        with open(os.path.join(OUT, p["_slug"] + ".html"), "w", encoding="utf-8", newline="\n") as f:
            f.write(html)

    # remove pages for plants that were deleted or switched off
    keep = set(p["_slug"] + ".html" for p in products)
    for name in os.listdir(OUT):
        if name.endswith(".html") and name not in keep:
            os.remove(os.path.join(OUT, name))

    # ------------------------------------------------------------------
    # All plants: one static page that links to every product page.
    # The homepage builds its grid with JavaScript, so Googlebot sees no
    # product links in the raw HTML; this page is the crawlable hub.
    # ------------------------------------------------------------------
    cat_order = ["\u0986\u09ae", "\u09b2\u09bf\u099a\u09c1", "\u09ab\u09c1\u09b2", "\u09ab\u09b2", "\u0994\u09b7\u09a7\u09bf", "\u09b8\u09ac\u099c\u09bf"]
    cats = [c for c in cat_order if c in by_cat] + [c for c in by_cat if c not in cat_order]
    hub_sections = []
    for cat in cats:
        cards = []
        for p in by_cat[cat]:
            pics = photos_of(p)
            sz = sizes_of(p)
            prices = [s["price"] for s in sz] or [float(p.get("price") or 0)]
            op = p.get("offer_price")
            price_txt = money(min(prices))
            if op and not sz and float(op) > 0:
                price_txt = money(op)
            cards.append(
                '<a class="card" href="product/%s.html"><span class="im">%s</span>'
                '<b>%s</b><small>%s</small><em>%s</em></a>'
                % (esc(p["_slug"]),
                   ('<img src="%s" alt="%s" loading="lazy" width="240" height="240">'
                    % (esc(thumb(pics[0])), esc(p["name"]))) if pics else "",
                   esc(p["name"]),
                   esc(p["_shop"] or "Green Friend"),
                   price_txt)
            )
        hub_sections.append(
            '<section class="cat"><h2>%s <span>%s</span></h2><div class="grid">%s</div></section>'
            % (esc(CAT_EN.get(cat, cat or "Plants")), esc(cat or ""), "".join(cards))
        )

    hub = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>All plants \u2014 mango, lychee, flowers &amp; more | Green Friend, Malda</title>
<meta name="description" content="Every plant Green Friend sells in one list: mango and lychee plants up to 8 ft, flowers, fruit and indoor plants. Prices from \u20b9, delivery across India.">
<link rel="canonical" href="__SITE__all-plants.html">
<meta name="google-site-verification" content="qR5lAltyvuzxGO6-5d3boY0GSkn2obe0kYzR9FS0jCM">
<meta name="theme-color" content="#173D25">
<style>
*{box-sizing:border-box}
body{margin:0;font-family:"Segoe UI",system-ui,-apple-system,"Noto Sans Bengali",sans-serif;color:#232820;background:#FBFAF6;line-height:1.5}
a{color:inherit;text-decoration:none}
header{position:sticky;top:0;z-index:5;background:rgba(255,255,255,.95);border-bottom:1px solid #E4E2D8;backdrop-filter:blur(10px)}
.hd{max-width:1120px;margin:0 auto;padding:12px 16px;display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.hd img{height:40px;width:auto;display:block}
.hd .t{font-weight:900;font-size:15px;margin-left:auto;color:#A9741C}
main{max-width:1120px;margin:0 auto;padding:22px 16px 40px}
h1{font-size:24px;margin:0 0 6px;letter-spacing:-.3px}
.lead{color:#6C7A66;font-size:13.5px;margin:0 0 18px}
.cat h2{font-size:17px;margin:26px 0 10px;display:flex;align-items:baseline;gap:8px}
.cat h2 span{font-size:12px;font-weight:800;color:#A9741C;background:#FDF6E7;border:1px solid #F1DFB6;border-radius:999px;padding:2px 9px}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.card{background:#fff;border:1px solid #E4E2D8;border-radius:14px;padding:10px;display:flex;flex-direction:column;gap:4px;transition:transform .12s,box-shadow .12s}
.card:hover{transform:translateY(-2px);box-shadow:0 8px 20px rgba(35,40,32,.08)}
.card .im{display:block;aspect-ratio:1;border-radius:10px;overflow:hidden;background:#F3F3EF}
.card .im img{width:100%;height:100%;object-fit:cover;display:block}
.card b{font-size:13px;line-height:1.3;margin-top:4px}
.card small{font-size:11px;color:#6C7A66}
.card em{font-style:normal;font-weight:900;color:#1F5F3E;font-size:13px;margin-top:auto}
footer{text-align:center;color:#6C7A66;font-size:12px;padding:26px 16px;border-top:1px solid #E4E2D8;margin-top:10px}
footer a{color:#A9741C;font-weight:800}
@media(max-width:820px){.grid{grid-template-columns:repeat(3,1fr)}}
@media(max-width:560px){.grid{grid-template-columns:repeat(2,1fr)}h1{font-size:20px}}
</style>
</head>
<body>
<header><div class="hd"><a href="index.html"><img src="logo.png" alt="Green Friend"></a><div class="t">__COUNT__ plants</div></div></header>
<main>
<h1>All plants</h1>
<p class="lead">Mango and lychee plants up to 8 ft, flowers, fruit, medicinal and indoor plants \u2014 from Malda &amp; Murshidabad, West Bengal.</p>
__SECTIONS__
</main>
<footer>Green Friend \u00b7 Malda &amp; Murshidabad, West Bengal \u00b7 <a href="index.html">Shop</a> \u00b7 <a href="photo-credits.html">Photo credits</a></footer>
</body>
</html>
"""
    hub = (hub.replace("__SITE__", SITE)
              .replace("__SECTIONS__", "".join(hub_sections))
              .replace("__COUNT__", str(len(products))))
    with open(os.path.join(DOCS, "all-plants.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(hub)

    # sitemap + robots
    json.dump({p["id"]: p["_slug"] for p in products},
              open(os.path.join(DOCS, "product-map.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=0)
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
          "  <url><loc>%s</loc><lastmod>%s</lastmod><changefreq>daily</changefreq><priority>1.0</priority></url>"
          % (SITE, TODAY),
          "  <url><loc>%sall-plants.html</loc><lastmod>%s</lastmod><changefreq>daily</changefreq><priority>0.9</priority></url>"
          % (SITE, TODAY)]
    for u, lm in urls:
        sm.append("  <url><loc>%s</loc><lastmod>%s</lastmod><changefreq>weekly</changefreq><priority>0.8</priority></url>" % (u, lm))
    sm.append("</urlset>")
    open(os.path.join(DOCS, "sitemap.xml"), "w", encoding="utf-8", newline="\n").write("\n".join(sm) + "\n")

    robots = "User-agent: *\nAllow: /\n\nSitemap: %ssitemap.xml\n" % SITE
    open(os.path.join(DOCS, "robots.txt"), "w", encoding="utf-8", newline="\n").write(robots)

    print("pages:", len(products), "| slugs sample:",
          ", ".join(p["_slug"] for p in products[:4]))


if __name__ == "__main__":
    main()
