import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")

FRIENDS = ["Alessandro", "Antonio", "Laura", "Roberta"]

def get_conn():
    return psycopg2.connect(os.environ["DATABASE_URL"])


# -------------------------
# SETUP MANUALE (una sola volta)
# -------------------------

@app.route("/setup")
def setup():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS resorts (
                id BIGSERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TIMESTAMPTZ,
                updated_at TIMESTAMPTZ
            );
            """)
    return "DB OK"


# -------------------------
# LOGIN
# -------------------------

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        name = request.form.get("name")
        if name in FRIENDS:
            session["user"] = name
            return redirect(url_for("index"))
    return render_template("login.html", friends=FRIENDS)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# -------------------------
# HOME
# -------------------------

@app.route("/")
def index():
    if "user" not in session:
        return redirect(url_for("login"))

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM resorts ORDER BY updated_at DESC NULLS LAST")
            resorts = cur.fetchall()

    return render_template("index.html", resorts=resorts)


# -------------------------
# NEW
# -------------------------

@app.route("/new", methods=["GET","POST"])
def new_resort():
    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        name = request.form.get("name")
        now = datetime.utcnow()

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO resorts (name, created_at, updated_at)
                    VALUES (%s,%s,%s)
                """, (name, now, now))

        return redirect(url_for("index"))

    return render_template("form.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
