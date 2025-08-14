from flask import Flask, render_template, request, redirect, url_for, session, flash
import os, json
from datetime import datetime
from config import ADMIN_USERNAME as CONF_USER, ADMIN_PASSWORD as CONF_PASS, CAR_MODELS

# ----- تنظیمات پایه
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change_this_secret_key")

# اگر روی رندر یا هر هاست دیگری ENV ست کردی، از آن استفاده می‌شود
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", CONF_USER)
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", CONF_PASS)

DATA_FOLDER = "data"
os.makedirs(DATA_FOLDER, exist_ok=True)

# ----- صفحه فرود
@app.route("/")
def index():
    return render_template("index.html")

# ----- فرم همکاران: ثبت مشاهدات روزانه ارزیابی
@app.route("/staff", methods=["GET", "POST"])
def staff_form():
    if request.method == "POST":
        # اطلاعات پایه
        vehicle_type = request.form.get("vehicle_type")              # نوع خودرو (از منو)
        vin = request.form.get("vin")                                 # شماره شاسی
        eval_date = request.form.get("eval_date")                     # تاریخ انجام ارزیابی
        start_time = request.form.get("start_time")                   # ساعت شروع
        end_time = request.form.get("end_time")                       # ساعت پایان
        start_km = request.form.get("start_km")                       # کیلومتر شروع
        end_km = request.form.get("end_km")                           # کیلومتر پایان
        distance = request.form.get("distance")                       # مسافت طی شده (محاسبه/ورودی)
        evaluator = request.form.get("evaluator")                     # نام ارزیاب

        # جدول ردیف‌ها به‌صورت JSON از input مخفی می‌آید
        rows_json = request.form.get("rows_json", "[]")
        try:
            rows = json.loads(rows_json)
        except json.JSONDecodeError:
            rows = []

        # ساخت پوشه مخصوص مدل خودرو
        car_folder = os.path.join(DATA_FOLDER, vehicle_type.upper())
        os.makedirs(car_folder, exist_ok=True)

        # ذخیره فایل
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
                "submitted_at": datetime.now().isoformat(timespec="seconds")
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
        all_data[model] = list(reversed(records))  # جدیدترین بالا
    return render_template("admin_panel.html", all_data=all_data)

# ----- حذف رکورد (ادمین)
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

# ----- خروج ادمین
@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    # در دیپلوی تولیدی debug را False بگذار
    app.run(host="0.0.0.0", port=5000, debug=True)
