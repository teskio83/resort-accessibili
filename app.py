import os
from datetime import datetime
from types import SimpleNamespace

from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-please")

REGIONS = [
    "Abruzzo","Basilicata","Calabria","Campania","Emilia-Romagna","Friuli-Venezia Giulia",
    "Lazio","Liguria","Lombardia","Marche","Molise","Piemonte","Puglia","Sardegna",
    "Sicilia","Toscana","Trentino-Alto Adige","Umbria","Valle d'Aosta","Veneto"
]

STATUS_CHOICES = [
    ("valutare", "Da valutare"),
    ("interessante", "Interessante"),
    ("scartare", "Scartare")
]

FEATURES = [
    ("wheelchair_access", "Accessibile in carrozzina"),
    ("beach_walkway", "Passerella per il mare"),
    ("beach_bathroom_h", "Bagno H (spiaggia/struttura)"),
    ("beach_job_chair", "Sedia JOB"),
    ("accessible_room", "Camera accessibile"),
    ("restaurant_accessible", "Ristorante accessibile"),
    ("pool_accessible", "Piscina accessibile"),
    ("lift", "Ascensore"),
    ("disabled_parking", "Parcheggio disabili"),
    ("step_free_paths", "Percorsi senza barriere"),
    ("staff_assistance", "Assistenza/servizi inclusivi"),
]

# -------------------------
# DB helpers (PostgreSQL only)
# -------------------------

def get_conn():
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL mancante (Render -> Environment).")
    # Render fornisce URL già pronto per psycopg2
    return psycopg2.connect(dsn)

def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS resorts (
                id BIGSERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                region TEXT,
                city TEXT,
                website TEXT,
                phone TEXT,
                email TEXT,

                price_week NUMERIC,
                price_period TEXT,
                price_notes TEXT,

                status TEXT DEFAULT 'valutare',
                keep_flag BOOLEAN DEFAULT FALSE,

                notes TEXT,

                wheelchair_access BOOLEAN DEFAULT FALSE,
                beach_walkway BOOLEAN DEFAULT FALSE,
                beach_bathroom_h BOOLEAN DEFAULT FALSE,
                beach_job_chair BOOLEAN DEFAULT FALSE,
                accessible_room BOOLEAN DEFAULT FALSE,
                restaurant_accessible BOOLEAN DEFAULT FALSE,
                pool_accessible BOOLEAN DEFAULT FALSE,
                lift BOOLEAN DEFAULT FALSE,
                disabled_parking BOOLEAN DEFAULT FALSE,
                step_free_paths BOOLEAN DEFAULT FALSE,
                staff_assistance BOOLEAN DEFAULT FALSE,

                created_at TIMESTAMPTZ,
                updated_at TIMESTAMPTZ
            );
            """)
            # indicini utili per filtri/ricerche
            cur.execute("CREATE INDEX IF NOT EXISTS idx_resorts_region ON resorts(region);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_resorts_status ON resorts(status);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_resorts_updated ON resorts(updated_at);")

def as_obj(d: dict):
    """Rende compatibili i template esistenti (r.name invece di r['name'])."""
    return SimpleNamespace(**d)

def to_bool(v):
    return str(v).lower() in ("1", "on", "true", "yes")

def parse_form(f):
    data = {
        "name": (f.get("name") or "").strip() or "Senza nome",
        "region": (f.get("region") or "").strip() or None,
        "city": (f.get("city") or "").strip() or None,
        "website": (f.get("website") or "").strip() or None,
        "phone": (f.get("phone") or "").strip() or None,
        "email": (f.get("email") or "").strip() or None,

        "price_week": (f.get("price_week") or "").strip() or None,
        "price_period": (f.get("price_period") or "").strip() or None,
        "price_notes": (f.get("price_notes") or "").strip() or None,

        "status": (f.get("status") or "valutare").strip(),
        "keep_flag": to_bool(f.get("keep_flag")),

        "notes": (f.get("notes") or "").strip() or None,
    }

    # checkbox accessibilità
    for key, _label in FEATURES:
        data[key] = to_bool(f.get(key))

    # normalizza price_week
    if data["price_week"] is not None:
        try:
            data["price_week"] = float(str(data["price_week"]).replace(",", "."))
        except ValueError:
            data["price_week"] = None

    return data

def calc_access_score(obj):
    total = len(FEATURES)
    have = 0
    for key, _label in FEATURES:
        have += 1 if getattr(obj, key, False) else 0
    return have, total

# Inizializza tabella all'avvio (safe anche su deploy/restart)
try:
    init_db()
except Exception as e:
    # in Render i log li vedi nella sezione Logs
    print("DB init error:", e)

# -------------------------
# Routes
# -------------------------

@app.route("/", methods=["GET"])
def index():
    q = (request.args.get("q") or "").strip()
    region = (request.args.get("region") or "").strip()
    status = (request.args.get("status") or "").strip()
    only_access = request.args.get("only_access", "")  # "1"
    keep = request.args.get("keep", "")               # "1"

    where = []
    params = []

    if q:
        where.append("(name ILIKE %s OR city ILIKE %s OR notes ILIKE %s)")
        like = f"%{q}%"
        params += [like, like, like]
    if region:
        where.append("region = %s")
        params.append(region)
    if status:
        where.append("status = %s")
        params.append(status)
    if keep == "1":
        where.append("keep_flag = TRUE")
    if only_access == "1":
        where.append("""
            wheelchair_access = TRUE
            AND beach_bathroom_h = TRUE
            AND (beach_walkway = TRUE OR beach_job_chair = TRUE)
        """)

    sql = "SELECT * FROM resorts"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY updated_at DESC NULLS LAST, created_at DESC NULLS LAST"

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    resorts = []
    for d in rows:
        obj = as_obj(d)
        have, total = calc_access_score(obj)
        resorts.append((obj, have, total))

    return render_template(
        "index.html",
        resorts=resorts,
        regions=REGIONS,
        status_choices=STATUS_CHOICES,
        filters={"q": q, "region": region, "status": status, "only_access": only_access, "keep": keep}
    )

@app.route("/new", methods=["GET", "POST"])
def new_resort():
    if request.method == "POST":
        data = parse_form(request.form)
        now = datetime.utcnow()

        data["created_at"] = now
        data["updated_at"] = now

        cols = list(data.keys())
        placeholders = ", ".join(["%s"] * len(cols))
        colnames = ", ".join(cols)
        values = [data[c] for c in cols]

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"INSERT INTO resorts ({colnames}) VALUES ({placeholders})",
                    values
                )

        flash("Resort inserito ✅", "success")
        return redirect(url_for("index"))

    return render_template(
        "form.html",
        mode="new",
        regions=REGIONS,
        status_choices=STATUS_CHOICES,
        features=FEATURES,
        resort=None
    )

@app.route("/edit/<int:resort_id>", methods=["GET", "POST"])
def edit_resort(resort_id):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM resorts WHERE id = %s", (resort_id,))
            d = cur.fetchone()

    if not d:
        flash("Resort non trovato.", "danger")
        return redirect(url_for("index"))

    resort = as_obj(d)

    if request.method == "POST":
        data = parse_form(request.form)
        data["updated_at"] = datetime.utcnow()

        cols = list(data.keys())
        sets = ", ".join([f"{c} = %s" for c in cols])
        values = [data[c] for c in cols] + [resort_id]

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(f"UPDATE resorts SET {sets} WHERE id = %s", values)

        flash("Salvato ✅", "success")
        return redirect(url_for("view_resort", resort_id=resort_id))

    return render_template(
        "form.html",
        mode="edit",
        regions=REGIONS,
        status_choices=STATUS_CHOICES,
        features=FEATURES,
        resort=resort
    )

@app.route("/view/<int:resort_id>")
def view_resort(resort_id):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM resorts WHERE id = %s", (resort_id,))
            d = cur.fetchone()

    if not d:
        flash("Resort non trovato.", "danger")
        return redirect(url_for("index"))

    resort = as_obj(d)
    have, total = calc_access_score(resort)
    return render_template("view.html", resort=resort, features=FEATURES, have=have, total=total)

@app.route("/delete/<int:resort_id>", methods=["POST"])
def delete_resort(resort_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM resorts WHERE id = %s", (resort_id,))

    flash("Eliminato 🗑️", "warning")
    return redirect(url_for("index"))

if __name__ == "__main__":
    # in locale
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
