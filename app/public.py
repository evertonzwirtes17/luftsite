from flask import Blueprint, render_template
import json
from flask import abort, request, jsonify, current_app, url_for
from . import csrf, db
from .models import settings, Product, Category, Brand, Event, Notify

bp = Blueprint("public", __name__)

@bp.route("/")
def index():
    ps = Product.query.filter_by(active=True).order_by(Product.created_at.desc()).all()
    if settings().get("hide_soldout") == "1": ps = [p for p in ps if p.available]
    counts = {}
    for p in ps:
        if p.brand_id: counts[p.brand_id] = counts.get(p.brand_id, 0) + 1
    covers = {}
    for p in ps:
        if p.cover and p.category_id not in covers: covers[p.category_id] = p.cover
    def cover(g):
        return next((p.cover for p in ps if p.cover and p.category.slug == g), None)
    DESC = {"camisas": "Vista as cores do seu time.", "agasalhos": "Seu time também no seu estilo.", "tenis-esportivo": "Performance para cada treino e cada corrida.", "tenis-casual": "Conforto e estilo para o dia a dia.",
            "chuteiras-society": "Controle total na grama sintética.", "chuteiras-futsal": "Agilidade e precisão na quadra.", "chuteiras-campo": "Tração e firmeza no gramado.", "chuteiras-usadas": "Chuteiras seminovas com preço especial."}
    used = {p.category_id for p in ps}
    slides = [{"t": c.name, "s": DESC.get(c.slug, "Confira os produtos desta categoria."), "f": c.slug, "img": cover(c.slug)} for c in Category.query.all() if c.id in used][:8]
    teams = sorted({p.team for p in ps if p.team})
    return render_template("index.html", teams=teams, slides=slides, counts=counts, covers=covers, products=ps, categories=Category.query.all(), brands=Brand.query.order_by(Brand.name).all(),
        featured=[p for p in ps if p.featured][:12], promos=[p for p in ps if p.on_sale][:12],
        news=[p for p in ps if p.is_new][:12], best=[p for p in ps if p.bestseller][:12])


@bp.route("/produto/<int:pid>")
def product(pid):
    p = db.get_or_404(Product, pid)
    if not p.active: abort(404)
    db.session.add(Event(kind="view", product_id=pid)); db.session.commit()
    up = lambda n: url_for("static", filename="uploads/" + n)
    general = [up(i) for i in (p.image, p.image2) if i]
    colors = {c: [up(i.filename) for i in v] for c, v in p.color_image_objs.items() if c}
    if not general: general = [v[0] for v in colors.values() if v]
    gal = json.dumps({"general": general, "colors": colors}).replace("</", "<\\/")
    rel = [r for r in Product.query.filter(Product.active == True, Product.category_id == p.category_id, Product.id != pid).all() if r.available][:4]
    vj = json.dumps([{"c": v.color, "s": v.size, "q": v.qty} for v in p.variants]).replace("</", "<\\/")
    return render_template("product.html", vars_json=vj, gal_json=gal, first=general[0] if general else "", p=p, related=rel)

@bp.post("/t/<kind>/<int:pid>")
@csrf.exempt
def track(kind, pid):
    if kind in ("wa", "sel"):
        db.session.add(Event(kind=kind, product_id=pid, meta=request.args.get("m", "")[:30])); db.session.commit()
    return ("", 204)

def listing(title, items, sub=""):
    return render_template("lista.html", title=title, sub=sub, items=[p for p in items if p.active])

@bp.route("/ofertas")
def offers(): return listing("Ofertas", Product.query.all() and [p for p in Product.query.all() if p.on_sale], "Produtos com preço promocional. Entram e saem daqui automaticamente.")

@bp.route("/lancamentos")
def launches(): return listing("Lançamentos", [p for p in Product.query.order_by(Product.created_at.desc()).all() if p.launch], "As novidades da loja.")

@bp.route("/futebol")
def football():
    return listing("Futebol", [p for p in Product.query.order_by(Product.created_at.desc()).all() if p.category.slug.startswith(("camisas", "agasalhos", "chuteiras"))], "Camisas, agasalhos e chuteiras.")

@bp.route("/time/<nome>")
def team(nome):
    return listing("Coleção " + nome, [p for p in Product.query.order_by(Product.created_at.desc()).all() if (p.team or "").lower() == nome.lower()], "Tudo do seu time em um só lugar.")

@bp.post("/avise/<int:pid>")
@csrf.exempt
def notify(pid):
    c = request.form.get("contact", "").strip()[:80]
    if len(c) < 5 or not db.session.get(Product, pid): return ("", 400)
    db.session.add(Notify(product_id=pid, contact=c)); db.session.commit()
    return ("", 204)

@bp.route("/api/produtos")
def api_products():
    ids = [int(x) for x in request.args.get("ids", "").split(",") if x.strip().isdigit()][:40]
    brl = current_app.jinja_env.filters["brl"]; out = {}
    for p in (Product.query.filter(Product.id.in_(ids), Product.active == True).all() if ids else []):
        out[str(p.id)] = {"name": p.name, "price": brl(p.price_now), "href": url_for("public.product", pid=p.id),
                          "img": url_for("static", filename="uploads/" + p.cover) if p.cover else "", "val": float(p.price_now), "avail": p.available, "stock": p.stock,
                          "variants": [{"c": v.color, "s": v.size, "q": v.qty} for v in p.variants]}
    return jsonify(out)
