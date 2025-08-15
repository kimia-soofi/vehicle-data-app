from flask import Flask, render_template, request, redirect, url_for, send_file
import sqlite3
import os
import pandas as pd
import jdatetime
from datetime import datetime

app = Flask(__name__)
DB_FILE = "data.db"

# ایجاد جدول‌ها اگر وجود نداشت
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS form_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            car_type TEXT,
            vin TEXT,
            mileage TEXT,
            notes TEXT,
            eval_date TEXT,
            status TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# تبدیل تاریخ میلادی به شمسی
def gregorian_to_jalali(g_date_str):
    if not g_date_str:
        return ""
    try:
        g_date = datetime.strptime(g_date_str, "%Y-%m-%d")
        j_date = jdatetime.date.fromgregorian(date=g_date)
        return f"{j_date.year:04d}-{j_date.month:02d}-{j_date.day:02d}"
    except:
        return g_date_str

# صفحه فرم همکاران
@app.route("/", methods=["GET", "POST"])
def form_page():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    cars = c.execute("SELECT name FROM vehicles").fetchall()
    conn.close()

    if request.method == "POST":
        car_type = request.form["car_type"]
        vin = request.form["vin"]
        mileage = request.form["mileage"]
        notes = request.form["notes"]
        eval_date = request.form["eval_date"]  # تاریخ شمسی مستقیم ذخیره می‌شود

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("""
            INSERT INTO form_data (car_type, vin, mileage, notes, eval_date, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (car_type, vin, mileage, notes, eval_date, "pending"))
        conn.commit()
        conn.close()
        return redirect(url_for("form_page"))

    return render_template("form.html", cars=[c[0] for c in cars])

# پنل ادمین
@app.route("/admin")
def admin_panel():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    data = c.execute("SELECT * FROM form_data").fetchall()
    conn.close()

    # تبدیل تاریخ‌ها به شمسی
    data_jalali = []
    for row in data:
        row = list(row)
        row[5] = gregorian_to_jalali(row[5]) if "-" in row[5] else row[5]
        data_jalali.append(row)

    return render_template("admin.html", data=data_jalali)

# حذف تمام رکوردها
@app.route("/admin/delete_all", methods=["POST"])
def delete_all():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM form_data")
    conn.commit()
    conn.close()
    return redirect(url_for("admin_panel"))

# مدیریت خودروها
@app.route("/admin/cars", methods=["GET", "POST"])
def manage_cars():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    if request.method == "POST":
        if "add_car" in request.form:
            car_name = request.form["car_name"]
            c.execute("INSERT INTO vehicles (name) VALUES (?)", (car_name,))
        elif "delete_car" in request.form:
            car_id = request.form["car_id"]
            c.execute("DELETE FROM vehicles WHERE id=?", (car_id,))
        conn.commit()

    cars = c.execute("SELECT * FROM vehicles").fetchall()
    conn.close()
    return render_template("manage_cars.html", cars=cars)

# دانلود اکسل
@app.route("/admin/download_excel")
def download_excel():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM form_data", conn)
    conn.close()

    df["eval_date"] = df["eval_date"].apply(lambda d: gregorian_to_jalali(d) if "-" in d else d)
    file_path = "form_data.xlsx"
    df.to_excel(file_path, index=False)

    return send_file(file_path, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
