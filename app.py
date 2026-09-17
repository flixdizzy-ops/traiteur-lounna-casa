import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from config import Config

app = Flask(__name__)
app.config.from_object(Config)

DB_PATH = Path(app.config["DATABASE"])
UPLOAD_PATH = Path(app.config["UPLOAD_FOLDER"])
TRANSLATIONS_DIR = Path(__file__).resolve().parent / "translations"
ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

# In-memory fallback catalogue for a fully working demo site while keeping independent product management.
DEFAULT_CATALOG = [
    {
        "id": 1,
        "name": {"fr": "Tajine Dinde Royal", "ar": "طاجين الديك الرومي الملكي", "en": "Royal Turkey Tagine"},
        "category": "tajines",
        "price": 220,
        "image": "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=900&q=80",
        "description": {
            "fr": "Dinde confite, pruneaux, amandes et épices marocaines, servi dans un tajine traditionnel.",
            "ar": "ديك رومي مطهو ببطء مع التمر واللوز والتوابل المغربية في طاجين تقليدي.",
            "en": "Slow-cooked turkey with dates, almonds and Moroccan spices in a traditional tagine."
        },
        "badge": {"fr": "Best seller", "ar": "الأكثر مبيعًا", "en": "Best seller"},
        "featured": True,
        "popular": True,
    },
    {
        "id": 2,
        "name": {"fr": "Couscous Royal", "ar": "كسكس ملكي", "en": "Royal Couscous"},
        "category": "couscous",
        "price": 190,
        "image": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&w=900&q=80",
        "description": {
            "fr": "Couscous parfumé aux légumes de saison, viande mijotée et sauce royale.",
            "ar": "كسكس مع الخضار الموسمية واللحم المطهو ببطء والصوص الملكي.",
            "en": "Fragrant couscous with seasonal vegetables, slow-cooked meat and royal sauce."
        },
        "badge": {"fr": "Signature", "ar": "توقيع", "en": "Signature"},
        "featured": True,
        "popular": True,
    },
    {
        "id": 3,
        "name": {"fr": "Pastilla de Poulet", "ar": "بسطيلة الدجاج", "en": "Chicken Pastilla"},
        "category": "bouches",
        "price": 140,
        "image": "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?auto=format&fit=crop&w=900&q=80",
        "description": {
            "fr": "Feuilleté doré au poulet, amande, cannelle et coriandre, finement croustillant.",
            "ar": "بسطيلة دجاج باللوز والقرفة والكزبرة مع قشرة ذهبية وهشة.",
            "en": "Golden pastry with chicken, almonds, cinnamon and coriander, crisp and refined."
        },
        "badge": {"fr": "À partager", "ar": "للمشاركة", "en": "Shareable"},
        "featured": False,
        "popular": True,
    },
    {
        "id": 4,
        "name": {"fr": "Mini Buffet Prestige", "ar": "بوفيه صغير فاخر", "en": "Prestige Mini Buffet"},
        "category": "buffets",
        "price": 420,
        "image": "https://images.unsplash.com/photo-1528605248644-14dd04022da1?auto=format&fit=crop&w=900&q=80",
        "description": {
            "fr": "Sélection raffinée de plats marocains pour accueil VIP et tables d’honneur.",
            "ar": "اختيار فاخر من الأطباق المغربية لاستقبال الضيوف والموائد المميزة.",
            "en": "Refined Moroccan platter selection for VIP welcome and elegant guest tables."
        },
        "badge": {"fr": "Événement", "ar": "مناسبة", "en": "Event"},
        "featured": True,
        "popular": False,
    },
    {
        "id": 5,
        "name": {"fr": "Assiette Mechoui", "ar": "طبق المشوي", "en": "Mechoui Platter"},
        "category": "grillades",
        "price": 260,
        "image": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=900&q=80",
        "description": {
            "fr": "Viande rôtie aux herbes, accompagnée de pain maison, légumes grillés et sauces.",
            "ar": "لحم مشوي بالأعشاب مع خبز منزلي وخضروات مشوية وصوصات.",
            "en": "Herb-roasted meat with house bread, grilled vegetables and sauces."
        },
        "badge": {"fr": "Grillades", "ar": "مشوي", "en": "Grill"},
        "featured": False,
        "popular": False,
    },
    {
        "id": 6,
        "name": {"fr": "Pâtisserie Marocaine", "ar": "حلويات مغربية", "en": "Moroccan Pastries"},
        "category": "desserts",
        "price": 95,
        "image": "https://images.unsplash.com/photo-1551024601-bec78aea704b?auto=format&fit=crop&w=900&q=80",
        "description": {
            "fr": "Assortiment de gâteaux marocains, makrout et fruits secs.",
            "ar": "مجموعة من الحلويات المغربية والمقرمشات والفواكه المجففة.",
            "en": "Selection of Moroccan cakes, makrout and dried fruits."
        },
        "badge": {"fr": "Sucré", "ar": "حلو", "en": "Sweet"},
        "featured": False,
        "popular": True,
    },
]

DEFAULT_CATEGORY_MAP = {
    "tajines": {"fr": "Tajines", "ar": "الأطباق", "en": "Tagines"},
    "couscous": {"fr": "Couscous", "ar": "الكسكسي", "en": "Couscous"},
    "bouches": {"fr": "Bouches", "ar": "مقبلات", "en": "Bites"},
    "buffets": {"fr": "Buffets", "ar": "بوفيهات", "en": "Buffets"},
    "grillades": {"fr": "Grillades", "ar": "مشويات", "en": "Grills"},
    "desserts": {"fr": "Desserts", "ar": "حلويات", "en": "Desserts"},
}


def get_db_connection():
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            image TEXT,
            description TEXT,
            featured INTEGER DEFAULT 0,
            popular INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT,
            address TEXT,
            items TEXT NOT NULL,
            total REAL NOT NULL,
            status TEXT DEFAULT 'new',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    existing_order_columns = {row[1] for row in conn.execute("PRAGMA table_info(orders)").fetchall()}
    for column, definition in {
        "city": "TEXT",
        "preferred_datetime": "TEXT",
        "notes": "TEXT",
    }.items():
        if column not in existing_order_columns:
            conn.execute(f"ALTER TABLE orders ADD COLUMN {column} {definition}")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            event_date TEXT NOT NULL,
            location TEXT NOT NULL,
            guests INTEGER NOT NULL,
            services TEXT,
            budget TEXT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            message TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            subject TEXT,
            message TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS content_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_type TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT,
            image TEXT,
            title_fr TEXT,
            title_ar TEXT,
            title_en TEXT,
            body_fr TEXT,
            body_ar TEXT,
            body_en TEXT,
            icon TEXT,
            sort_order INTEGER DEFAULT 0,
            active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute("CREATE TABLE IF NOT EXISTS pages (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, slug TEXT UNIQUE NOT NULL, title TEXT NOT NULL, content TEXT, image TEXT, active INTEGER DEFAULT 1, nav_visible INTEGER DEFAULT 0, footer_visible INTEGER DEFAULT 0, sort_order INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
    conn.execute("CREATE TABLE IF NOT EXISTS navigation_items (id INTEGER PRIMARY KEY AUTOINCREMENT, label TEXT NOT NULL, url TEXT NOT NULL, target_type TEXT DEFAULT 'external', visible_nav INTEGER DEFAULT 1, visible_footer INTEGER DEFAULT 0, sort_order INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
    conn.execute("CREATE TABLE IF NOT EXISTS media_library (id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT NOT NULL, url TEXT NOT NULL, mime_type TEXT, file_size INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
    for table, columns in {
        "products": {"active": "INTEGER DEFAULT 1", "sort_order": "INTEGER DEFAULT 0", "details": "TEXT"},
        "categories": {"active": "INTEGER DEFAULT 1", "sort_order": "INTEGER DEFAULT 0"},
        "reservations": {"status": "TEXT DEFAULT 'new'"},
        "content_items": {"title_fr": "TEXT", "title_ar": "TEXT", "title_en": "TEXT", "body_fr": "TEXT", "body_ar": "TEXT", "body_en": "TEXT", "icon": "TEXT"},
    }.items():
        existing_columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        for column, definition in columns.items():
            if column not in existing_columns:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
    conn.commit()
    conn.close()

    seed_demo_data()


def seed_demo_data():
    conn = sqlite3.connect(app.config["DATABASE"])
    existing = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    if existing == 0:
        for product in DEFAULT_CATALOG:
            conn.execute(
                "INSERT INTO products (name, category, price, image, description, featured, popular) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    json.dumps(product["name"], ensure_ascii=False),
                    product["category"],
                    product["price"],
                    product["image"],
                    json.dumps(product["description"], ensure_ascii=False),
                    int(product["featured"]),
                    int(product["popular"]),
                ),
            )
        categories = [
            ("tajines", json.dumps({"fr": "Tajines", "ar": "الأطباق", "en": "Tagines"}, ensure_ascii=False)),
            ("couscous", json.dumps({"fr": "Couscous", "ar": "الكسكسي", "en": "Couscous"}, ensure_ascii=False)),
            ("bouches", json.dumps({"fr": "Bouches", "ar": "مقبلات", "en": "Bites"}, ensure_ascii=False)),
            ("buffets", json.dumps({"fr": "Buffets", "ar": "بوفيهات", "en": "Buffets"}, ensure_ascii=False)),
            ("grillades", json.dumps({"fr": "Grillades", "ar": "مشويات", "en": "Grills"}, ensure_ascii=False)),
            ("desserts", json.dumps({"fr": "Desserts", "ar": "حلويات", "en": "Desserts"}, ensure_ascii=False)),
        ]
        conn.executemany(
            "INSERT INTO categories (slug, name) VALUES (?, ?)",
            categories,
        )
        default_settings = {
            "phone": "+212 713 915 287",
            "location": "Casablanca, Maroc",
            "instagram": "https://www.instagram.com/traiteur_loubna_casa/",
            "tiktok": "https://www.tiktok.com/@traiteur_loubna_casa",
            "whatsapp": "https://wa.me/212713915287",
            "email": "contact@traiteurlounnacasa.ma",
        }
        for key, value in default_settings.items():
            conn.execute("INSERT INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()


def ensure_default_admin():
    conn = sqlite3.connect(app.config["DATABASE"])
    exists = conn.execute("SELECT 1 FROM admin_users LIMIT 1").fetchone()
    if not exists:
        conn.execute(
            "INSERT INTO admin_users (username, password_hash) VALUES (?, ?)",
            (app.config["ADMIN_USERNAME"], generate_password_hash(app.config["ADMIN_PASSWORD"])),
        )
        conn.commit()
    conn.close()


init_db()
ensure_default_admin()


def is_admin_authenticated():
    return bool(session.get("admin_user_id"))


@app.before_request
def protect_admin_routes():
    if request.path.startswith("/admin") and request.endpoint not in {"admin_login", "admin_register"}:
        if not is_admin_authenticated():
            if request.path == "/admin/upload":
                return jsonify({"success": False, "message": "Unauthorized"}), 401
            return redirect(url_for("admin_login", next=request.path))


def normalize_lang(lang):
    return lang if lang in ("fr", "ar", "en") else "fr"


def get_translation(lang):
    lang = normalize_lang(lang)
    path = TRANSLATIONS_DIR / f"{lang}.json"
    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}


@app.template_filter("from_json")
def from_json_filter(value):
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return {}


def get_product_data(product_row):
    if not product_row:
        return None
    try:
        name = json.loads(product_row["name"])
        description = json.loads(product_row["description"])
    except (TypeError, ValueError):
        name = {"fr": product_row["name"], "ar": product_row["name"], "en": product_row["name"]}
        description = {"fr": product_row["description"], "ar": product_row["description"], "en": product_row["description"]}
    return {
        "id": product_row["id"],
        "name": name,
        "category": product_row["category"],
        "price": float(product_row["price"]),
        "image": product_row["image"] or "/static/images/logo/hero/products/default.jpg",
        "description": description,
        "featured": bool(product_row["featured"]),
        "popular": bool(product_row["popular"]),
    }


def _category_name_for_lang(category_slug, lang):
    conn = get_db_connection()
    row = conn.execute("SELECT name FROM categories WHERE slug = ?", (category_slug,)).fetchone()
    conn.close()
    if not row:
        return DEFAULT_CATEGORY_MAP.get(category_slug, {}).get(lang, category_slug)
    try:
        name = json.loads(row["name"])
    except (TypeError, ValueError):
        name = {"fr": row["name"], "ar": row["name"], "en": row["name"]}
    return name.get(lang, name.get("fr", category_slug))


def get_all_products(lang):
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM products WHERE COALESCE(active, 1) = 1 ORDER BY COALESCE(sort_order, 0), created_at DESC").fetchall()
    conn.close()
    return [get_product_data(row) for row in rows]


def get_settings_dict():
    conn = get_db_connection()
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    conn.close()
    settings = {row["key"]: row["value"] for row in rows}
    if settings.get("tiktok") == "https://www.tiktok.com/@traiteur_loubna_casa":
        settings["tiktok"] = "https://www.tiktok.com/@traiteur_loubna_casa/"
    return settings


def get_content_items(content_type=None, include_inactive=False):
    conn = get_db_connection()
    active_clause = "" if include_inactive else " AND active = 1"
    if content_type:
        rows = conn.execute(f"SELECT * FROM content_items WHERE content_type = ?{active_clause} ORDER BY sort_order, id", (content_type,)).fetchall()
    else:
        rows = conn.execute(f"SELECT * FROM content_items WHERE 1 = 1{active_clause} ORDER BY content_type, sort_order, id").fetchall()
    conn.close()
    return rows


def get_navigation_items():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM navigation_items WHERE visible_nav = 1 ORDER BY sort_order, id").fetchall()
    conn.close()
    return rows


def get_categories():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM categories WHERE COALESCE(active, 1) = 1 ORDER BY COALESCE(sort_order, 0), id").fetchall()
    conn.close()
    return rows


def save_uploaded_image(file):
    extension = Path(file.filename).suffix.lower().lstrip(".")
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError("Unsupported image format")
    safe_name = secure_filename(Path(file.filename).stem) or "image"
    filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{safe_name}.{extension}"
    UPLOAD_PATH.mkdir(parents=True, exist_ok=True)
    file.save(UPLOAD_PATH / filename)
    return url_for("uploaded_file", filename=filename)


@app.context_processor
def inject_globals():
    lang = session.get("lang", "fr")
    translations = get_translation(lang)
    settings = get_settings_dict()
    return {
        "lang": lang,
        "translations": translations,
        "settings": settings,
        "cms_content": get_content_items(),
        "navigation_items": get_navigation_items(),
        "current_year": datetime.now().year,
    }


@app.route("/lang/<lang>")
def set_language(lang):
    normalized = normalize_lang(lang)
    session["lang"] = normalized
    return redirect(request.referrer or url_for("home"))


@app.route("/<lang>")
def language_shortcut(lang):
    if lang not in ("fr", "ar", "en"):
        return render_template("errors/404.html"), 404
    session["lang"] = lang
    return redirect(url_for("home"))


@app.route("/")
def home():
    lang = session.get("lang", "fr")
    products = get_all_products(lang)
    featured_products = [product for product in products if product["featured"]] or products
    return render_template("index.html", products=featured_products[:6], page_title="Accueil")


@app.route("/about")
def about():
    return render_template("about.html", page_title="À propos")


@app.route("/services")
def services():
    return render_template("services.html", page_title="Services")


@app.route("/menu")
def menu():
    products = get_all_products(session.get("lang", "fr"))
    return render_template("menu.html", products=products, page_title="Menu")


@app.route("/product/<int:product_id>")
def product_detail(product_id):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    conn.close()
    product = get_product_data(row)
    if not product:
        return render_template("errors/404.html"), 404
    related = [p for p in get_all_products(session.get("lang", "fr")) if p["id"] != product_id][:3]
    return render_template("product.html", product=product, related=related, page_title="Produit")


@app.route("/events")
def events():
    return render_template("events.html", page_title="Événements")


@app.route("/gallery")
def gallery():
    return render_template("gallery.html", page_title="Galerie")


@app.route("/order")
def order_page():
    products = get_all_products(session.get("lang", "fr"))
    return render_template("order.html", products=products, page_title="Commander")


@app.route("/reservation")
def reservation_page():
    return render_template("reservation.html", page_title="Réservation")


@app.route("/contact")
def contact_page():
    return render_template("contact.html", page_title="Contact")


@app.route("/faq")
def faq_page():
    return render_template("faq.html", page_title="FAQ")


@app.route("/page/<slug>")
def dynamic_page(slug):
    conn = get_db_connection()
    page = conn.execute("SELECT * FROM pages WHERE slug = ? AND active = 1", (slug,)).fetchone()
    conn.close()
    if not page:
        return render_template("errors/404.html"), 404
    return render_template("page.html", page=page, page_title=page["name"])


@app.route("/api/products")
def api_products():
    products = get_all_products(session.get("lang", "fr"))
    return jsonify({"products": products})


@app.route("/api/cart", methods=["POST"])
def api_add_to_cart():
    data = request.get_json(silent=True) or {}
    item = data.get("item")
    if not item:
        return jsonify({"success": False, "message": "Invalid item"}), 400
    cart = session.get("cart", [])
    existing = next((i for i in cart if i["id"] == item["id"]), None)
    if existing:
        existing["quantity"] += int(item.get("quantity", 1))
    else:
        cart.append({"id": int(item["id"]), "quantity": int(item.get("quantity", 1))})
    session["cart"] = cart
    return jsonify({"success": True, "cart_count": sum(i["quantity"] for i in cart)})


@app.route("/api/cart", methods=["GET"])
def api_get_cart():
    cart = session.get("cart", [])
    products = get_all_products(session.get("lang", "fr"))
    product_map = {p["id"]: p for p in products}
    items = []
    total = 0.0
    for entry in cart:
        product = product_map.get(int(entry["id"]))
        if not product:
            continue
        quantity = int(entry.get("quantity", 1))
        subtotal = product["price"] * quantity
        total += subtotal
        items.append({
            "id": product["id"],
            "name": product["name"].get(session.get("lang", "fr"), product["name"].get("fr")),
            "image": product["image"],
            "quantity": quantity,
            "price": product["price"],
            "subtotal": subtotal,
        })
    return jsonify({"items": items, "total": total})


@app.route("/api/order", methods=["POST"])
def submit_order():
    data = request.get_json(silent=True) or {}
    name = (data.get("customer_name") or "").strip()
    phone = (data.get("phone") or "").strip()
    city = (data.get("city") or "").strip()
    address = (data.get("delivery_address") or "").strip()
    preferred_datetime = (data.get("preferred_datetime") or "").strip()
    notes = (data.get("notes") or "").strip()
    items = data.get("items") or []
    if not city or not address or not preferred_datetime:
        return jsonify({"success": False, "message": "Veuillez renseigner la ville, l’adresse et la date souhaitée."}), 400

    products = {product["id"]: product for product in get_all_products(session.get("lang", "fr"))}
    normalized_items = []
    total = 0.0
    for item in items:
        product = products.get(int(item.get("id", 0)))
        quantity = int(item.get("quantity", 0))
        if not product or quantity < 1 or quantity > 99:
            return jsonify({"success": False, "message": "Le panier contient un article invalide."}), 400
        subtotal = product["price"] * quantity
        total += subtotal
        normalized_items.append({"id": product["id"], "name": product["name"].get(session.get("lang", "fr"), product["name"].get("fr")), "quantity": quantity, "price": product["price"], "subtotal": subtotal})

    if not name or not phone or not normalized_items:
        return jsonify({"success": False, "message": "Please provide valid order details."}), 400

    conn = sqlite3.connect(app.config["DATABASE"])
    conn.execute(
        "INSERT INTO orders (customer_name, phone, address, city, preferred_datetime, notes, items, total) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (name, phone, address, city, preferred_datetime, notes, json.dumps(normalized_items, ensure_ascii=False), total),
    )
    conn.commit()
    conn.close()
    session["cart"] = []
    return jsonify({"success": True, "message": "Order sent successfully."})


@app.route("/api/reservation", methods=["POST"])
def submit_reservation():
    data = request.form or {}
    required = ["event_type", "event_date", "location", "guests", "name", "phone"]
    if not all(data.get(key) for key in required):
        return jsonify({"success": False, "message": "Please complete required fields."}), 400

    conn = sqlite3.connect(app.config["DATABASE"])
    conn.execute(
        "INSERT INTO reservations (event_type, event_date, location, guests, services, budget, name, phone, message) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            data.get("event_type"),
            data.get("event_date"),
            data.get("location"),
            int(data.get("guests", 0)),
            data.get("services", ""),
            data.get("budget", ""),
            data.get("name"),
            data.get("phone"),
            data.get("message", ""),
        ),
    )
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Reservation sent successfully."})


@app.route("/api/contact", methods=["POST"])
def submit_contact():
    data = request.form or {}
    if not data.get("name") or not data.get("message"):
        return jsonify({"success": False, "message": "Name and message are required."}), 400

    conn = sqlite3.connect(app.config["DATABASE"])
    conn.execute(
        "INSERT INTO contacts (name, email, phone, subject, message) VALUES (?, ?, ?, ?, ?)",
        (
            data.get("name"),
            data.get("email", ""),
            data.get("phone", ""),
            data.get("subject", ""),
            data.get("message"),
        ),
    )
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Message sent successfully."})


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM admin_users WHERE username = ?", (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password_hash"], password):
            session["admin_user_id"] = user["id"]
            session["admin_logged_in"] = True
            return redirect(request.args.get("next") or url_for("admin_dashboard"))
        return render_template("admin/login.html", error="Identifiants invalides")
    return render_template("admin/login.html")


@app.route("/admin/register", methods=["GET", "POST"])
def admin_register():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        confirmation = request.form.get("password_confirmation") or ""
        if len(username) < 3 or len(password) < 8:
            return render_template("admin/register.html", error="Utilisez un identifiant de 3 caractères et un mot de passe de 8 caractères minimum.")
        if password != confirmation:
            return render_template("admin/register.html", error="Les mots de passe ne correspondent pas.")
        conn = sqlite3.connect(app.config["DATABASE"])
        try:
            cursor = conn.execute(
                "INSERT INTO admin_users (username, password_hash) VALUES (?, ?)",
                (username, generate_password_hash(password)),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return render_template("admin/register.html", error="Cet identifiant existe déjà.")
        conn.close()
        session["admin_user_id"] = cursor.lastrowid
        session["admin_logged_in"] = True
        return redirect(url_for("admin_dashboard"))
    return render_template("admin/register.html")


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    session.pop("admin_user_id", None)
    return redirect(url_for("admin_login"))


@app.route("/admin")
def admin_dashboard():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    conn = get_db_connection()
    products_count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    categories_count = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
    orders_count = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    reservations_count = conn.execute("SELECT COUNT(*) FROM reservations").fetchone()[0]
    messages_count = conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
    pages_count = conn.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
    recent_orders = conn.execute("SELECT id, customer_name, total, status, created_at FROM orders ORDER BY id DESC LIMIT 5").fetchall()
    recent_reservations = conn.execute("SELECT id, name, event_type, status, created_at FROM reservations ORDER BY id DESC LIMIT 5").fetchall()
    conn.close()
    return render_template(
        "admin/dashboard.html",
        products_count=products_count,
        categories_count=categories_count,
        orders_count=orders_count,
        reservations_count=reservations_count,
        messages_count=messages_count,
        pages_count=pages_count,
        recent_orders=recent_orders,
        recent_reservations=recent_reservations,
    )


@app.route("/admin/products")
def admin_products():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    conn.close()
    products = [get_product_data(row) for row in rows]
    return render_template("admin/products.html", products=products)


@app.route("/admin/categories", methods=["GET", "POST"])
def admin_categories():
    conn = get_db_connection()
    if request.method == "POST":
        slug = (request.form.get("slug") or "").strip().lower().replace(" ", "-")
        names = {"fr": request.form.get("name_fr"), "ar": request.form.get("name_ar"), "en": request.form.get("name_en")}
        if slug and names["fr"]:
            conn.execute("INSERT OR REPLACE INTO categories (slug, name) VALUES (?, ?)", (slug, json.dumps(names, ensure_ascii=False)))
            conn.commit()
    categories = conn.execute("SELECT * FROM categories ORDER BY id").fetchall()
    conn.close()
    return render_template("admin/categories.html", categories=categories)


@app.route("/admin/categories/<int:category_id>/delete", methods=["POST"])
def admin_category_delete(category_id):
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_categories"))


@app.route("/admin/content", methods=["GET", "POST"])
def admin_content():
    if request.method == "POST":
        image = ""
        image_file = request.files.get("image_file")
        if image_file and image_file.filename:
            image = save_uploaded_image(image_file)
        conn = sqlite3.connect(app.config["DATABASE"])
        title_fr = request.form.get("title_fr", "").strip()
        body_fr = request.form.get("body_fr", "")
        conn.execute(
            "INSERT INTO content_items (content_type, title, body, image, title_fr, title_ar, title_en, body_fr, body_ar, body_en, icon, sort_order, active) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (request.form.get("content_type", "service"), title_fr or request.form.get("title", "").strip(), body_fr or request.form.get("body", ""), image, title_fr, request.form.get("title_ar", ""), request.form.get("title_en", ""), body_fr, request.form.get("body_ar", ""), request.form.get("body_en", ""), request.form.get("icon", ""), int(request.form.get("sort_order", 0) or 0), 1 if request.form.get("active") == "on" else 0),
        )
        conn.commit()
        conn.close()
        return redirect(url_for("admin_content"))
    return render_template("admin/content.html", content_items=get_content_items(include_inactive=True))


@app.route("/admin/content/<int:item_id>/delete", methods=["POST"])
def admin_content_delete(item_id):
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.execute("DELETE FROM content_items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_content"))


@app.route("/admin/content/<int:item_id>/edit", methods=["GET", "POST"])
def admin_content_edit(item_id):
    conn = get_db_connection()
    item = conn.execute("SELECT * FROM content_items WHERE id = ?", (item_id,)).fetchone()
    conn.close()
    if not item:
        return render_template("errors/404.html"), 404
    if request.method == "POST":
        image = item["image"]
        image_file = request.files.get("image_file")
        if image_file and image_file.filename:
            image = save_uploaded_image(image_file)
        conn = sqlite3.connect(app.config["DATABASE"])
        conn.execute("UPDATE content_items SET title = ?, body = ?, title_fr = ?, title_ar = ?, title_en = ?, body_fr = ?, body_ar = ?, body_en = ?, image = ?, icon = ?, sort_order = ?, active = ? WHERE id = ?", (request.form.get("title_fr", ""), request.form.get("body_fr", ""), request.form.get("title_fr", ""), request.form.get("title_ar", ""), request.form.get("title_en", ""), request.form.get("body_fr", ""), request.form.get("body_ar", ""), request.form.get("body_en", ""), image, request.form.get("icon", ""), int(request.form.get("sort_order", 0) or 0), request.form.get("active") == "on", item_id))
        conn.commit()
        conn.close()
        return redirect(url_for("admin_content"))
    return render_template("admin/content_edit.html", item=item)


@app.route("/admin/pages", methods=["GET", "POST"])
def admin_pages():
    if request.method == "POST":
        image = ""
        image_file = request.files.get("image_file")
        if image_file and image_file.filename:
            image = save_uploaded_image(image_file)
        titles = {"fr": request.form.get("title_fr", ""), "ar": request.form.get("title_ar", ""), "en": request.form.get("title_en", "")}
        bodies = {"fr": request.form.get("content_fr", ""), "ar": request.form.get("content_ar", ""), "en": request.form.get("content_en", "")}
        conn = sqlite3.connect(app.config["DATABASE"])
        try:
            conn.execute("INSERT INTO pages (name, slug, title, content, image, active, nav_visible, footer_visible, sort_order) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (request.form.get("name", "").strip(), request.form.get("slug", "").strip().lower(), json.dumps(titles, ensure_ascii=False), json.dumps(bodies, ensure_ascii=False), image, request.form.get("active") == "on", request.form.get("nav_visible") == "on", request.form.get("footer_visible") == "on", int(request.form.get("sort_order", 0) or 0)))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.rollback()
        conn.close()
        return redirect(url_for("admin_pages"))
    conn = get_db_connection()
    pages = conn.execute("SELECT * FROM pages ORDER BY sort_order, id").fetchall()
    conn.close()
    return render_template("admin/pages.html", pages=pages)


@app.route("/admin/pages/<int:page_id>/delete", methods=["POST"])
def admin_page_delete(page_id):
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.execute("DELETE FROM pages WHERE id = ?", (page_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_pages"))


@app.route("/admin/pages/<int:page_id>/edit", methods=["GET", "POST"])
def admin_page_edit(page_id):
    conn = get_db_connection()
    page = conn.execute("SELECT * FROM pages WHERE id = ?", (page_id,)).fetchone()
    conn.close()
    if not page:
        return render_template("errors/404.html"), 404
    if request.method == "POST":
        image = page["image"]
        image_file = request.files.get("image_file")
        if image_file and image_file.filename:
            image = save_uploaded_image(image_file)
        conn = sqlite3.connect(app.config["DATABASE"])
        conn.execute("UPDATE pages SET name = ?, slug = ?, title = ?, content = ?, image = ?, active = ?, nav_visible = ?, footer_visible = ?, sort_order = ? WHERE id = ?", (request.form.get("name", ""), request.form.get("slug", ""), json.dumps({"fr": request.form.get("title_fr", ""), "ar": request.form.get("title_ar", ""), "en": request.form.get("title_en", "")}, ensure_ascii=False), json.dumps({"fr": request.form.get("content_fr", ""), "ar": request.form.get("content_ar", ""), "en": request.form.get("content_en", "")}, ensure_ascii=False), image, request.form.get("active") == "on", request.form.get("nav_visible") == "on", request.form.get("footer_visible") == "on", int(request.form.get("sort_order", 0) or 0), page_id))
        conn.commit()
        conn.close()
        return redirect(url_for("admin_pages"))
    return render_template("admin/page_edit.html", page=page)


@app.route("/admin/navigation", methods=["GET", "POST"])
def admin_navigation():
    if request.method == "POST":
        conn = sqlite3.connect(app.config["DATABASE"])
        conn.execute("INSERT INTO navigation_items (label, url, target_type, visible_nav, visible_footer, sort_order) VALUES (?, ?, ?, ?, ?, ?)", (request.form.get("label", "").strip(), request.form.get("url", "").strip(), request.form.get("target_type", "external"), request.form.get("visible_nav") == "on", request.form.get("visible_footer") == "on", int(request.form.get("sort_order", 0) or 0)))
        conn.commit()
        conn.close()
        return redirect(url_for("admin_navigation"))
    conn = get_db_connection()
    items = conn.execute("SELECT * FROM navigation_items ORDER BY sort_order, id").fetchall()
    conn.close()
    return render_template("admin/navigation.html", items=items)


@app.route("/admin/navigation/<int:item_id>/delete", methods=["POST"])
def admin_navigation_delete(item_id):
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.execute("DELETE FROM navigation_items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_navigation"))


@app.route("/admin/navigation/<int:item_id>/edit", methods=["GET", "POST"])
def admin_navigation_edit(item_id):
    conn = get_db_connection()
    item = conn.execute("SELECT * FROM navigation_items WHERE id = ?", (item_id,)).fetchone()
    conn.close()
    if not item:
        return render_template("errors/404.html"), 404
    if request.method == "POST":
        conn = sqlite3.connect(app.config["DATABASE"])
        conn.execute("UPDATE navigation_items SET label = ?, url = ?, target_type = ?, visible_nav = ?, visible_footer = ?, sort_order = ? WHERE id = ?", (request.form.get("label", ""), request.form.get("url", ""), request.form.get("target_type", "external"), request.form.get("visible_nav") == "on", request.form.get("visible_footer") == "on", int(request.form.get("sort_order", 0) or 0), item_id))
        conn.commit()
        conn.close()
        return redirect(url_for("admin_navigation"))
    return render_template("admin/navigation_edit.html", item=item)


@app.route("/admin/media", methods=["GET", "POST"])
def admin_media():
    if request.method == "POST":
        file = request.files.get("file")
        if file and file.filename:
            url = save_uploaded_image(file)
            path = UPLOAD_PATH / Path(url).name
            conn = sqlite3.connect(app.config["DATABASE"])
            conn.execute("INSERT INTO media_library (filename, url, mime_type, file_size) VALUES (?, ?, ?, ?)", (file.filename, url, file.mimetype, path.stat().st_size if path.exists() else 0))
            conn.commit()
            conn.close()
        return redirect(url_for("admin_media"))
    conn = get_db_connection()
    media = conn.execute("SELECT * FROM media_library ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("admin/media.html", media=media)


@app.route("/admin/media/<int:media_id>/delete", methods=["POST"])
def admin_media_delete(media_id):
    conn = get_db_connection()
    item = conn.execute("SELECT * FROM media_library WHERE id = ?", (media_id,)).fetchone()
    conn.close()
    if item:
        (UPLOAD_PATH / Path(item["url"]).name).unlink(missing_ok=True)
        conn = sqlite3.connect(app.config["DATABASE"])
        conn.execute("DELETE FROM media_library WHERE id = ?", (media_id,))
        conn.commit()
        conn.close()
    return redirect(url_for("admin_media"))


@app.route("/admin/products/new", methods=["GET", "POST"])
def admin_product_form():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    if request.method == "POST":
        product_name = {"fr": request.form.get("name_fr"), "ar": request.form.get("name_ar"), "en": request.form.get("name_en")}
        description = {"fr": request.form.get("description_fr"), "ar": request.form.get("description_ar"), "en": request.form.get("description_en")}
        image = request.form.get("image") or "/static/images/logo/hero/products/default.jpg"
        image_file = request.files.get("image_file")
        if image_file and image_file.filename:
            image = save_uploaded_image(image_file)
        conn = sqlite3.connect(app.config["DATABASE"])
        conn.execute(
            "INSERT INTO products (name, category, price, image, description, featured, popular) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                json.dumps(product_name, ensure_ascii=False),
                request.form.get("category", "tajines"),
                float(request.form.get("price", 0)),
                image,
                json.dumps(description, ensure_ascii=False),
                1 if request.form.get("featured") == "on" else 0,
                1 if request.form.get("popular") == "on" else 0,
            ),
        )
        conn.commit()
        conn.close()
        return redirect(url_for("admin_products"))
    return render_template("admin/product_form.html", product=None, categories=get_categories())


@app.route("/admin/products/<int:product_id>/edit", methods=["GET", "POST"])
def admin_product_edit(product_id):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    conn.close()
    product = get_product_data(row)
    if not product:
        return render_template("errors/404.html"), 404
    if request.method == "POST":
        names = {"fr": request.form.get("name_fr"), "ar": request.form.get("name_ar"), "en": request.form.get("name_en")}
        descriptions = {"fr": request.form.get("description_fr"), "ar": request.form.get("description_ar"), "en": request.form.get("description_en")}
        image = product["image"]
        if request.form.get("remove_image") == "on":
            if image.startswith("/uploads/"):
                (UPLOAD_PATH / Path(image).name).unlink(missing_ok=True)
            image = "/static/images/logo/hero/products/default.jpg"
        image_file = request.files.get("image_file")
        if image_file and image_file.filename:
            image = save_uploaded_image(image_file)
        conn = sqlite3.connect(app.config["DATABASE"])
        conn.execute(
            "UPDATE products SET name = ?, category = ?, price = ?, image = ?, description = ?, featured = ?, popular = ? WHERE id = ?",
            (json.dumps(names, ensure_ascii=False), request.form.get("category", "tajines"), float(request.form.get("price", 0)), image, json.dumps(descriptions, ensure_ascii=False), request.form.get("featured") == "on", request.form.get("popular") == "on", product_id),
        )
        conn.commit()
        conn.close()
        return redirect(url_for("admin_products"))
    return render_template("admin/product_form.html", product=product, categories=get_categories())


@app.route("/admin/products/<int:product_id>/delete", methods=["POST"])
def admin_product_delete(product_id):
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_products"))


@app.route("/admin/products/<int:product_id>/duplicate", methods=["POST"])
def admin_product_duplicate(product_id):
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.execute("INSERT INTO products (name, category, price, image, description, featured, popular, active, sort_order, details) SELECT name, category, price, image, description, featured, popular, active, sort_order, details FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_products"))


@app.route("/admin/products/<int:product_id>/toggle", methods=["POST"])
def admin_product_toggle(product_id):
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.execute("UPDATE products SET active = CASE WHEN COALESCE(active, 1) = 1 THEN 0 ELSE 1 END WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_products"))


@app.route("/admin/orders")
def admin_orders():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("admin/orders.html", orders=rows)


@app.route("/admin/orders/<int:order_id>/status", methods=["POST"])
def admin_order_status(order_id):
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.execute("UPDATE orders SET status = ? WHERE id = ?", (request.form.get("status", "new"), order_id))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_orders"))


@app.route("/admin/orders/<int:order_id>/delete", methods=["POST"])
def admin_order_delete(order_id):
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.execute("DELETE FROM orders WHERE id = ?", (order_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_orders"))


@app.route("/admin/reservations")
def admin_reservations():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM reservations ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("admin/reservations.html", reservations=rows)


@app.route("/admin/reservations/<int:reservation_id>/status", methods=["POST"])
def admin_reservation_status(reservation_id):
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.execute("UPDATE reservations SET status = ? WHERE id = ?", (request.form.get("status", "new"), reservation_id))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_reservations"))


@app.route("/admin/reservations/<int:reservation_id>/delete", methods=["POST"])
def admin_reservation_delete(reservation_id):
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.execute("DELETE FROM reservations WHERE id = ?", (reservation_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_reservations"))


@app.route("/admin/messages")
def admin_messages():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM contacts ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("admin/messages.html", messages=rows)


@app.route("/admin/settings", methods=["GET", "POST"])
def admin_settings():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    if request.method == "POST":
        conn = sqlite3.connect(app.config["DATABASE"])
        for key in ["company_name", "website_title", "website_description", "keywords", "hero_title_fr", "hero_title_ar", "hero_title_en", "hero_text_fr", "hero_text_ar", "hero_text_en", "hero_button_label", "hero_button_url", "phone", "location", "maps_url", "instagram", "facebook", "tiktok", "whatsapp", "email", "other_social", "business_hours", "footer_text", "copyright"]:
            value = request.form.get(key, "")
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
        for key in ["logo", "favicon", "og_image", "hero_image"]:
            image_file = request.files.get(key)
            if image_file and image_file.filename:
                conn.execute("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, save_uploaded_image(image_file)))
        conn.commit()
        conn.close()
        return redirect(url_for("admin_settings"))
    return render_template("admin/settings.html", settings=get_settings_dict())


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/admin/upload", methods=["POST"])
def admin_upload():
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"success": False, "message": "No file selected"}), 400
    try:
        return jsonify({"success": True, "url": save_uploaded_image(file)})
    except ValueError:
        return jsonify({"success": False, "message": "Only JPG, JPEG, PNG and WEBP images are supported."}), 400


@app.route("/404")
def page_not_found():
    return render_template("errors/404.html"), 404


@app.errorhandler(404)
def not_found(_):
    return render_template("errors/404.html"), 404


@app.errorhandler(500)
def internal_error(_):
    return render_template("errors/500.html"), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
