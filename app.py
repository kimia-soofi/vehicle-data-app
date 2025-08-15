from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import os, json, pandas as pd
from datetime import datetime
import jdatetime
from config import ADMIN_USERNAME as CONF_USER, ADMIN_PASSWORD as CONF_PASS, CAR_MODELS

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
        eval_date = request.form.get("eval_date")  # تاریخ شمسی
        start_time = request.form.get("start_time")
        end_time = request.form.get("end_time")
        start_km = request.form.get("start_km")
        end_km = request.form.get("end_km")
        distance = request.form.get("distance")
        evaluator = request.form.get("evaluator")
        rows_json = request.form.get("rows_json", "[]")
        try:
            rows = json.loads(rows_json)
        except:
            rows = []

        car_folder = os.path.join(DATA_FOLDER, vehicle_type.upper())
        os.makedirs(car_folder, exist_ok=True)

        # زمان ثبت شمسی
        submitted_at = jdatetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")

        filename = f"{submitted_at.replace(' ','_').replace('/','-')}_{vehicle_type}_{vin}_{evaluator}.json"
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
                "submitted_at": submitted_at,
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

# ----- تایید اطلاعات
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
        flash("رکورد تایید شد ✅")
    return redirect(url_for("admin_panel"))

# ----- رد اطلاعات
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
    return redirect(url_for("admin_panel"))

# ----- دانلود اکسل از رکورد تایید شده
@app.route("/admin/download/<model>/<fname>")
def admin_download(model, fname):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    fpath = os.path.join(DATA_FOLDER, model.upper(), fname)
    if os.path.isfile(fpath):
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        df_meta = pd.DataFrame([data["meta"]])
        df_obs = pd.DataFrame(data["observations"])
        # ذخیره کل فرم در اکسل
        excel_path = os.path.join("downloads", fname.replace(".json", ".xlsx"))
        os.makedirs("downloads", exist_ok=True)
        with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
            df_meta.to_excel(writer, sheet_name="اطلاعات پایه", index=False)
            df_obs.to_excel(writer, sheet_name="مشاهدات", index=False)
        return send_file(excel_path, as_attachment=True)
    flash("فایل پیدا نشد")
    return redirect(url_for("admin_panel"))

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

# ----- خروج ادمین
@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
