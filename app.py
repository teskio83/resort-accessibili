import os
from datetime import datetime
from types import SimpleNamespace

from flask import Flask, render_template, request, redirect, url_for, flash, session
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")

FRIENDS = ["Alessandro", "Antonio", "Laura", "Roberta"]

# -------------------------
# DATABASE
# -------------------------

def get_conn():
    return psycopg2.connect(os.environ.get("DATABASE_URL"))

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

def require_login():
    if "user" not in session:
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
            rows = cur.fetchall()

    resorts = [SimpleNamespace(**r) for r in rows]
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
                    RETURNING id
                """, (name, now, now))
                resort_id = cur.fetchone()[0]

                cur.execute("""
                    INSERT INTO activity_log (resort_id, user_name, action)
                    VALUES (%s,%s,%s)
                """, (resort_id, session["user"], "CREATED"))

        return redirect(url_for("index"))

    return render_template("form.html")

# -------------------------
# DELETE
# -------------------------

@app.route("/delete/<int:resort_id>", methods=["POST"])
def delete_resort(resort_id):
    if "user" not in session:
        return redirect(url_for("login"))

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO activity_log (resort_id, user_name, action)
                VALUES (%s,%s,%s)
            """, (resort_id, session["user"], "DELETED"))

            cur.execute("DELETE FROM resorts WHERE id=%s", (resort_id,))

    return redirect(url_for("index"))

# -------------------------
# ACTIVITY
# -------------------------

@app.route("/activity")
def activity():
    if "user" not in session:
        return redirect(url_for("login"))

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM activity_log ORDER BY created_at DESC LIMIT 50")
            logs = cur.fetchall()

    return render_template("activity.html", logs=logs)

# -------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
