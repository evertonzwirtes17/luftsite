import os, secrets, datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf import CSRFProtect

db, login, csrf = SQLAlchemy(), LoginManager(), CSRFProtect()
login.login_view = "admin.login"

def _secret(base):
    if os.getenv("SECRET_KEY"): return os.environ["SECRET_KEY"]
    p = os.path.join(base, "..", "secret.key")
    try:
        if os.path.exists(p): return open(p).read().strip()
        k = secrets.token_hex(32); open(p, "w").write(k); return k
    except OSError: return secrets.token_hex(32)

def create_app():
    app = Flask(__name__)
    base = os.path.abspath(os.path.dirname(__file__))
    app.config.update(
        SECRET_KEY=_secret(base), SEND_FILE_MAX_AGE_DEFAULT=604800,
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "sqlite:///" + os.path.join(base, "..", "luft.db")),
        UPLOAD_DIR=os.path.join(base, "static", "uploads"),
        MAX_CONTENT_LENGTH=5 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
        WHATSAPP=os.getenv("WHATSAPP_NUMBER", "555198274978"),
        INSTAGRAM=os.getenv("INSTAGRAM", ""),
    )
    db.init_app(app); login.init_app(app); csrf.init_app(app)
    from .models import seed
    from .public import bp as public
    from .admin import bp as admin
    app.register_blueprint(public); app.register_blueprint(admin, url_prefix="/admin")

    @app.template_filter("brl")
    def brl(v):
        return "R$ " + f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @app.template_filter("wa")
    def wa(p):
        from urllib.parse import quote
        from .models import settings
        st = settings()
        msg = st["msg_product"].replace("{produto}", p.name).replace("{preco}", brl(p.price_now)).replace("{opcoes}", "")
        return f"https://wa.me/{st['whatsapp']}?text={quote(msg)}"

    @app.errorhandler(413)
    def too_big(e):
        from flask import flash, redirect, request
        flash("Arquivo muito grande. O limite é 5 MB por envio."); return redirect(request.referrer or "/admin/")

    @app.cli.command("reset-admin")
    def reset_admin():
        """Gera uma nova senha temporária para o administrador (troca obrigatória no próximo acesso)."""
        from .models import Admin
        a = Admin.query.first() or Admin(username="admin"); pw = secrets.token_urlsafe(9)
        a.set_password(pw); a.must_change = True; db.session.add(a); db.session.commit()
        print(f"\nUsuário: {a.username}\nNova senha temporária: {pw}\n(será pedida uma senha nova no próximo acesso)\n")

    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template
        return render_template("404.html"), 404

    @app.context_processor
    def inject():
        from flask import url_for
        def asset(p):
            try: v = int(os.path.getmtime(os.path.join(base, "static", p)))
            except OSError: v = 0
            return url_for("static", filename=p) + f"?v={v}"
        inject.asset = asset
        from .models import settings
        from .models import Category
        return {"S": settings(), "asset": inject.asset, "all_categories": Category.query.all(), "year": datetime.date.today().year}

    with app.app_context():
        db.create_all(); seed(app)
    return app
