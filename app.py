import os
import uuid
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request, flash, abort
from urllib.parse import urlencode
import requests
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import inspect, text, or_
from sqlalchemy.exc import IntegrityError

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-before-deploying")
db_url = (os.environ.get("DATABASE_URL") or "sqlite:///ice_nice.db").strip()
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
# News uploads are limited to 100 MB per request to avoid accidental oversized uploads.
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024
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
    diplomacy_blocked = db.Column(db.Boolean, default=False, nullable=False)
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
    image_url = db.Column(db.String(500), default="", nullable=False)
video_url = db.Column(db.String(500), default="", nullable=False)
image_data = db.Column(db.LargeBinary, nullable=True)
video_data = db.Column(db.LargeBinary, nullable=True)
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
    description = db.Column(db.Text, default="", nullable=False)
    # Optional direct checkout price in Iranian toman; legacy credit price is untouched.
    direct_price_toman = db.Column(db.Integer, nullable=True)
    quantity = db.Column(db.Integer, default=0, nullable=False)
    image_url = db.Column(db.String(500), default="", nullable=False)
    discount_percent = db.Column(db.Integer, default=0, nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)

class ShopPaymentOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    item_id = db.Column(db.Integer, db.ForeignKey("shop_item.id"), nullable=False)
    item_name = db.Column(db.String(100), nullable=False)
    amount_toman = db.Column(db.Integer, nullable=False)
    authority = db.Column(db.String(100), unique=True, nullable=True, index=True)
    status = db.Column(db.String(30), nullable=False, default="pending")
    ref_id = db.Column(db.String(100), nullable=True)
    payment_method = db.Column(db.String(30), default="gateway", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

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
        image_url = (request.form.get("image_url") or "").strip()[:500]
        video_url = (request.form.get("video_url") or "").strip()[:500]
        try:
            uploaded_image = save_news_media(request.files.get("image_file"), "image")
            uploaded_video = save_news_media(request.files.get("video_file"), "video")
            if uploaded_image:
                image_url = uploaded_image
            if uploaded_video:
                video_url = uploaded_video
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("news_page"))
        db.session.add(News(title=form.title.data.strip(), body=form.body.data.strip(), target=form.target.data,
                            image_url=image_url, video_url=video_url))
        db.session.commit()
        flash("خبر منتشر شد.", "success")
        return redirect(url_for("news_page"))
    items = News.query.order_by(News.created_at.desc()).all()
    return render_template("news.html", news=items, form=form)

@app.route("/diplomacy", methods=["GET", "POST"])
@login_required
def diplomacy():
    form = DiplomacyForm()
    form.target_country.choices = [(c.id, f"{c.flag} {c.name}") for c in Country.query.filter(Country.id != (current_user.country_id or -1)).order_by(Country.name).all()]
    if current_user.diplomacy_blocked:
        flash("دسترسی شما به دیپلماسی توسط مالک محدود شده است.", "error")
    elif form.validate_on_submit():
        target = db.session.get(Country, form.target_country.data)
        if not target or target.id == current_user.country_id:
            flash("کشور مقابل معتبر نیست.", "error")
        elif form.kind.data == "اتحاد" and DiplomaticRequest.query.filter_by(kind="اتحاد", status="پذیرفته شد", target_country_id=target.id, user_id=current_user.id).first():
            flash("پیشنهاد اتحاد با این کشور قبلاً پذیرفته شده است.", "error")
        elif form.kind.data == "اتحاد" and current_user.country_id and DiplomaticRequest.query.filter_by(kind="اتحاد", status="پذیرفته شد", target_country_id=current_user.country_id).join(User, DiplomaticRequest.user_id == User.id).filter(User.country_id == target.id).first():
            flash("این کشور از قبل متحد شماست.", "error")
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
    items = ShopItem.query.filter_by(active=True).order_by(ShopItem.id).all()
    purchases = Purchase.query.filter_by(user_id=current_user.id).order_by(Purchase.created_at.desc()).all()
    setting = AppSetting.query.filter_by(key="shop_discount_percent").first()
    global_discount = int(setting.value) if setting else 0
    display_prices = {}
    for item in items:
        discount = max(global_discount, item.discount_percent or 0)
        display_prices[item.id] = max(0, round(item.price * (100 - discount) / 100))
    return render_template("shop.html", items=items, purchases=purchases, display_prices=display_prices, global_discount=global_discount)

@app.route("/shop/pay/<int:item_id>", methods=["POST"])
@login_required
def shop_pay(item_id):
    """Create a manual-transfer order; the owner must verify payment before delivery."""
    item = db.session.get(ShopItem, item_id)
    if not item or not item.active or item.quantity < 1:
        flash("این محصول فعلاً ناموجود است.", "error")
        return redirect(url_for("shop"))
    if not item.direct_price_toman or item.direct_price_toman < 1:
        flash("پرداخت مستقیم برای این محصول توسط مالک فعال نشده است.", "error")
        return redirect(url_for("shop"))
    discount = item.discount_percent or 0
    global_discount = AppSetting.query.filter_by(key="shop_discount_percent").first()
    if global_discount:
        discount = max(discount, min(90, max(0, int(global_discount.value))))
    amount = max(1, round(item.direct_price_toman * (100 - discount) / 100))
    order = ShopPaymentOrder(user_id=current_user.id, item_id=item.id, item_name=item.name,
                             amount_toman=amount, status="manual_pending", payment_method="card_transfer")
    db.session.add(order); db.session.commit()
    return render_template("manual_payment.html", order=order, item=item,
                           card_number="6219861357182780", account_name="باقرپور", rubika_id="@IP_mamad2")

@app.route("/shop/payment/callback/<int:order_id>", methods=["GET"])
@login_required
def shop_payment_callback(order_id):
    order = db.session.get(ShopPaymentOrder, order_id)
    if not order or order.user_id != current_user.id:
        abort(404)
    if order.payment_method == "card_transfer":
        abort(400)
    if order.status == "paid":
        flash("این خرید قبلاً تأیید شده است.", "success")
        return redirect(url_for("shop"))
    if request.args.get("Status", "").upper() != "OK" or not order.authority:
        order.status = "cancelled"
        db.session.commit()
        flash("پرداخت لغو شد یا تأیید نشد؛ آیتمی تحویل داده نشد.", "error")
        return redirect(url_for("shop"))
    merchant_id = (os.environ.get("ZARINPAL_MERCHANT_ID") or "").strip()
    if not merchant_id:
        flash("تنظیمات درگاه ناقص است؛ با مدیر تماس بگیر.", "error")
        return redirect(url_for("shop"))
    sandbox = os.environ.get("ZARINPAL_SANDBOX", "0").strip().lower() in ("1", "true", "yes")
    api_base = "https://sandbox.zarinpal.com/pg/v4/payment" if sandbox else "https://api.zarinpal.com/pg/v4/payment"
    try:
        response = requests.post(f"{api_base}/verify.json", json={
            "merchant_id": merchant_id,
            "amount": order.amount_toman * 10,
            "authority": order.authority,
        }, timeout=15)
        data = response.json().get("data", {})
        code = data.get("code")
        if response.ok and code in (100, 101):
            order.status = "paid"
            order.ref_id = str(data.get("ref_id", ""))
            # Deliver the item exactly once, after server-side gateway verification.
            db.session.add(Purchase(user_id=order.user_id, item=order.item_name, price=0))
            if order.item_name in ("🎗️ نشان CIP", "🏅 نشان VIP"):
                buyer = db.session.get(User, order.user_id)
                if buyer:
                    buyer.badges = ",".join(filter(None, [buyer.badges, order.item_name]))
            db.session.commit()
            flash(f"پرداخت تأیید شد و آیتم «{order.item_name}» به خریدهای شما اضافه شد. کد پیگیری: {order.ref_id}", "success")
        else:
            app.logger.warning("Zarinpal verify rejected order %s: %s", order.id, response.text[:500])
            order.status = "verification_failed"
            db.session.commit()
            flash("درگاه پرداخت را تأیید نکرد؛ آیتم تحویل داده نشد.", "error")
    except (requests.RequestException, ValueError) as exc:
        app.logger.warning("Zarinpal verify failed for order %s: %s", order.id, exc)
        flash("بررسی پرداخت موقتاً ناموفق بود؛ با مدیر تماس بگیر و دوباره پرداخت نکن.", "error")
    return redirect(url_for("shop"))

@app.route("/shop/buy/<int:item_id>", methods=["POST"])
@login_required
def buy(item_id):
    item = db.session.get(ShopItem, item_id)
    if not item: abort(404)
    setting = AppSetting.query.filter_by(key="shop_discount_percent").first()
    global_discount = int(setting.value) if setting else 0
    discount = max(global_discount, item.discount_percent or 0)
    final_price = max(0, round(item.price * (100 - discount) / 100))
    if not item.active or item.quantity < 1:
        flash("این محصول ناموجود است.", "error")
    elif current_user.balance < final_price:
        flash("اعتبار کافی نیست. با مدیر تماس بگیر.", "error")
    else:
        current_user.balance -= final_price
        item.quantity -= 1
        if item.quantity == 0: item.active = False
        db.session.add(Purchase(user_id=current_user.id, item=item.name, price=final_price))
        if item.name in ("🎗️ نشان CIP", "🏅 نشان VIP"):
            current_user.badges = ",".join(filter(None, [current_user.badges, item.name]))
        db.session.commit(); flash("خرید ثبت شد.", "success")
    return redirect(url_for("shop"))

def save_shop_image(upload):
    if not upload or not upload.filename:
        return None
    filename = secure_filename(upload.filename)
    if not filename or not filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
        raise ValueError("فرمت عکس باید PNG، JPG، WEBP یا GIF باشد.")
    upload_dir = os.path.join(app.static_folder, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{int(datetime.utcnow().timestamp())}_{filename}"
    upload.save(os.path.join(upload_dir, filename))
    return url_for("static", filename="uploads/" + filename)


def save_news_media(upload, media_type):
    """Save an uploaded news image or video under static/uploads with a unique filename."""
    if not upload or not upload.filename:
        return None
    filename = secure_filename(upload.filename)
    ext = os.path.splitext(filename)[1].lower()
    allowed = {
        "image": {".png", ".jpg", ".jpeg", ".webp", ".gif"},
        "video": {".mp4", ".webm", ".mov", ".m4v", ".ogv"},
    }
    if not filename or ext not in allowed.get(media_type, set()):
        if media_type == "video":
            raise ValueError("فرمت ویدیو باید MP4، WEBM، MOV، M4V یا OGV باشد.")
        raise ValueError("فرمت عکس باید PNG، JPG، WEBP یا GIF باشد.")
    upload_dir = os.path.join(app.static_folder, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    stored_name = f"news_{media_type}_{uuid.uuid4().hex}{ext}"
    upload.save(os.path.join(upload_dir, stored_name))
    return url_for("static", filename="uploads/" + stored_name)

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
        elif action == "shop_discount":
            percent = request.form.get("discount_percent", type=int)
            if percent is not None and 0 <= percent <= 90:
                setting = AppSetting.query.filter_by(key="shop_discount_percent").first()
                if not setting:
                    setting = AppSetting(key="shop_discount_percent", value=str(percent)); db.session.add(setting)
                else: setting.value = str(percent)
                db.session.commit(); flash("تخفیف عمومی شاپ ذخیره شد.", "success")
            else: flash("درصد تخفیف باید بین صفر تا ۹۰ باشد.", "error")
        elif action == "shop_update":
            item = db.session.get(ShopItem, request.form.get("item_id", type=int))
            if item:
                quantity = request.form.get("quantity", type=int)
                discount = request.form.get("discount_percent", type=int)
                direct_price = request.form.get("direct_price_toman", type=int)
                if quantity is not None and quantity >= 0 and discount is not None and 0 <= discount <= 90 and (direct_price is None or direct_price >= 1):
                    item.name = (request.form.get("name") or item.name).strip()[:100]
                    item.price = max(0, request.form.get("price", type=int) or 0)
                    item.description = (request.form.get("description") or "").strip()
                    item.quantity = quantity; item.discount_percent = discount
                    item.direct_price_toman = direct_price
                    item.image_url = (request.form.get("image_url") or "").strip()[:500] or item.image_url
                    try:
                        uploaded_image = save_shop_image(request.files.get("image_file"))
                        if uploaded_image: item.image_url = uploaded_image
                    except ValueError as exc:
                        flash(str(exc), "error"); return redirect(url_for("admin"))
                    item.active = quantity > 0
                    db.session.commit(); flash("محصول به‌روزرسانی شد.", "success")
                else: flash("موجودی، قیمت یا تخفیف معتبر نیست.", "error")
        elif action == "diplomacy_delete":
            r = db.session.get(DiplomaticRequest, request.form.get("request_id", type=int))
            if r: db.session.delete(r); db.session.commit(); flash("درخواست دیپلماتیک حذف شد.", "success")
        elif action == "diplomacy_block":
            u = db.session.get(User, request.form.get("user_id", type=int))
            if u and u.role != "admin":
                u.diplomacy_blocked = request.form.get("blocked") == "1"
                db.session.commit(); flash("دسترسی دیپلماسی کاربر به‌روزرسانی شد.", "success")
        elif action == "manual_payment_approve":
            order = db.session.get(ShopPaymentOrder, request.form.get("order_id", type=int))
            if order and order.status == "manual_pending" and order.payment_method == "card_transfer":
                item = db.session.get(ShopItem, order.item_id)
                if item and item.quantity > 0:
                    item.quantity -= 1; item.active = item.quantity > 0
                    order.status = "paid"
                    db.session.add(Purchase(user_id=order.user_id, item=order.item_name, price=0))
                    db.session.commit(); flash("پرداخت دستی تأیید و محصول تحویل شد.", "success")
                else: flash("موجودی محصول کافی نیست؛ خرید تأیید نشد.", "error")
        elif action == "manual_payment_reject":
            order = db.session.get(ShopPaymentOrder, request.form.get("order_id", type=int))
            if order and order.status == "manual_pending":
                order.status = "rejected"; db.session.commit(); flash("سفارش رد شد.", "success")
        elif action == "shop_add":
            name = (request.form.get("name") or "").strip()
            price = request.form.get("price", type=int)
            direct_price = request.form.get("direct_price_toman", type=int)
            description = (request.form.get("description") or "").strip()
            quantity = request.form.get("quantity", type=int)
            discount = request.form.get("discount_percent", type=int) or 0
            image_url = (request.form.get("image_url") or "").strip()[:500]
            try:
                uploaded_image = save_shop_image(request.files.get("image_file"))
                if uploaded_image: image_url = uploaded_image
            except ValueError as exc:
                flash(str(exc), "error"); return redirect(url_for("admin"))
            if name and price is not None and price >= 0 and len(name) <= 100 and not ShopItem.query.filter_by(name=name).first() and (direct_price is None or direct_price >= 1) and quantity is not None and quantity >= 0 and 0 <= discount <= 90:
                db.session.add(ShopItem(name=name, price=price, description=description, direct_price_toman=direct_price, quantity=quantity, discount_percent=discount, image_url=image_url, active=quantity > 0)); db.session.commit(); flash("آیتم شاپ اضافه شد.", "success")
            else: flash("نام باید یکتا باشد؛ قیمت اعتبار صفر یا بیشتر و قیمت پرداخت مستقیم خالی یا حداقل یک تومان باشد.", "error")
        elif action == "shop_delete":
            item = db.session.get(ShopItem, request.form.get("item_id", type=int))
            if item:
                # Preserve historical orders. Any FK restriction falls back to safely hiding the item.
                has_orders = ShopPaymentOrder.query.filter_by(item_id=item.id).first() is not None
                if has_orders:
                    item.active = False
                    item.quantity = 0
                    db.session.commit()
                    flash("این محصول در سفارش‌های قبلی ثبت شده بود؛ برای حفظ سوابق خرید، از شاپ غیرفعال شد.", "success")
                else:
                    try:
                        db.session.delete(item)
                        db.session.commit()
                        flash("آیتم از شاپ حذف شد.", "success")
                    except IntegrityError:
                        db.session.rollback()
                        item = db.session.get(ShopItem, request.form.get("item_id", type=int))
                        if item:
                            item.active = False
                            item.quantity = 0
                            db.session.commit()
                            flash("به دلیل وجود سابقهٔ مرتبط، محصول برای حفظ اطلاعات غیرفعال شد.", "success")
                        else:
                            flash("محصول قبلاً حذف شده است.", "success")
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
    manual_orders = ShopPaymentOrder.query.filter_by(payment_method="card_transfer", status="manual_pending").order_by(ShopPaymentOrder.created_at.desc()).all()
    shop_discount = AppSetting.query.filter_by(key="shop_discount_percent").first()
    return render_template("admin.html", users=users, countries=countries, requests=requests_list, items=items, manual_orders=manual_orders, shop_discount=int(shop_discount.value) if shop_discount else 0, top20=Country.query.filter(Country.superpower_rank.isnot(None)).order_by(Country.superpower_rank).all())

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
        "user": {"diplomacy_blocked": "BOOLEAN DEFAULT FALSE"},
        "news": {"image_url": "VARCHAR(500) DEFAULT ''", "video_url": "VARCHAR(500) DEFAULT ''"},
        "country": {"flag": "VARCHAR(16) DEFAULT '🏳️'", "category": "VARCHAR(20) DEFAULT 'country'", "superpower_rank": "INTEGER"},
        "diplomatic_request": {"target_country_id": "INTEGER", "trade_details": "TEXT DEFAULT ''"},
        "shop_item": {"direct_price_toman": "INTEGER", "quantity": "INTEGER DEFAULT 0", "image_url": "VARCHAR(500) DEFAULT ''", "discount_percent": "INTEGER DEFAULT 0", "active": "BOOLEAN DEFAULT TRUE"},
        "shop_payment_order": {"payment_method": "VARCHAR(30) DEFAULT 'gateway'"},
    }
    for table, columns in additions.items():
        if table in inspector.get_table_names():
            present = {c["name"] for c in inspect(db.engine).get_columns(table)}
            for col, definition in columns.items():
                if col not in present:
                    with db.engine.begin() as conn:
                        conn.execute(text(f'ALTER TABLE "{table}" ADD COLUMN "{col}" {definition}'))
    # Do not auto-restock zero-quantity products on startup. Zero means sold out;
    # an automatic UPDATE here would resurrect sold-out items on every deploy.

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
        palette = ["#2563eb", "#dc2626", "#16a34a", "#9333ea", "#ea580c", "#0891b2", "#be123c", "#4f46e5", "#65a30d", "#c026d3", "#0f766e", "#b45309", "#1d4ed8", "#a21caf", "#047857", "#b91c1c", "#0369a1", "#6d28d9", "#4d7c0f", "#9f1239"]
        for idx, country in enumerate(Country.query.filter_by(category="country").order_by(Country.name).all()):
            if not country.color or country.color == "#718096": country.color = palette[idx % len(palette)]
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
