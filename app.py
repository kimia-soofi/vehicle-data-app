from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os

app = Flask(__name__)

DB_FILE = "database.db"

# --- ایجاد دیتابیس در اولین اجرا ---
def init_db():
    if not os.path.exists(DB_FILE):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE vehicle_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            vehicle_type TEXT,
            vin TEXT,
            mileage TEXT,
            plate_number TEXT,
            customer_name TEXT,
            phone_number TEXT
        )
        """)
        conn.commit()
        conn.close()

@app.route("/", methods=["GET", "POST"])
def form():
    if request.method == "POST":
        date = request.form.get("date")
        vehicle_type = request.form.get("vehicle_type")
        vin = request.form.get("vin")
        mileage = request.form.get("mileage")
        plate_number = request.form.get("plate_number")
        customer_name = request.form.get("customer_name")
        phone_number = request.form.get("phone_number")

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO vehicle_data (date, vehicle_type, vin, mileage, plate_number, customer_name, phone_number)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (date, vehicle_type, vin, mileage, plate_number, customer_name, phone_number))
        conn.commit()
        conn.close()

        return redirect(url_for("success"))

    return render_template("form.html")

@app.route("/success")
def success():
    return "<h2>اطلاعات با موفقیت ذخیره شد ✅</h2>"

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
