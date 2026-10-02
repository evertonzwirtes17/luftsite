import os, re, time, uuid, unicodedata
from decimal import Decimal, InvalidOperation
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from . import db
from datetime import datetime, timedelta
from collections import Counter
from .models import ProductImage, Notify, Variant, Admin, Product, Category, Brand, Event, Setting, settings, DEFAULTS

bp = Blueprint("admin", __name__)
FAILS = {}  # tentativas de login por IP (proteção contra tentativa e erro)
EXT = {"jpg", "jpeg", "png", "webp"}
KINDS = {"categorias": (Category, "Categorias"), "marcas": (Brand, "Marcas")}

@bp.before_request
def force_password_change():
    if current_user.is_authenticated and current_user.must_change and request.endpoint not in ("admin.password", "admin.logout"):
        return redirect(url_for("admin.password"))

@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        ip, now = request.remote_addr or "?", time.time(); n, t0 = FAILS.get(ip, (0, now))
        if now - t0 > 300: n, t0 = 0, now
        if n >= 5: flash("Muitas tentativas de acesso. Aguarde alguns minutos e tente de novo."); return render_template("admin/login.html")
        u = Admin.query.filter_by(username=request.form.get("username", "").strip()).first()
        if u and u.check_password(request.form.get("password", "")):
            FAILS.pop(ip, None); login_user(u); return redirect(url_for("admin.dashboard"))
        FAILS[ip] = (n + 1, t0); flash("Usuário ou senha inválidos.")
    return render_template("admin/login.html")

@bp.route("/logout")
def logout():
    logout_user(); return redirect(url_for("admin.login"))

@bp.route("/senha", methods=["GET", "POST"])
@login_required
def password():
    if request.method == "POST":
        new = request.form.get("new", "")
        if not current_user.check_password(request.form.get("current", "")): flash("Senha atual incorreta.")
        elif len(new) < 10: flash("A nova senha deve ter ao menos 10 caracteres.")
        elif new != request.form.get("confirm"): flash("As senhas não coincidem.")
        else:
            current_user.set_password(new); current_user.must_change = False; db.session.commit()
            flash("Senha alterada com sucesso."); return redirect(url_for("admin.dashboard"))
    return render_template("admin/password.html")

@bp.route("/")
@login_required
def dashboard():
    ps = Product.query.all()
    now = datetime.utcnow(); since = now - timedelta(days=6)
    evs = Event.query.filter(Event.created_at >= since.replace(hour=0, minute=0, second=0)).all()
    allv, allw = {}, {}
    for k, pid, n in db.session.query(Event.kind, Event.product_id, db.func.count()).group_by(Event.kind, Event.product_id):
        if k == "view": allv[pid] = n
        elif k == "wa": allw[pid] = n
    days = []
    for i in range(6, -1, -1):
        d = (now - timedelta(days=i)).date()
        days.append({"label": d.strftime("%d/%m"), "v": sum(e.kind == "view" and e.created_at.date() == d for e in evs), "w": sum(e.kind == "wa" and e.created_at.date() == d for e in evs)})
    top = lambda m: [(p, m[p.id]) for p in sorted(ps, key=lambda p: -m.get(p.id, 0)) if m.get(p.id)][:5]
    sels, sizes, hrs = Counter(), Counter(), Counter()
    pm = {p.id: p for p in ps}
    for e in Event.query.all():
        hrs[(e.created_at - timedelta(hours=3)).hour] += 1
        if e.kind == "sel": sels[e.product_id] += 1; sizes[e.meta] += bool(e.meta)
    catv = Counter()
    for pid, n in allv.items():
        if pid in pm: catv[pm[pid].category.name] += n
    extra = {"sels": [(pm[i].name, n) for i, n in sels.most_common(5) if i in pm], "sizes": sizes.most_common(5), "cats": catv.most_common(5),
             "hours": [(f"{h:02d}h", n) for h, n in hrs.most_common(3)], "low": [p for p in ps if p.low or not p.available][:6]}
    today = (now - timedelta(hours=3)).date(); td = [e for e in evs if (e.created_at - timedelta(hours=3)).date() == today]
    hoje = [("Visualizações hoje", sum(e.kind == "view" for e in td)), ("Cliques no WhatsApp hoje", sum(e.kind == "wa" for e in td)),
            ("Adicionados à seleção hoje", sum(e.kind == "sel" for e in td)), ("Produtos com estoque baixo", sum(p.low for p in ps))]
    tv = Counter(e.product_id for e in td if e.kind == "view").most_common(1)
    extra["hot"] = pm[tv[0][0]].name if tv and tv[0][0] in pm else None
    try: thr = int(settings().get("low_stock", 3))
    except (ValueError, TypeError): thr = 3
    extra["alerts"] = [(p.name, v.color, v.size, v.qty) for p in ps for v in p.variants if v.qty <= thr][:8]
    extra["hoje"] = hoje
    att = []
    for p in ps:
        if not p.cover: att.append((p, "sem imagem"))
        if group(p.category.slug) and not p.variants and not p.sizes: att.append((p, "sem tamanho/numeração"))
        if p.active and p.total_stock is None: att.append((p, "estoque não informado"))
    extra["att"] = att[:10]; extra["avisos"] = Notify.query.count()
    stats = [("Produtos cadastrados", len(ps)), ("Produtos ativos", sum(p.active for p in ps)), ("Em promoção", sum(p.on_sale for p in ps)),
             ("Disponíveis", sum(p.active and p.available for p in ps)), ("Indisponíveis", sum(p.active and not p.available for p in ps)), ("Estoque baixo", sum(p.low for p in ps)),
             ("Visualizações", sum(allv.values())), ("Cliques no WhatsApp", sum(allw.values())), ("Categorias / Marcas", f"{Category.query.count()} / {Brand.query.count()}")]
    return render_template("admin/dashboard.html", stats=stats, days=days, mx=max([d["v"] for d in days] + [d["w"] for d in days] + [1]),
                           top_v=top(allv), top_w=top(allw), x=extra, idle=[p for p in ps if p.active and not allv.get(p.id)][:5])

@bp.route("/produtos")
@login_required
def products():
    f = request.args.get("f")
    ps = Product.query.order_by(Product.created_at.desc()).all()
    if f == "promo": ps = [p for p in ps if p.on_sale]
    return render_template("admin/products.html", products=ps, f=f)

def save_image(f):
    ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
    if ext not in EXT: return None
    d = current_app.config["UPLOAD_DIR"]; base = uuid.uuid4().hex
    try:
        from PIL import Image, ImageOps
        im = ImageOps.exif_transpose(Image.open(f)); im.thumbnail((1400, 1400))
        alpha = im.mode in ("RGBA", "LA") or "transparency" in im.info
        name = base + (".webp" if alpha else ".jpg")
        (im if alpha else im.convert("RGB")).save(os.path.join(d, name), "WEBP" if alpha else "JPEG", quality=84)
        return name
    except ImportError:
        f.stream.seek(0); name = f"{base}.{ext}"; f.save(os.path.join(d, secure_filename(name))); return name
    except Exception:
        return None  # arquivo não é uma imagem válida

def money(v):
    return Decimal(v.replace(",", ".")) if v.strip() else None

SPECS = {"camisas": ["Temporada", "Modelo", "Manga"], "agasalhos": ["Modelo", "Peça"], "tenis": ["Modelo", "Tipo"], "chuteiras": ["Modelo", "Solado"]}
def group(slug):
    return next((g for g in SPECS if slug.startswith(g)), None)

def sync_color_images(p):
    bad = 0; f = request.form; by_id = {str(i.id): i for i in p.images}; out = []
    for i in sorted({k.split("_")[1] for k in f if k.startswith("cname_")}, key=int):
        name = f.get(f"cname_{i}", "").strip()[:40]
        if not name: continue
        ids = [x for x in f.getlist(f"cold_{i}") if x in by_id]; main = f.get(f"cmain_{i}")
        if main in ids: ids.remove(main); ids.insert(0, main)
        grp = [by_id[x] for x in ids]
        for up in request.files.getlist(f"cfiles_{i}"):
            if up and up.filename:
                n = save_image(up)
                if n: grp.append(ProductImage(filename=n))
                else: bad += 1
        for pos, im in enumerate(grp): im.color, im.position = name, pos; out.append(im)
    if bad: flash(f"⚠ {bad} imagem(ns) inválida(s) foram ignoradas. Use JPG, PNG ou WEBP.")
    p.images = out

def fill(p):
    f = request.form
    try: p.price, p.promo_price = money(f["price"]), money(f.get("promo_price", ""))
    except (InvalidOperation, KeyError): flash("Preço inválido."); return False
    if p.price is None or p.price <= 0: flash("Informe um preço maior que zero."); return False
    if p.promo_price is not None and p.promo_price <= 0: flash("O preço promocional deve ser maior que zero."); return False
    p.name, p.description = f["name"].strip(), f.get("description", "").strip()
    p.category_id, p.brand_id = int(f["category_id"]), int(f["brand_id"]) if f.get("brand_id") else None
    if "sku" in f: p.sku = f.get("sku", "").strip()[:60]
    p.team = f.get("team", "").strip()[:60]
    if f.get("vt"):  # tabela de estoque por cor/tamanho
        agg = {}
        for c, sz, q in zip(f.getlist("v_color"), f.getlist("v_size"), f.getlist("v_qty")):
            c, sz, q = c.strip()[:40], sz.strip()[:20], q.strip()
            if not (c or sz or q): continue
            k = (c.lower(), sz.lower()); qn = int(q) if q.isdigit() else 0
            agg[k] = (c, sz, agg.get(k, (0, 0, 0))[2] + qn)
        p.variants = [Variant(color=c, size=sz, qty=min(q, 100000)) for c, sz, q in agg.values()]
    p.launch = "launch" in f
    p.active, p.featured, p.bestseller, p.promo_active = ("active" in f), ("featured" in f), ("bestseller" in f), ("promo_active" in f)
    if p.promo_active and not (p.promo_price and p.promo_price < p.price): flash("O preço promocional deve ser menor que o preço original."); return False
    img = request.files.get("image")
    if img and img.filename:
        n = save_image(img)
        if not n: flash("Formato de imagem inválido (use JPG, PNG ou WEBP)."); return False
        p.image = n
    img2 = request.files.get("image2")
    if img2 and img2.filename:
        n2 = save_image(img2)
        if n2: p.image2 = n2
    sync_color_images(p)
    return bool(p.name)

@bp.route("/novo", methods=["GET", "POST"])
@bp.route("/<int:pid>/editar", methods=["GET", "POST"])
@login_required
def edit(pid=None):
    p = db.get_or_404(Product, pid) if pid else Product()
    if request.method == "POST" and fill(p):
        db.session.add(p); db.session.commit(); flash("Produto salvo.")
        return redirect(url_for("admin.products"))
    return render_template("admin/form.html", p=p, categories=Category.query.all(), brands=Brand.query.order_by(Brand.name).all())

@bp.post("/<int:pid>/excluir")
@login_required
def delete(pid):
    db.session.delete(db.get_or_404(Product, pid)); db.session.commit()
    return redirect(url_for("admin.products"))

@bp.post("/<int:pid>/ativar")
@login_required
def toggle(pid):
    p = db.get_or_404(Product, pid); p.active = not p.active; db.session.commit()
    return redirect(url_for("admin.products"))

@bp.route("/cadastros/<kind>", methods=["GET", "POST"])
@login_required
def registry(kind):
    M, title = KINDS.get(kind) or (None, None)
    if not M: return redirect(url_for("admin.dashboard"))
    if request.method == "POST":
        n = request.form.get("name", "").strip()[:60]
        slug = re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode().lower()).strip("-") or "item-" + uuid.uuid4().hex[:6]
        if not n: flash("Digite um nome.")
        elif M.query.filter((db.func.lower(M.name) == n.lower()) | (M.slug == slug)).first(): flash(f"“{n}” já está cadastrada.")
        else:
            it = M(name=n, slug=slug); img = request.files.get("logo")
            if M is Brand and img and img.filename: it.logo = save_image(img)
            db.session.add(it); db.session.commit(); flash(f"✓ “{n}” adicionada.")
        return redirect(url_for("admin.registry", kind=kind))
    items = M.query.order_by(M.name).all(); fld = "category_id" if M is Category else "brand_id"
    return render_template("admin/registry.html", items=items, kind=kind, title=title, usage={i.id: Product.query.filter_by(**{fld: i.id}).count() for i in items})

@bp.post("/cadastros/<kind>/<int:iid>/excluir")
@login_required
def registry_delete(kind, iid):
    M = KINDS[kind][0]; it = db.get_or_404(M, iid)
    used = Product.query.filter_by(**{("category_id" if M is Category else "brand_id"): iid}).count()
    if used: flash(f"Não é possível excluir: {used} produto(s) usam este item.")
    else: db.session.delete(it); db.session.commit()
    return redirect(url_for("admin.registry", kind=kind))

@bp.post("/massa")
@login_required
def bulk():
    ids, a = request.form.getlist("ids", type=int), request.form.get("action")
    ps = Product.query.filter(Product.id.in_(ids)).all() if ids else []
    for p in ps:
        if a == "ativar": p.active = True
        elif a == "desativar": p.active = False
        elif a == "destaque": p.featured = True
        elif a == "sem_destaque": p.featured = False
        elif a == "lancamento": p.launch = True
        elif a == "sem_lancamento": p.launch = False
    db.session.commit(); flash(f"✓ {len(ps)} produto(s) atualizado(s)" if ps else "Selecione ao menos um produto.")
    return redirect(url_for("admin.products"))

@bp.post("/<int:pid>/duplicar")
@login_required
def duplicate(pid):
    o = db.get_or_404(Product, pid)
    n = Product(name=o.name + " (cópia)", description=o.description, price=o.price, promo_price=o.promo_price, promo_active=False, image=o.image, image2=o.image2,
                sizes=o.sizes, colors=o.colors, stock=o.stock, team=o.team, specs=o.specs, category_id=o.category_id, brand_id=o.brand_id, active=False,
                variants=[Variant(color=v.color, size=v.size, qty=v.qty) for v in o.variants],
                images=[ProductImage(color=i.color, filename=i.filename, position=i.position) for i in o.images])
    db.session.add(n); db.session.commit(); flash("✓ Produto duplicado. Ajuste os dados e ative quando estiver pronto.")
    return redirect(url_for("admin.edit", pid=n.id))

@bp.route("/avisos")
@login_required
def notices():
    pm = {p.id: p.name for p in Product.query.all()}
    return render_template("admin/avisos.html", items=Notify.query.order_by(Notify.created_at.desc()).all(), pm=pm)

@bp.post("/avisos/<int:nid>/excluir")
@login_required
def notice_delete(nid):
    db.session.delete(db.get_or_404(Notify, nid)); db.session.commit()
    return redirect(url_for("admin.notices"))

CFG = [("Loja", [("store_name", "Nome da loja", "text"), ("address", "Endereço (aparece no rodapé)", "text"), ("hours", "Horário de atendimento (aparece no rodapé)", "text"), ("instagram", "Instagram (usuário, sem @)", "text")]),
 ("WhatsApp", [("whatsapp", "Número (DDI + DDD, só números)", "text"), ("btn_text", "Texto do botão de WhatsApp", "text"), ("msg_product", "Mensagem do produto — use {produto}, {preco} e {opcoes}", "area"), ("msg_selection", "Mensagem da seleção — introdução", "area"), ("msg_selection_end", "Mensagem da seleção — frase final", "area")]),
 ("Aparência", [("brand_color", "Cor principal da loja", "color"), ("announce", "Barra de aviso no topo (vazio = oculta)", "text"), ("announce_link", "Link da barra de aviso (opcional, começa com http ou /)", "text"), ("seo_desc", "Descrição para buscadores (SEO)", "area")]),
 ("Página inicial", [("hero_eyebrow", "Topo: frase pequena", "text"), ("hero_title", "Topo: título", "text"), ("hero_lead", "Topo: subtítulo", "text"), ("hero_cta", "Topo: texto do botão", "text"),
   ("show_featured", "Mostrar Produtos em destaque", "check"), ("show_promos", "Mostrar Promoções", "check"), ("show_launch", "Mostrar Lançamentos", "check"), ("show_best", "Mostrar Mais vendidos", "check"),
   ("show_teams", "Mostrar Vista seu time", "check"), ("show_brands", "Mostrar Marcas", "check"), ("show_recent", "Mostrar Vistos recentemente", "check"), ("show_about", "Mostrar seção institucional", "check")]),
 ("Catálogo e estoque", [("default_sort", "Ordem inicial do catálogo", "sort"), ("hide_soldout", "Ocultar produtos esgotados da loja", "check"), ("low_stock", "Alertar estoque baixo a partir de (unidades)", "number")])]

@bp.route("/config", methods=["GET", "POST"])
@login_required
def config():
    if request.method == "POST":
        for _, fs in CFG:
            for k, _, t in fs:
                v = ("1" if k in request.form else "0") if t == "check" else request.form.get(k, "").strip()
                if k == "whatsapp": v = "".join(c for c in v if c.isdigit())
                if t == "color" and not re.fullmatch(r"#[0-9a-fA-F]{6}", v): v = DEFAULTS[k]
                if t == "number" and not v.isdigit(): v = DEFAULTS[k]
                row = db.session.get(Setting, k) or Setting(key=k); row.value = v; db.session.add(row)
        db.session.commit(); flash("✓ Configurações salvas. Já estão valendo na loja.")
        return redirect(url_for("admin.config"))
    return render_template("admin/config.html", s=settings(), groups=CFG)
