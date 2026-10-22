import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import inspect, text, or_

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-before-deploying")
db_url = (os.environ.get("DATABASE_URL") or "sqlite:///ice_nice.db").strip()
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

TOP_COUNTRIES = [
    ("🇺🇸", "ایالات متحده آمریکا"),
    ("🇷🇺", "فدراسیون روسیه"),
    ("🇨🇳", "جمهوری خلق چین"),
    ("🇮🇳", "جمهوری هند"),
    ("🇬🇧", "پادشاهی متحد بریتانیای کبیر و ایرلند شمالی"),
    ("🇫🇷", "جمهوری فرانسه"),
    ("🇯🇵", "ژاپن"),
    ("🇰🇷", "جمهوری کره جنوبی"),
    ("🇹🇷", "جمهوری ترکیه"),
    ("🇮🇷", "جمهوری اسلامی ایران"),
    ("🇸🇦", "پادشاهی عربستان سعودی"),
    ("🇮🇱", "اسرائیل"),
    ("🇵🇰", "جمهوری اسلامی پاکستان"),
    ("🇮🇹", "جمهوری ایتالیا"),
    ("🇩🇪", "جمهوری فدرال آلمان"),
    ("🇦🇪", "امارات متحده عربی"),
    ("🇪🇬", "جمهوری عربی مصر"),
    ("🇧🇷", "جمهوری فدراتیو برزیل"),
    ("🇦🇺", "قلمرو همسود استرالیا"),
    ("🇨🇦", "کانادا"),
]
ORGANIZATIONS = [
    ("🏴", "حزب‌الله"), ("🏴", "حماس"), ("🏴", "حوثی‌ها"),
    ("🏴", "طالبان"), ("🛡️", "سپاه پاسداران انقلاب اسلامی"),
    ("🇺🇸", "سنتکام"), ("🏴", "گروه واگنر"), ("🇮🇱", "موساد"), ("🏴", "هندالا"),
]
OTHER_COUNTRIES = [
    ("🇵🇱", "لهستان"), ("🇪🇸", "پادشاهی اسپانیا"), ("🇳🇱", "پادشاهی هلند"),
    ("🇧🇪", "پادشاهی بلژیک"), ("🇬🇷", "جمهوری یونان"), ("🇺🇦", "اوکراین"),
    ("🇳🇴", "پادشاهی نروژ"), ("🇸🇪", "پادشاهی سوئد"), ("🇫🇮", "جمهوری فنلاند"),
    ("🇩🇰", "پادشاهی دانمارک"), ("🇵🇹", "جمهوری پرتغال"), ("🇷🇴", "رومانی"),
    ("🇰🇵", "جمهوری دموکراتیک خلق کره"), ("🇿🇦", "جمهوری آفریقای جنوبی"),
    ("🇻🇪", "ونزوئلا"), ("🇱🇧", "لبنان"), ("🇮🇩", "اندونزی"), ("🇨🇭", "سوئیس"),
    ("🇦🇹", "اتریش"), ("🇮🇪", "ایرلند"), ("🇳🇿", "نیوزیلند"), ("🇲🇽", "مکزیک"),
    ("🇦🇷", "آرژانتین"), ("🇨🇴", "کلمبیا"), ("🇨🇺", "کوبا"), ("🇰🇿", "قزاقستان"),
    ("🇦🇿", "جمهوری آذربایجان"), ("🇲🇦", "مراکش"), ("🇩🇿", "الجزایر"),
    ("🇮🇶", "جمهوری عراق"), ("🇶🇦", "قطر"), ("🇰🇼", "کویت"), ("🇴🇲", "عمان"),
]
FLAG_BY_NAME = {name: flag for flag, name in TOP_COUNTRIES + ORGANIZATIONS + OTHER_COUNTRIES}
ALIASES = {
    "ایالات متحده": "ایالات متحده آمریکا", "روسیه": "فدراسیون روسیه", "چین": "جمهوری خلق چین",
    "هند": "جمهوری هند", "بریتانیا": "پادشاهی متحد بریتانیای کبیر و ایرلند شمالی",
    "فرانسه": "جمهوری فرانسه", "کره جنوبی": "جمهوری کره جنوبی", "ترکیه": "جمهوری ترکیه",
    "ایران": "جمهوری اسلامی ایران", "عربستان سعودی": "پادشاهی عربستان سعودی", "پاکستان": "جمهوری اسلامی پاکستان",
    "ایتالیا": "جمهوری ایتالیا", "آلمان": "جمهوری فدرال آلمان", "امارات": "امارات متحده عربی",
    "مصر": "جمهوری عربی مصر", "برزیل": "جمهوری فدراتیو برزیل", "استرالیا": "قلمرو همسود استرالیا",
    "اسپانیا": "پادشاهی اسپانیا", "هلند": "پادشاهی هلند", "بلژیک": "پادشاهی بلژیک",
    "یونان": "جمهوری یونان", "کره شمالی": "جمهوری دموکراتیک خلق کره", "آفریقای جنوبی": "جمهوری آفریقای جنوبی",
    "عراق": "جمهوری عراق", "مکزیک": "مکزیک", "نیوزیلند": "نیوزیلند", "لهستان": "لهستان",
}

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(10), default="player", nullable=False)
    country_id = db.Column(db.Integer, db.ForeignKey("country.id"), nullable=True)
    balance = db.Column(db.Integer, default=0, nullable=False)
    badges = db.Column(db.String(500), default="", nullable=False)
    country = db.relationship("Country", foreign_keys=[country_id])

class Country(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    color = db.Column(db.String(20), default="#718096", nullable=False)
    status = db.Column(db.String(30), default="آزاد 🟢", nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    flag = db.Column(db.String(16), default="🏳️", nullable=False)
    category = db.Column(db.String(20), default="country", nullable=False)
    superpower_rank = db.Column(db.Integer, nullable=True)

class News(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    body = db.Column(db.Text, nullable=False)
    target = db.Column(db.String(40), default="همه کشورها", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class DiplomaticRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    kind = db.Column(db.String(60), nullable=False)
    details = db.Column(db.Text, default="", nullable=False)
    status = db.Column(db.String(30), default="در انتظار بررسی", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    target_country_id = db.Column(db.Integer, db.ForeignKey("country.id"), nullable=True)
    trade_details = db.Column(db.Text, default="", nullable=False)
    sender = db.relationship("User", backref="diplomatic_requests")
    target_country = db.relationship("Country", foreign_keys=[target_country_id])

class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    item = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class ShopItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    price = db.Column(db.Integer, nullable=False, default=0)
    description = db.Column(db.String(300), default="", nullable=False)

class AppSetting(db.Model):
    key = db.Column(db.String(80), primary_key=True)
    value = db.Column(db.String(200), nullable=False)

class RegisterForm(FlaskForm):
    username = StringField("نام کاربری", validators=[DataRequired(), Length(min=3, max=40)])
    password = PasswordField("گذرواژه", validators=[DataRequired(), Length(min=8, max=128)])
    country = SelectField("کشور یا گروه", coerce=int, validators=[DataRequired()])
    submit = SubmitField("ساخت حساب")

class LoginForm(FlaskForm):
    username = StringField("نام کاربری", validators=[DataRequired()])
    password = PasswordField("گذرواژه", validators=[DataRequired()])
    submit = SubmitField("ورود")

class NewsForm(FlaskForm):
    title = StringField("عنوان خبر", validators=[DataRequired(), Length(max=160)])
    body = TextAreaField("متن خبر", validators=[DataRequired(), Length(max=10000)])
    target = SelectField("مخاطب", choices=[("همه کشورها","همه بازیکنان"),("ناتو","ناتو"),("بریکس","بریکس"),("بی‌طرف","بی‌طرف")])
    submit = SubmitField("انتشار خبر")

class DiplomacyForm(FlaskForm):
    kind = SelectField("نوع درخواست", choices=[("مذاکره","مذاکره"),("معامله تجاری","معامله تجاری"),("پیمان عدم تجاوز","پیمان عدم تجاوز"),("همکاری اقتصادی","همکاری اقتصادی"),("آتش‌بس","آتش‌بس"),("اتحاد","پیشنهاد اتحاد")])
    target_country = SelectField("کشور یا گروه مقابل", coerce=int, validators=[DataRequired()])
    trade_details = TextAreaField("جزئیات معامله تجاری", validators=[Length(max=3000)])
    details = TextAreaField("جزئیات پیشنهاد", validators=[Length(max=3000)])
    submit = SubmitField("ارسال پیشنهاد دیپلماتیک")

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def admin_required():
    if not current_user.is_authenticated or current_user.role != "admin":
        abort(403)

@app.context_processor
def inject_globals():
    country = db.session.get(Country, current_user.country_id) if current_user.is_authenticated and current_user.country_id else None
    return {"site_name": "ICE Nice", "my_country": country}

@app.route("/")
def index():
    latest_news = News.query.order_by(News.created_at.desc()).limit(5).all()
    top20 = Country.query.filter(Country.superpower_rank.isnot(None)).order_by(Country.superpower_rank).all()
    return render_template("index.html", news=latest_news, top20=top20, countries_count=Country.query.filter_by(category="country").count(), organizations_count=Country.query.filter_by(category="organization").count())

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("admin" if current_user.role == "admin" else "dashboard"))
    form = RegisterForm()
    form.country.choices = [(c.id, f"{c.flag} {c.name}") for c in Country.query.filter_by(category="country", owner_id=None).order_by(Country.name).all()]
    form.country.choices += [(c.id, f"{c.flag} {c.name} (گروه/سازمان)") for c in Country.query.filter_by(category="organization", owner_id=None).order_by(Country.name).all()]
    if form.validate_on_submit():
        username = form.username.data.strip()
        chosen = db.session.get(Country, form.country.data)
        if User.query.filter_by(username=username).first():
            flash("این نام کاربری قبلاً ثبت شده است.", "error")
        elif not chosen or chosen.owner_id is not None:
            flash("این کشور یا گروه دیگر آزاد نیست.", "error")
        else:
            user = User(username=username, password_hash=generate_password_hash(form.password.data), role="player", country_id=chosen.id, balance=0)
            db.session.add(user); db.session.flush(); chosen.owner_id = user.id; db.session.commit(); login_user(user)
            flash("حساب ساخته شد؛ اعتبار اولیه شما صفر است.", "success")
            return redirect(url_for("dashboard"))
    return render_template("register.html", form=form)

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin" if current_user.role == "admin" else "dashboard"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data.strip()).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            return redirect(url_for("admin" if user.role == "admin" else "dashboard"))
        flash("نام کاربری یا گذرواژه نادرست است.", "error")
    return render_template("login.html", form=form)

@app.route("/logout")
@login_required
def logout():
    logout_user(); return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    latest_news = News.query.order_by(News.created_at.desc()).limit(8).all()
    my_requests = DiplomaticRequest.query.filter_by(user_id=current_user.id).order_by(DiplomaticRequest.created_at.desc()).limit(5).all()
    top20 = Country.query.filter(Country.superpower_rank.isnot(None)).order_by(Country.superpower_rank).all()
    return render_template("dashboard.html", news=latest_news, requests=my_requests, top20=top20)

@app.route("/countries")
def countries():
    return render_template("countries.html", countries=Country.query.order_by(Country.category, Country.name).all())

@app.route("/map")
def map_page():
    coordinates = {
        "ایالات متحده آمریکا": [39.8, -98.6], "فدراسیون روسیه": [61.5, 105.3], "جمهوری خلق چین": [35.9, 104.2],
        "جمهوری هند": [21.0, 78.0], "پادشاهی متحد بریتانیای کبیر و ایرلند شمالی": [55.4, -3.4], "جمهوری فرانسه": [46.2, 2.2],
        "ژاپن": [36.2, 138.2], "جمهوری کره جنوبی": [36.4, 127.9], "جمهوری ترکیه": [39.0, 35.2], "جمهوری اسلامی ایران": [32.4, 53.7],
        "پادشاهی عربستان سعودی": [23.9, 45.1], "اسرائیل": [31.0, 34.8], "جمهوری اسلامی پاکستان": [30.4, 69.3], "جمهوری ایتالیا": [41.9, 12.6],
        "جمهوری فدرال آلمان": [51.2, 10.4], "امارات متحده عربی": [24.2, 53.8], "جمهوری عربی مصر": [26.8, 30.8],
        "جمهوری فدراتیو برزیل": [-10.8, -52.9], "قلمرو همسود استرالیا": [-25.3, 133.8], "کانادا": [56.1, -106.3],
        "لهستان": [52.1, 19.4], "پادشاهی اسپانیا": [40.2, -3.7], "پادشاهی هلند": [52.1, 5.3], "پادشاهی بلژیک": [50.5, 4.5],
        "جمهوری یونان": [39.1, 21.8], "اوکراین": [48.4, 31.2], "پادشاهی نروژ": [60.5, 8.5], "پادشاهی سوئد": [60.1, 18.6],
        "جمهوری فنلاند": [64.0, 26.0], "پادشاهی دانمارک": [56.0, 9.5], "جمهوری پرتغال": [39.4, -8.2], "رومانی": [45.9, 24.9],
        "جمهوری دموکراتیک خلق کره": [40.3, 127.5], "جمهوری آفریقای جنوبی": [-29.0, 24.0], "ونزوئلا": [6.4, -66.6], "لبنان": [33.9, 35.9],
        "اندونزی": [-2.5, 118.0], "سوئیس": [46.8, 8.2], "اتریش": [47.5, 14.5], "ایرلند": [53.1, -8.0], "نیوزیلند": [-41.0, 174.0],
        "مکزیک": [23.6, -102.5], "آرژانتین": [-38.4, -63.6], "کلمبیا": [4.6, -74.1], "کوبا": [21.5, -79.5], "قزاقستان": [48.0, 67.0],
        "جمهوری آذربایجان": [40.1, 47.6], "مراکش": [31.8, -7.1], "الجزایر": [28.0, 1.7], "جمهوری عراق": [33.2, 43.7], "قطر": [25.3, 51.2],
        "کویت": [29.3, 47.5], "عمان": [21.5, 55.9]
    }
    countries = Country.query.order_by(Country.category, Country.name).all()
    points = [{"name": c.name, "flag": c.flag, "color": c.color, "status": c.status, "lat": coordinates[c.name][0], "lon": coordinates[c.name][1]}
              for c in countries if c.category == "country" and c.name in coordinates]
    return render_template("map.html", countries=countries, map_points=points)

@app.route("/superpowers")
def superpowers():
    top20 = Country.query.filter(Country.superpower_rank.isnot(None)).order_by(Country.superpower_rank).all()
    return render_template("superpowers.html", top20=top20)

@app.route("/news", methods=["GET", "POST"])
def news_page():
    form = NewsForm()
    if current_user.is_authenticated and current_user.role == "admin" and form.validate_on_submit():
        db.session.add(News(title=form.title.data.strip(), body=form.body.data.strip(), target=form.target.data))
        db.session.commit(); flash("خبر منتشر شد.", "success"); return redirect(url_for("news_page"))
    items = News.query.order_by(News.created_at.desc()).all()
    return render_template("news.html", news=items, form=form)

@app.route("/diplomacy", methods=["GET", "POST"])
@login_required
def diplomacy():
    form = DiplomacyForm()
    form.target_country.choices = [(c.id, f"{c.flag} {c.name}") for c in Country.query.filter(Country.id != (current_user.country_id or -1)).order_by(Country.name).all()]
    if form.validate_on_submit():
        target = db.session.get(Country, form.target_country.data)
        if not target or target.id == current_user.country_id:
            flash("کشور مقابل معتبر نیست.", "error")
        else:
            db.session.add(DiplomaticRequest(user_id=current_user.id, kind=form.kind.data, details=(form.details.data or "").strip(), target_country_id=target.id, trade_details=(form.trade_details.data or "").strip()))
            db.session.commit(); flash("پیشنهاد دیپلماتیک ارسال شد.", "success"); return redirect(url_for("diplomacy"))
    if current_user.role == "admin":
        items = DiplomaticRequest.query.order_by(DiplomaticRequest.created_at.desc()).all()
    else:
        # Players see proposals they sent and proposals addressed to their country.
        # A request appears only once even when both conditions match.
        items = DiplomaticRequest.query.filter(
            or_(
                DiplomaticRequest.user_id == current_user.id,
                DiplomaticRequest.target_country_id == current_user.country_id,
            )
        ).order_by(DiplomaticRequest.created_at.desc()).all()
    return render_template("diplomacy.html", form=form, requests=items)

@app.route("/diplomacy/respond/<int:req_id>", methods=["POST"])
@login_required
def diplomacy_respond(req_id):
    proposal = db.session.get(DiplomaticRequest, req_id)
    if not proposal:
        abort(404)
    # Only the owner of the addressed country or the admin can decide a proposal.
    is_target_owner = (
        current_user.role != "admin"
        and current_user.country_id is not None
        and proposal.target_country_id == current_user.country_id
    )
    if current_user.role != "admin" and not is_target_owner:
        abort(403)
    if proposal.status != "در انتظار بررسی":
        flash("این پیشنهاد قبلاً تعیین تکلیف شده است.", "error")
        return redirect(url_for("diplomacy"))
    decision = request.form.get("decision", "")
    if decision not in ("پذیرفته شد", "رد شد"):
        abort(400)
    proposal.status = decision
    db.session.commit()
    flash("پیشنهاد دیپلماتیک " + decision + ".", "success")
    return redirect(url_for("diplomacy"))

@app.route("/shop")
@login_required
def shop():
    items = ShopItem.query.order_by(ShopItem.id).all()
    purchases = Purchase.query.filter_by(user_id=current_user.id).order_by(Purchase.created_at.desc()).all()
    return render_template("shop.html", items=items, purchases=purchases)

@app.route("/shop/buy/<int:item_id>", methods=["POST"])
@login_required
def buy(item_id):
    item = db.session.get(ShopItem, item_id)
    if not item: abort(404)
    if current_user.balance < item.price:
        flash("اعتبار کافی نیست. با مدیر تماس بگیر.", "error")
    else:
        current_user.balance -= item.price
        db.session.add(Purchase(user_id=current_user.id, item=item.name, price=item.price))
        if item.name in ("🎗️ نشان CIP", "🏅 نشان VIP"):
            current_user.badges = ",".join(filter(None, [current_user.badges, item.name]))
        db.session.commit(); flash("خرید ثبت شد.", "success")
    return redirect(url_for("shop"))

@app.route("/admin", methods=["GET", "POST"])
@login_required
def admin():
    admin_required()
    if request.method == "POST":
        action = request.form.get("action", "")
        if action == "country":
            c = db.session.get(Country, request.form.get("country_id", type=int))
            color = request.form.get("color", "#718096")
            if c and len(color) == 7 and color.startswith("#"):
                c.color = color
                c.status = request.form.get("status", "آزاد 🟢")[:30]
                db.session.commit(); flash("رنگ و وضعیت روی نقشه ذخیره شد.", "success")
        elif action == "balance":
            u = db.session.get(User, request.form.get("user_id", type=int))
            amount = request.form.get("balance", type=int)
            if u and amount is not None and amount >= 0:
                u.balance = amount; db.session.commit(); flash(f"اعتبار {u.username} به‌روزرسانی شد.", "success")
        elif action == "shop_add":
            name = (request.form.get("name") or "").strip()
            price = request.form.get("price", type=int)
            description = (request.form.get("description") or "").strip()
            if name and price is not None and price >= 0 and len(name) <= 100 and not ShopItem.query.filter_by(name=name).first():
                db.session.add(ShopItem(name=name, price=price, description=description[:300])); db.session.commit(); flash("آیتم شاپ اضافه شد.", "success")
            else: flash("نام باید یکتا باشد و قیمت صفر یا بیشتر وارد شود.", "error")
        elif action == "shop_delete":
            item = db.session.get(ShopItem, request.form.get("item_id", type=int))
            if item:
                db.session.delete(item); db.session.commit(); flash("آیتم از شاپ حذف شد.", "success")
        elif action == "rank":
            c = db.session.get(Country, request.form.get("country_id", type=int))
            rank = request.form.get("rank", type=int)
            if c and rank is not None and 0 <= rank <= 20:
                if rank == 0:
                    c.superpower_rank = None
                else:
                    for other in Country.query.filter_by(superpower_rank=rank).all():
                        other.superpower_rank = None
                    c.superpower_rank = rank
                db.session.commit(); flash("رتبهٔ ابرقدرت‌ها ذخیره شد.", "success")
        elif action == "admin_role":
            u = db.session.get(User, request.form.get("user_id", type=int))
            if u and u.id != current_user.id:
                u.role = "admin" if request.form.get("role") == "admin" else "player"
                db.session.commit(); flash("نقش حساب تغییر کرد.", "success")
        return redirect(url_for("admin"))
    countries = Country.query.order_by(Country.category, Country.name).all()
    users = User.query.order_by(User.username).all()
    requests_list = DiplomaticRequest.query.order_by(DiplomaticRequest.created_at.desc()).limit(50).all()
    items = ShopItem.query.order_by(ShopItem.id).all()
    return render_template("admin.html", users=users, countries=countries, requests=requests_list, items=items, top20=Country.query.filter(Country.superpower_rank.isnot(None)).order_by(Country.superpower_rank).all())

@app.route("/admin/request/<int:req_id>", methods=["POST"])
@login_required
def admin_request(req_id):
    admin_required()
    r = db.session.get(DiplomaticRequest, req_id)
    if not r: abort(404)
    status = request.form.get("status", "")
    if status in ["در انتظار بررسی", "پذیرفته شد", "رد شد"]:
        r.status = status; db.session.commit()
    return redirect(url_for("admin"))

@app.errorhandler(403)
def forbidden(_):
    return render_template("error.html", code=403, message="به این بخش دسترسی نداری."), 403

@app.errorhandler(404)
def not_found(_):
    return render_template("error.html", code=404, message="صفحه پیدا نشد."), 404

def migrate_schema():
    inspector = inspect(db.engine)
    additions = {
        "country": {"flag": "VARCHAR(16) DEFAULT '🏳️'", "category": "VARCHAR(20) DEFAULT 'country'", "superpower_rank": "INTEGER"},
        "diplomatic_request": {"target_country_id": "INTEGER", "trade_details": "TEXT DEFAULT ''"},
    }
    for table, columns in additions.items():
        if table in inspector.get_table_names():
            present = {c["name"] for c in inspect(db.engine).get_columns(table)}
            for col, definition in columns.items():
                if col not in present:
                    with db.engine.begin() as conn:
                        conn.execute(text(f'ALTER TABLE "{table}" ADD COLUMN "{col}" {definition}'))

def init_db():
    with app.app_context():
        db.create_all()
        migrate_schema()
        # Rename seeded legacy labels in place so existing player/country links remain intact.
        for old, new in ALIASES.items():
            old_country = Country.query.filter_by(name=old).first()
            if old_country and not Country.query.filter_by(name=new).first():
                old_country.name = new
        db.session.commit()
        top_ids = {name: rank for rank, (_, name) in enumerate(TOP_COUNTRIES, start=1)}
        seed = TOP_COUNTRIES + OTHER_COUNTRIES + ORGANIZATIONS
        for flag, name in seed:
            c = Country.query.filter_by(name=name).first()
            if not c:
                c = Country(name=name, flag=flag, category="organization" if (flag, name) in ORGANIZATIONS else "country")
                db.session.add(c)
            c.flag = flag
            c.category = "organization" if (flag, name) in ORGANIZATIONS else "country"
            if name in top_ids:
                c.superpower_rank = top_ids[name]
        # Keep flag and category metadata for old seeded entries too.
        for c in Country.query.all():
            if c.name in FLAG_BY_NAME:
                c.flag = FLAG_BY_NAME[c.name]
            if c.name in [n for _, n in ORGANIZATIONS]:
                c.category = "organization"
        if not ShopItem.query.first():
            db.session.add_all([
                ShopItem(name="🎗️ نشان CIP", price=120, description="نشان ویژهٔ CIP"),
                ShopItem(name="🏅 نشان VIP", price=70, description="نشان ویژهٔ VIP"),
                ShopItem(name="📣 خبر برجسته", price=20, description="برجسته‌سازی خبر در بازی"),
                ShopItem(name="🎨 بسته شخصی‌سازی", price=10, description="بستهٔ شخصی‌سازی نمایه"),
            ])
        # Reset balances from the prototype once; never reset again on every restart.
        if not db.session.get(AppSetting, "zero_balance_migration_v1"):
            User.query.update({User.balance: 0})
            db.session.add(AppSetting(key="zero_balance_migration_v1", value="done"))
        admin_name = (os.environ.get("ADMIN_USERNAME") or "").strip()
        admin_password = os.environ.get("ADMIN_PASSWORD") or ""
        if admin_name and admin_password:
            admin_user = User.query.filter_by(username=admin_name).first()
            if admin_user:
                admin_user.role = "admin"
                admin_user.password_hash = generate_password_hash(admin_password)
            else:
                db.session.add(User(username=admin_name, password_hash=generate_password_hash(admin_password), role="admin", balance=0))
        db.session.commit()

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
