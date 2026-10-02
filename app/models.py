import os, secrets
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db, login

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), unique=True, nullable=False)
    slug = db.Column(db.String(60), unique=True, nullable=False)

class Setting(db.Model):
    key = db.Column(db.String(60), primary_key=True)
    value = db.Column(db.Text, default="")

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.String(10), index=True)
    meta = db.Column(db.String(30))
    product_id = db.Column(db.Integer, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

DEFAULTS = {"store_name": "BYN Sports", "whatsapp": os.getenv("WHATSAPP_NUMBER", "555198274978"), "instagram": os.getenv("INSTAGRAM", ""),
    "address": "", "hours": "", "btn_text": "Tenho interesse — falar no WhatsApp",
    "msg_product": "Olá! Tenho interesse no produto {produto}{opcoes}, no valor de {preco}. Gostaria de saber se está disponível.",
    "msg_selection": "Gostaria de consultar estes produtos:",
    "low_stock": "3", "announce": "", "announce_link": "", "hero_eyebrow": "Esporte é estilo de vida", "hero_title": "Do seu jeito, sempre.",
    "hero_lead": "Conforto · Performance · Estilo", "hero_cta": "Ver produtos", "brand_color": "#ff5a1f", "seo_desc": "Tênis, chuteiras e roupas esportivas. Escolha e peça pelo WhatsApp.",
    "default_sort": "new", "hide_soldout": "0", "show_featured": "1", "show_promos": "1", "show_launch": "1", "show_best": "1", "show_teams": "1", "show_brands": "1", "show_recent": "1", "show_about": "1", "msg_selection_end": "Pode confirmar a disponibilidade?"}

def settings():
    from flask import g
    if "luft_s" not in g:
        d = dict(DEFAULTS); d.update({x.key: x.value for x in Setting.query.all() if x.value})
        g.luft_s = d
    return g.luft_s

class ProductImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"))
    color = db.Column(db.String(40), default="")
    filename = db.Column(db.String(200))
    position = db.Column(db.Integer, default=0)

class Variant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"))
    color = db.Column(db.String(40), default="")
    size = db.Column(db.String(20), default="")
    qty = db.Column(db.Integer, default=0)

class Notify(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, index=True)
    contact = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Brand(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    logo = db.Column(db.String(200))
    name = db.Column(db.String(60), unique=True, nullable=False)
    slug = db.Column(db.String(60), unique=True, nullable=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, default="")
    price = db.Column(db.Numeric(10, 2), nullable=False)
    image = db.Column(db.String(200))
    active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=False)
    category = db.relationship("Category")
    brand_id = db.Column(db.Integer, db.ForeignKey("brand.id"))
    brand = db.relationship("Brand")
    image2 = db.Column(db.String(200))
    sku = db.Column(db.String(60))
    team = db.Column(db.String(60))
    specs = db.Column(db.Text)
    variants = db.relationship("Variant", cascade="all, delete-orphan")
    images = db.relationship("ProductImage", cascade="all, delete-orphan")
    @property
    def color_image_objs(self):
        d = {}
        for im in sorted(self.images, key=lambda i: i.id): d.setdefault(im.color, []).append(im)
        for v in d.values(): v.sort(key=lambda i: (i.position or 0, i.id))
        return d
    @property
    def cover(self): return self.image or next((v[0].filename for v in self.color_image_objs.values() if v), None)
    sizes = db.Column(db.String(200))
    colors = db.Column(db.String(200))
    stock = db.Column(db.Integer)
    @property
    def size_list(self): return [x.strip() for x in (self.sizes or "").split(",") if x.strip()]
    @property
    def color_list(self): return [x.strip() for x in (self.colors or "").split(",") if x.strip()]
    @property
    def total_stock(self): return sum(v.qty for v in self.variants) if self.variants else self.stock
    @property
    def available(self): t = self.total_stock; return t is None or t > 0
    @property
    def spec_dict(self):
        import json
        try: return json.loads(self.specs or "{}")
        except ValueError: return {}
    @property
    def low(self):
        try: thr = int(settings().get("low_stock", 3))
        except (ValueError, TypeError): thr = 3
        t = self.total_stock; return t is not None and 0 < t <= thr
    def _u(self, attr, only_in_stock):
        vs = [v for v in self.variants if (v.qty > 0 or not only_in_stock)]
        return list(dict.fromkeys(getattr(v, attr) for v in vs if getattr(v, attr)))
    @property
    def all_sizes(self): return self._u("size", False) or self.size_list
    @property
    def all_colors(self):
        cs = self._u("color", False) or self.color_list; low = {c.lower() for c in cs}
        return cs + [c for c in self.color_image_objs if c and c.lower() not in low]
    @property
    def avail_sizes(self): return self._u("size", True) if self.variants else self.size_list
    @property
    def avail_colors(self): return self._u("color", True) if self.variants else self.color_list
    promo_price = db.Column(db.Numeric(10, 2))
    promo_active = db.Column(db.Boolean, default=False)
    featured = db.Column(db.Boolean, default=False)
    bestseller = db.Column(db.Boolean, default=False)
    launch = db.Column(db.Boolean, default=False)
    @property
    def on_sale(self): return bool(self.promo_active and self.promo_price and self.promo_price < self.price)
    @property
    def price_now(self): return self.promo_price if self.on_sale else self.price
    @property
    def discount(self): return round((1 - self.promo_price / self.price) * 100) if self.on_sale else 0
    @property
    def is_new(self): return (datetime.utcnow() - self.created_at).days < 30
    @property
    def ts(self): return int(self.created_at.timestamp())

class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(60), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    must_change = db.Column(db.Boolean, default=True)
    def set_password(self, pw): self.password_hash = generate_password_hash(pw)
    def check_password(self, pw): return check_password_hash(self.password_hash, pw)

@login.user_loader
def load_user(uid): return db.session.get(Admin, int(uid))

def migrate():
    from sqlalchemy import inspect, text
    cols = {c["name"] for c in inspect(db.engine).get_columns("product")}
    for n, d in {"brand_id": "INTEGER", "image2": "VARCHAR(200)", "sizes": "VARCHAR(200)", "colors": "VARCHAR(200)", "stock": "INTEGER", "promo_price": "NUMERIC(10,2)", "promo_active": "BOOLEAN DEFAULT 0",
                 "featured": "BOOLEAN DEFAULT 0", "bestseller": "BOOLEAN DEFAULT 0"}.items():
        if n not in cols: db.session.execute(text(f"ALTER TABLE product ADD COLUMN {n} {d}"))
    if "logo" not in {c["name"] for c in inspect(db.engine).get_columns("brand")}:
        db.session.execute(text("ALTER TABLE brand ADD COLUMN logo VARCHAR(200)"))
    if "meta" not in {c["name"] for c in inspect(db.engine).get_columns("event")}:
        db.session.execute(text("ALTER TABLE event ADD COLUMN meta VARCHAR(30)"))
    for n, d in {"launch": "BOOLEAN DEFAULT 0", "sku": "VARCHAR(60)", "team": "VARCHAR(60)", "specs": "TEXT"}.items():
        if n not in cols: db.session.execute(text(f"ALTER TABLE product ADD COLUMN {n} {d}"))
    db.session.commit()

def seed(app):
    migrate()
    if not Brand.query.count():
        for n in ["Nike", "Adidas", "Puma", "Lacoste"]: db.session.add(Brand(name=n, slug=n.lower()))
    for n, sl in [("Camisas de Times", "camisas"), ("Agasalhos de Times", "agasalhos"), ("Tênis Esportivo", "tenis-esportivo"), ("Tênis Casual", "tenis-casual"),
                  ("Chuteiras Society", "chuteiras-society"), ("Chuteiras Futsal", "chuteiras-futsal"), ("Chuteiras Campo", "chuteiras-campo"), ("Chuteiras Usadas", "chuteiras-usadas")]:
        if not Category.query.filter_by(slug=sl).first(): db.session.add(Category(name=n, slug=sl))
    if not Admin.query.count():
        pw = os.getenv("ADMIN_PASSWORD") or secrets.token_urlsafe(9)
        a = Admin(username=os.getenv("ADMIN_USER", "admin")); a.set_password(pw)
        db.session.add(a)
        print(f"\n=== ACESSO ADMIN INICIAL === usuário: {a.username} | senha: {pw} (troca obrigatória no 1º login)\n")
    db.session.commit()
