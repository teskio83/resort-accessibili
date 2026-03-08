import os
import imaplib
import email
from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from flask import Flask, render_template, request, redirect, url_for, flash, session
import psycopg2
from psycopg2.extras import RealDictCursor
import urllib.parse

def to_italy_time(dt):
    if not dt:
        return None
    return dt.astimezone(ZoneInfo("Europe/Rome"))

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

def fetch_emails():

    user = os.environ.get("GMAIL_USER")
    password = os.environ.get("GMAIL_PASS")

    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(user, password)
    mail.select("inbox")

    status, messages = mail.search(None, "ALL")
    email_ids = messages[0].split()[-20:]

    results = []

    for eid in reversed(email_ids):

        status, msg_data = mail.fetch(eid, "(RFC822)")

        msg = email.message_from_bytes(msg_data[0][1])

        subject = msg.get("subject")
        sender = msg.get("from")
        date = msg.get("date")

        body = ""

        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode(errors="ignore")
                    break
        else:
            body = msg.get_payload(decode=True).decode(errors="ignore")

        results.append({
            "subject": subject,
            "from": sender,
            "date": date,
            "body": body[:500]
        })

    mail.logout()

    return results
    
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

            cur.execute("""
            CREATE TABLE IF NOT EXISTS notification_reads (
                id BIGSERIAL PRIMARY KEY,
                activity_id BIGINT REFERENCES resort_activity(id) ON DELETE CASCADE,
                user_name TEXT NOT NULL,
                read_at TIMESTAMPTZ
            );
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS resort_messages (
                id BIGSERIAL PRIMARY KEY,
                resort_id BIGINT REFERENCES resorts(id) ON DELETE CASCADE,
                user_name TEXT NOT NULL,
                subject TEXT,
                body TEXT,
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
        "region": (f.get("region") or "").strip(),
        "city": (f.get("city") or "").strip(),
        "website": (f.get("website") or "").strip(),
        "phone": (f.get("phone") or "").strip(),
        "email": (f.get("email") or "").strip(),
        "price_week": (f.get("price_week") or "").strip(),
        "price_period": (f.get("price_period") or "").strip(),
        "price_notes": (f.get("price_notes") or "").strip(),
        "status": f.get("status") or "valutare",
        "keep_flag": to_bool(f.get("keep_flag")),
        "notes": (f.get("notes") or "").strip(),
    }

    for key, _ in FEATURES:
        data[key] = to_bool(f.get(key))

    if data["price_week"]:
        try:
            data["price_week"] = float(str(data["price_week"]).replace(",", "."))
        except ValueError:
            data["price_week"] = None
    else:
        data["price_week"] = None

    return data

def calc_access_score(resort):
    total = len(FEATURES)
    have = sum(1 for k,_ in FEATURES if getattr(resort, k))
    return have, total

def get_unread_notifications(user):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            cur.execute("""
                SELECT ra.*, r.name
                FROM resort_activity ra
                JOIN resorts r ON r.id = ra.resort_id
                WHERE ra.user_name != %s
                AND ra.id NOT IN (
                    SELECT activity_id
                    FROM notification_reads
                    WHERE user_name = %s
                )
                ORDER BY ra.created_at DESC
                LIMIT 10
            """, (user, user))
            
            rows = cur.fetchall()

            for r in rows:
                r["created_at"] = to_italy_time(r["created_at"])

            return rows

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

    notifications = get_unread_notifications(session["user"])
    notif_count = len(notifications)

    q = request.args.get("q", "").strip()
    region = request.args.get("region", "")
    status = request.args.get("status", "")
    only_access = request.args.get("only_access")
    keep = request.args.get("keep")

    query = "SELECT * FROM resorts WHERE 1=1"
    params = []

    if q:
        query += " AND (LOWER(name) LIKE %s OR LOWER(city) LIKE %s OR LOWER(notes) LIKE %s)"
        params += [f"%{q.lower()}%", f"%{q.lower()}%", f"%{q.lower()}%"]

    if region:
        query += " AND region=%s"
        params.append(region)

    if status:
        query += " AND status=%s"
        params.append(status)

    if only_access == "1":
        query += " AND wheelchair_access = TRUE"

    if keep == "1":
        query += " AND keep_flag = TRUE"

    query += " ORDER BY CASE WHEN keep_flag = TRUE THEN 0 WHEN status='interessante' THEN 1 WHEN status='valutare' THEN 2 WHEN status='scartare' THEN 3 ELSE 4 END, updated_at DESC NULLS LAST"

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

    resorts = []
    for r in rows:
        obj = as_obj(r)
        have, total = calc_access_score(obj)
        resorts.append((obj, have, total))

    filters = {
        "q": q,
        "region": region,
        "status": status,
        "only_access": only_access,
        "keep": keep
    }

    return render_template(
        "index.html",
        resorts=resorts,
        regions=REGIONS,
        status_choices=STATUS_CHOICES,
        filters=filters,
        notif_count=notif_count
    )
        
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

            # storico attività
            cur.execute(
                "SELECT * FROM resort_activity WHERE resort_id=%s ORDER BY created_at DESC LIMIT 3",
                (resort_id,)
            )
            activity = cur.fetchall()

            for a in activity:
                a["created_at"] = to_italy_time(a["created_at"])

            # 📩 messaggi collegati al resort
            cur.execute("""
                SELECT *
                FROM resort_messages
                WHERE resort_id=%s
                ORDER BY created_at DESC
            """, (resort_id,))

            messages = cur.fetchall()

            for m in messages:
                m["created_at"] = to_italy_time(m["created_at"])

    if not r:
        return redirect(url_for("index"))

    resort = as_obj(r)
    have, total = calc_access_score(resort)

    map_query = f"{resort.name} {(resort.city or '')} {(resort.region or '')}".strip()
    map_url = "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote_plus(map_query)

    return render_template(
        "view.html",
        resort=resort,
        features=FEATURES,
        have=have,
        total=total,
        activity=activity,
        messages=messages,
        map_url=map_url
    )
    
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
                    "price_period",
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
                else:
                    action_text = "modifica"
                
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

@app.route("/resort/<int:resort_id>/add_message", methods=["POST"])
def add_message(resort_id):

    if "user" not in session:
        return redirect(url_for("login"))

    subject = (request.form.get("subject") or "").strip()
    body = (request.form.get("body") or "").strip()

    with get_conn() as conn:
        with conn.cursor() as cur:

            cur.execute("""
                INSERT INTO resort_messages
                (resort_id, user_name, subject, body, created_at)
                VALUES (%s,%s,%s,%s,NOW())
            """, (
                resort_id,
                session["user"],
                subject,
                body
            ))

            # registriamo anche nello storico attività
            cur.execute("""
                INSERT INTO resort_activity
                (resort_id, action, user_name, created_at)
                VALUES (%s,%s,%s,NOW())
            """, (
                resort_id,
                "messaggio",
                session["user"]
            ))

    return redirect(url_for("view_resort", resort_id=resort_id))

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

@app.route("/notifications")
def notifications():

    if "user" not in session:
        return redirect(url_for("login"))

    user = session["user"]

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            cur.execute("""
                SELECT ra.*, r.name as resort_name
                FROM resort_activity ra
                JOIN resorts r ON r.id = ra.resort_id
                ORDER BY ra.created_at DESC
                LIMIT 30
            """)

            activities = cur.fetchall()

            for a in activities:
                a["created_at"] = to_italy_time(a["created_at"])

            # segna come lette
            for a in activities:
                cur.execute("""
                    INSERT INTO notification_reads (activity_id, user_name, read_at)
                    VALUES (%s,%s,NOW())
                    ON CONFLICT DO NOTHING
                """, (a["id"], user))

    return render_template(
        "notifications.html",
        activities=activities
    )

@app.route("/emails")
def emails():

    if "user" not in session:
        return redirect(url_for("login"))

    emails = fetch_emails()

    return render_template(
        "emails.html",
        emails=emails
    )
    
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
