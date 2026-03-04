import os
from datetime import datetime
import pytz
from types import SimpleNamespace

from flask import Flask, render_template, request, redirect, url_for, flash, session
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-please")

ALLOWED_USERS = ["ALESSANDRO", "ANTONIO", "LAURA", "ROBERTA"]

REGIONS = [
    "Abruzzo","Basilicata","Calabria","Campania","Emilia-Romagna","Friuli-Venezia Giulia",
    "Lazio","Liguria","Lombardia","Marche","Molise","Piemonte","Puglia","Sardegna",
    "Sicilia","Toscana","Trentino-Alto Adige","Umbria","Valle d'Aosta","Veneto"
]

STATUS_CHOICES = [("valutare", "Da valutare"), ("interessante", "Interessante"), ("scartare", "Scartare")]

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

def get_conn():
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL non configurato")
    return psycopg2.connect(dsn, sslmode="require")

def localtime(dt):
    if not dt:
        return None
    tz = pytz.timezone("Europe/Rome")
    return dt.astimezone(tz)

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
                created_by TEXT,
                updated_by TEXT,
                created_at TIMESTAMPTZ,
                updated_at TIMESTAMPTZ
            );
            """)

            # Tabella attività
            cur.execute("""
            CREATE TABLE IF NOT EXISTS resort_activity (
                id BIGSERIAL PRIMARY KEY,
                resort_id BIGINT REFERENCES resorts(id) ON DELETE CASCADE,
                action TEXT,
                user_name TEXT,
                created_at TIMESTAMPTZ
            );
            """)

try:
    init_db()
except Exception as e:
    print("DB INIT ERROR:", e)

def as_obj(d):
    return SimpleNamespace(**d)

def to_bool(v):
    return str(v).lower() in ("1","on","true","yes")

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
        "status": f.get("status") or "valutare",
        "keep_flag": to_bool(f.get("keep_flag")),
        "notes": (f.get("notes") or "").strip() or None,
    }

    for key, _ in FEATURES:
        data[key] = to_bool(f.get(key))

    if data["price_week"]:
        try:
            data["price_week"] = float(str(data["price_week"]).replace(",", "."))
        except ValueError:
            data["price_week"] = None

    return data

def calc_access_score(resort):
    total = len(FEATURES)
    have = sum(1 for k,_ in FEATURES if getattr(resort, k))
    return have, total


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].upper()
        if username in ALLOWED_USERS:
            session["user"] = username
            return redirect(url_for("index"))
    return render_template("login.html", users=ALLOWED_USERS)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
def index():
    if "user" not in session:
        return redirect(url_for("login"))

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM resorts ORDER BY updated_at DESC NULLS LAST")
            rows = cur.fetchall()

    resorts = []
    for r in rows:
        obj = as_obj(r)
        have, total = calc_access_score(obj)
        resorts.append((obj, have, total))

    return render_template("index.html", resorts=resorts,
                           regions=REGIONS, status_choices=STATUS_CHOICES,
                           filters={})

@app.route("/new", methods=["GET","POST"])
def new_resort():
    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        data = parse_form(request.form)
        now = datetime.utcnow()
        data["created_at"] = now
        data["updated_at"] = now
        data["created_by"] = session["user"]
        data["updated_by"] = session["user"]

        cols = list(data.keys())
        placeholders = ", ".join(["%s"] * len(cols))
        values = [data[c] for c in cols]

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"INSERT INTO resorts ({','.join(cols)}) VALUES ({placeholders}) RETURNING id",
                    values
                )
                new_id = cur.fetchone()[0]

                cur.execute(
                    "INSERT INTO resort_activity (resort_id, action, user_name, created_at) VALUES (%s,%s,%s,%s)",
                    (new_id, "creazione", session["user"], now)
                )

        return redirect(url_for("index"))

    return render_template("form.html", mode="new",
                           regions=REGIONS, status_choices=STATUS_CHOICES,
                           features=FEATURES, resort=None)

@app.route("/view/<int:resort_id>")
def view_resort(resort_id):
    if "user" not in session:
        return redirect(url_for("login"))

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM resorts WHERE id=%s", (resort_id,))
            r = cur.fetchone()

            cur.execute(
                "SELECT * FROM resort_activity WHERE resort_id=%s ORDER BY created_at DESC LIMIT 3",
                (resort_id,)
            )
            activity = cur.fetchall()
            
            for a in activity:
                a["created_at"] = to_italy_time(a["created_at"])
                
    if not r:
        return redirect(url_for("index"))

    resort = as_obj(r)
    have, total = calc_access_score(resort)

    return render_template("view.html", resort=resort,
                           features=FEATURES, have=have,
                           total=total, activity=activity)

@app.route("/edit/<int:resort_id>", methods=["GET","POST"])
def edit_resort(resort_id):
    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        data = parse_form(request.form)

        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:

                # 🔎 Recupero dati vecchi
                cur.execute("SELECT * FROM resorts WHERE id=%s", (resort_id,))
                old = cur.fetchone()
                if not old:
                    return redirect(url_for("index"))

                changes = []

                # Campi che vogliamo tracciare
                tracked_fields = [
                    "price_week",
                    "status",
                    "keep_flag",
                    "notes"
                ]

                for field in tracked_fields:
                    old_val = old.get(field)
                    new_val = data.get(field)

                    if old_val != new_val:
                        changes.append(
                            f"{field}: {old_val} → {new_val}"
                        )

                # Aggiorno resort
                data["updated_at"] = datetime.utcnow()
                data["updated_by"] = session["user"]

                cols = list(data.keys())
                sets = ", ".join([f"{c}=%s" for c in cols])
                values = [data[c] for c in cols] + [resort_id]

                cur.execute(f"UPDATE resorts SET {sets} WHERE id=%s", values)

                # Se ci sono modifiche reali, le salvo
                if changes:
                    action_text = "modifica\n" + "\n".join(changes)

                    cur.execute(
                        "INSERT INTO resort_activity (resort_id, action, user_name, created_at) VALUES (%s,%s,%s,%s)",
                        (resort_id, action_text, session["user"], datetime.utcnow())
                    )

        return redirect(url_for("view_resort", resort_id=resort_id))

    # GET
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM resorts WHERE id=%s", (resort_id,))
            r = cur.fetchone()

    return render_template("form.html",
                           mode="edit",
                           regions=REGIONS,
                           status_choices=STATUS_CHOICES,
                           features=FEATURES,
                           resort=as_obj(r))

@app.route("/delete/<int:resort_id>", methods=["POST"])
def delete_resort(resort_id):
    if "user" not in session:
        return redirect(url_for("login"))

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM resorts WHERE id=%s", (resort_id,))

    return redirect(url_for("index"))

@app.route("/resort/<int:resort_id>/history")
def resort_history(resort_id):
    if "user" not in session:
        return redirect(url_for("login"))

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT name FROM resorts WHERE id=%s", (resort_id,))
            resort = cur.fetchone()

            if not resort:
                return redirect(url_for("index"))

            cur.execute("""
                SELECT *
                FROM resort_activity
                WHERE resort_id=%s
                ORDER BY created_at DESC
            """, (resort_id,))
            activities = cur.fetchall()
            for a in activities:
                a["created_at"] = to_italy_time(a["created_at"])

    return render_template(
        "activity.html",
        activities=activities,
        resort_name=resort["name"],
        resort_id=resort_id
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
