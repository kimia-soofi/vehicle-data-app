from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import os, json
from datetime import datetime
import pandas as pd
import io
from config import ADMIN_USERNAME as CONF_USER, ADMIN_PASSWORD as CONF_PASS, CAR_MODELS
from openpyxl import Workbook
# ----- تنظیمات پایه
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change_this_secret_key")

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", CONF_USER)
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", CONF_PASS)

DATA_FOLDER = "data"
os.makedirs(DATA_FOLDER, exist_ok=True)

# ----- صفحه فرود
@app.route("/")
def index():
    return render_template("index.html")

# ----- فرم همکاران
@app.route("/staff", methods=["GET", "POST"])
def staff_form():
    if request.method == "POST":
        vehicle_type = request.form.get("vehicle_type")
        vin = request.form.get("vin")
        eval_date = request.form.get("eval_date")
        start_time = request.form.get("start_time")
        end_time = request.form.get("end_time")
        start_km = request.form.get("start_km")
        end_km = request.form.get("end_km")
        distance = request.form.get("distance")
        evaluator = request.form.get("evaluator")
        rows_json = request.form.get("rows_json", "[]")
        try:
            rows = json.loads(rows_json)
        except json.JSONDecodeError:
            rows = []

        car_folder = os.path.join(DATA_FOLDER, vehicle_type.upper())
        os.makedirs(car_folder, exist_ok=True)

        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        payload = {
            "meta": {
                "vehicle_type": vehicle_type,
                "vin": vin,
                "eval_date": eval_date,
                "start_time": start_time,
                "end_time": end_time,
                "start_km": start_km,
                "end_km": end_km,
                "distance": distance,
                "evaluator": evaluator,
                "submitted_at": datetime.now().isoformat(timespec="seconds"),
                "status": "pending"
            },
            "observations": rows
        }
        with open(os.path.join(car_folder, filename), "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        flash("فرم با موفقیت ذخیره شد ✅")
        return redirect(url_for("staff_form"))

    return render_template("staff_form.html", car_models=CAR_MODELS)

# ----- ورود ادمین
@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        u = request.form.get("username", "")
        p = request.form.get("password", "")
        if u == ADMIN_USERNAME and p == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin_panel"))
        flash("نام کاربری یا رمز عبور اشتباه است ❌")
        return redirect(url_for("admin_login"))
    return render_template("admin_login.html")

# ----- پنل ادمین
@app.route("/admin/panel")
def admin_panel():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    all_data = {}
    for model in CAR_MODELS:
        car_folder = os.path.join(DATA_FOLDER, model.upper())
        records = []
        if os.path.isdir(car_folder):
            for fname in sorted(os.listdir(car_folder)):
                if fname.lower().endswith(".json"):
                    fpath = os.path.join(car_folder, fname)
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        data["_filename"] = fname
                        data["_model"] = model
                        records.append(data)
        all_data[model] = list(reversed(records))
    return render_template("admin_panel.html", all_data=all_data)

# ----- حذف رکورد
@app.route("/admin/delete/<model>/<fname>", methods=["POST"])
def admin_delete(model, fname):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    fpath = os.path.join(DATA_FOLDER, model.upper(), fname)
    if os.path.isfile(fpath):
        os.remove(fpath)
        flash("رکورد حذف شد 🗑️")
    else:
        flash("فایل پیدا نشد")
    return redirect(url_for("admin_panel"))

# ----- تأیید رکورد
@app.route("/admin/approve/<model>/<fname>", methods=["POST"])
def admin_approve(model, fname):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    fpath = os.path.join(DATA_FOLDER, model.upper(), fname)
    if os.path.isfile(fpath):
        with open(fpath, "r+", encoding="utf-8") as f:
            data = json.load(f)
            data["meta"]["status"] = "approved"
            f.seek(0)
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.truncate()
        flash("رکورد تأیید شد ✅")
    else:
        flash("فایل پیدا نشد ❌")
    return redirect(url_for("admin_panel"))

# ----- رد رکورد
@app.route("/admin/reject/<model>/<fname>", methods=["POST"])
def admin_reject(model, fname):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    fpath = os.path.join(DATA_FOLDER, model.upper(), fname)
    if os.path.isfile(fpath):
        with open(fpath, "r+", encoding="utf-8") as f:
            data = json.load(f)
            data["meta"]["status"] = "rejected"
            f.seek(0)
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.truncate()
        flash("رکورد رد شد ❌")
    else:
        flash("فایل پیدا نشد ❌")
    return redirect(url_for("admin_panel"))

# ----- دانلود اکسل
@app.route("/admin/download_excel/<model>/<fname>", methods=["POST"])
def admin_download_excel(model, fname):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    car_folder = os.path.join(DATA_FOLDER, model.upper())
    fpath = os.path.join(car_folder, fname)
    if not os.path.isfile(fpath):
        flash("فایل پیدا نشد")
        return redirect(url_for("admin_panel"))

    with open(fpath, "r", encoding="utf-8") as f:
        data = json.load(f)

    # ایجاد ورک‌بوک
    wb = Workbook()
    ws = wb.active
    ws.title = "فرم کامل"

    # اطلاعات پایه
    meta = data["meta"]
    ws.append(["نوع خودرو", meta["vehicle_type"]])
    ws.append(["VIN", meta["vin"]])
    ws.append(["تاریخ ارزیابی", meta["eval_date"]])
    ws.append(["ساعت شروع", meta["start_time"]])
    ws.append(["ساعت پایان", meta["end_time"]])
    ws.append(["کیلومتر شروع", meta["start_km"]])
    ws.append(["کیلومتر پایان", meta["end_km"]])
    ws.append(["مسافت طی شده", meta["distance"]])
    ws.append(["نام ارزیاب", meta["evaluator"]])
    ws.append([])  # خط خالی

    # جدول مشاهدات
    ws.append(["ردیف","ایرادات فنی","شرایط بروز ایراد","کیلومتر بروز ایراد","نظر سرپرست"])
    for r in data["observations"]:
        ws.append([r["row"], r["issue"], r["condition"], r["km"], r["supervisor_comment"]])

    # مسیر ذخیره در درایو D
    save_dir = os.path.join("D:/اطلاعات خودرو", meta["vehicle_type"].upper())
    os.makedirs(save_dir, exist_ok=True)
    filename = f'{meta["eval_date"]}_{meta["vehicle_type"]}_{meta["vin"]}_{meta["evaluator"]}.xlsx'
    save_path = os.path.join(save_dir, filename)
    wb.save(save_path)

    flash(f"فایل اکسل در {save_path} ذخیره شد ✅")
    return redirect(url_for("admin_panel"))
    
# ----- خروج ادمین
@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

