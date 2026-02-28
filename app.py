from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from pathlib import Path
from datetime import datetime
import os
import psycopg2
from urllib.parse import urlparse

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "resorts.db"

app = Flask(__name__)
app.secret_key = "change-me-please"

REGIONS = [
    "Abruzzo","Basilicata","Calabria","Campania","Emilia-Romagna","Friuli-Venezia Giulia",
    "Lazio","Liguria","Lombardia","Marche","Molise","Piemonte","Puglia","Sardegna",
    "Sicilia","Toscana","Trentino-Alto Adige","Umbria","Valle d'Aosta","Veneto"
]
STATUS_CHOICES = [("valutare", "Da valutare"), ("interessante", "Interessante"), ("scartare", "Scartare")]

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

def db():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise Exception("DATABASE_URL non configurato")
    return psycopg2.connect(database_url)

def init_db():
    conn = db()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS resorts (
        id SERIAL PRIMARY KEY,
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

        created_at TIMESTAMP,
        updated_at TIMESTAMP
    );
    """)
    conn.commit()
    cur.close()
    conn.close()

def to_int(v):
    return 1 if v in ("1", "on", "true", "yes") else 0

def calc_access_score(row):
    # punteggio “a colpo d’occhio”
    total = len(FEATURES)
    have = 0
    for key, _label in FEATURES:
        have += 1 if row[key] else 0
    return have, total

@app.before_request
def _ensure_db():
    init_db()

@app.route("/", methods=["GET"])
def index():
    q = request.args.get("q", "").strip()
    region = request.args.get("region", "").strip()
    status = request.args.get("status", "").strip()
    only_access = request.args.get("only_access", "")  # "1" => con almeno basics
    keep = request.args.get("keep", "")               # "1" => solo da tenere in considerazione

    where = []
    params = []

    if q:
        where.append("(name ILIKE %s OR city ILIKE %s OR notes ILIKE %s)")
        like = f"%{q}%"
        params += [like, like, like]
    if region:
        where.append("region = ?")
        params.append(region)
    if status:
        where.append("status = ?")
        params.append(status)
    if keep == "1":
        where.append("keep_flag = 1")
    if only_access == "1":
        # minimo sindacale: carrozzina + (passerella OR job) + bagno H
        where.append("wheelchair_access = 1 AND beach_bathroom_h = 1 AND (beach_walkway = 1 OR beach_job_chair = 1)")

    sql = "SELECT * FROM resorts"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY updated_at DESC, created_at DESC"

    conn = db()
    rows = conn.execute(sql, params).fetchall()
    conn.close()

    resorts = []
    for r in rows:
        have, total = calc_access_score(r)
        resorts.append((r, have, total))

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
        now = datetime.utcnow().isoformat(timespec="seconds")
        data["created_at"] = now
        data["updated_at"] = now

        cols = ", ".join(data.keys())
        ph = ", ".join(["?"] * len(data))
        vals = list(data.values())

        conn = db()
        conn.execute(f"INSERT INTO resorts ({cols}) VALUES ({ph})", vals)
        conn.commit()
        conn.close()

        flash("Resort inserito ✅", "success")
        return redirect(url_for("index"))

    return render_template("form.html",
                           mode="new",
                           regions=REGIONS,
                           status_choices=STATUS_CHOICES,
                           features=FEATURES,
                           resort=None)

@app.route("/edit/<int:resort_id>", methods=["GET", "POST"])
def edit_resort(resort_id):
    conn = db()
    resort = conn.execute("SELECT * FROM resorts WHERE id = %s", (resort_id,)).fetchone()
    if not resort:
        conn.close()
        flash("Resort non trovato.", "danger")
        return redirect(url_for("index"))

    if request.method == "POST":
        data = parse_form(request.form)
        data["updated_at"] = datetime.utcnow().isoformat(timespec="seconds")

        sets = ", ".join([f"{k} = %s" for k in data.keys()])
        vals = list(data.values()) + [resort_id]
        conn.execute(f"UPDATE resorts SET {sets} WHERE id = %s", vals)
        conn.commit()
        conn.close()

        flash("Salvato ✅", "success")
        return redirect(url_for("view_resort", resort_id=resort_id))

    conn.close()
    return render_template("form.html",
                           mode="edit",
                           regions=REGIONS,
                           status_choices=STATUS_CHOICES,
                           features=FEATURES,
                           resort=resort)

@app.route("/view/<int:resort_id>")
def view_resort(resort_id):
    conn = db()
    resort = conn.execute("SELECT * FROM resorts WHERE id = %s", (resort_id,)).fetchone()
    conn.close()
    if not resort:
        flash("Resort non trovato.", "danger")
        return redirect(url_for("index"))

    have, total = calc_access_score(resort)
    return render_template("view.html", resort=resort, features=FEATURES, have=have, total=total)

@app.route("/delete/<int:resort_id>", methods=["POST"])
def delete_resort(resort_id):
    conn = db()
    conn.execute("DELETE FROM resorts WHERE id = %s", (resort_id,))
    conn.commit()
    conn.close()
    flash("Eliminato 🗑️", "warning")
    return redirect(url_for("index"))

def parse_form(f):
    data = {
        "name": f.get("name", "").strip(),
        "region": f.get("region", "").strip(),
        "city": f.get("city", "").strip(),
        "website": f.get("website", "").strip(),
        "phone": f.get("phone", "").strip(),
        "email": f.get("email", "").strip(),

        "price_week": f.get("price_week", "").strip() or None,
        "price_period": f.get("price_period", "").strip(),
        "price_notes": f.get("price_notes", "").strip(),

        "status": f.get("status", "valutare"),
        "keep_flag": to_int(f.get("keep_flag")),

        "notes": f.get("notes", "").strip(),
    }

    # checkbox accessibilità
    for key, _label in FEATURES:
        data[key] = to_int(f.get(key))

    # normalizza price_week in float se possibile
    if data["price_week"] is not None:
        try:
            data["price_week"] = float(str(data["price_week"]).replace(",", "."))
        except ValueError:
            data["price_week"] = None

    if not data["name"]:
        data["name"] = "Senza nome"
    return data

if __name__ == "__main__":
    # per usarla dal telefono sulla stessa rete: host="0.0.0.0"
    app.run(host="0.0.0.0", port=5000, debug=True)
