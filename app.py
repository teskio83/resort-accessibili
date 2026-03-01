import os
from datetime import datetime
from types import SimpleNamespace

from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-please")


# =========================
# CONFIG
# =========================

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
    ("beach_bathroom_h", "Bagno H"),
    ("beach_job_chair", "Sedia JOB"),
    ("accessible_room", "Camera accessibile"),
    ("restaurant_accessible", "Ristorante accessibile"),
    ("pool_accessible", "Piscina accessibile"),
    ("lift", "Ascensore"),
    ("disabled_parking", "Parcheggio disabili"),
    ("step_free_paths", "Percorsi senza barriere"),
    ("staff_assistance", "Assistenza inclusiva"),
]


# =========================
# DATABASE
# =========================

def get_conn():
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL non configurato")
    return psycopg2.connect(dsn, sslmode="require")


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

            cur.execute("""
            CREATE TABLE IF NOT EXISTS activity_log (
                id BIGSERIAL PRIMARY KEY,
                resort_id BIGINT REFERENCES resorts(id) ON DELETE CASCADE,
                action TEXT,
                description TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            """)


# =========================
# UTILITIES
# =========================

def as_obj(d):
    return SimpleNamespace(**d)

def to_bool(v):
    return str(v).lower() in ("1","on","true","yes")

def parse_form(f):
    data = {
        "name": (f.get("name") or "").strip() or "Senza nome",
        "region": f.get("region") or None,
        "city": f.get("city") or None,
        "website": f.get("website") or None,
        "phone": f.get("phone") or None,
        "email": f.get("email") or None,
        "price_week": f.get("price_week") or None,
        "price_period": f.get("price_period") or None,
        "price_notes": f.get("price_notes") or None,
        "status": f.get("status") or "valutare",
        "keep_flag": to_bool(f.get("keep_flag")),
        "notes": f.get("notes") or None
    }

    for key, _ in FEATURES:
        data[key] = to_bool(f.get(key))

    if data["price_week"]:
        try:
            data["price_week"] = float(str(data["price_week"]).replace(",", "."))
        except:
            data["price_week"] = None

    return data

def calc_access_score(resort):
    total = len(FEATURES)
    have = sum(1 for k,_ in FEATURES if getattr(resort, k))
    return have, total


# =========================
# ROUTES
# =========================

@app.route("/")
def index():

    q = (request.args.get("q") or "").strip()

    where = []
    params = []

    if q:
        where.append("(name ILIKE %s OR city ILIKE %s OR notes ILIKE %s OR region ILIKE %s)")
        like = f"%{q}%"
        params += [like, like, like, like]

    sql = "SELECT * FROM resorts"

    if where:
        sql += " WHERE " + " AND ".join(where)

    sql += " ORDER BY updated_at DESC NULLS LAST, created_at DESC NULLS LAST"

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    resorts = []
    for r in rows:
        obj = as_obj(r)
        have,total = calc_access_score(obj)
        resorts.append((obj,have,total))

    return render_template("index.html",
                           resorts=resorts,
                           regions=REGIONS,
                           status_choices=STATUS_CHOICES,
                           filters={"q": q})


@app.route("/new", methods=["GET","POST"])
def new_resort():
    if request.method == "POST":
        data = parse_form(request.form)
        now = datetime.utcnow()
        data["created_at"] = now
        data["updated_at"] = now

        cols = list(data.keys())
        placeholders = ", ".join(["%s"]*len(cols))
        values = [data[c] for c in cols]

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"INSERT INTO resorts ({','.join(cols)}) VALUES ({placeholders}) RETURNING id",
                    values
                )
                resort_id = cur.fetchone()[0]

                cur.execute("""
                    INSERT INTO activity_log (resort_id,action,description)
                    VALUES (%s,%s,%s)
                """,(resort_id,"CREATED",f"Creato resort: {data['name']}"))

        flash("Resort inserito ✅","success")
        return redirect(url_for("index"))

    return render_template("form.html",
                           mode="new",
                           regions=REGIONS,
                           status_choices=STATUS_CHOICES,
                           features=FEATURES,
                           resort=None)


@app.route("/delete/<int:resort_id>",methods=["POST"])
def delete_resort(resort_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM resorts WHERE id=%s",(resort_id,))

    flash("Eliminato 🗑️","warning")
    return redirect(url_for("index"))


# =========================
# LOCAL RUN
# =========================

if __name__=="__main__":
    port=int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0",port=port)
