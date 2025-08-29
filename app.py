from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import os, json, io, shutil
from datetime import datetime
import jdatetime
from config import ADMIN_USERNAME, ADMIN_PASSWORD, STAFF_USERNAME, STAFF_PASSWORD, CAR_MODELS_FILE, INITIAL_CAR_MODELS

# ----- تنظیمات پایه
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change_this_secret_key")


DATA_FOLDER = "data"
os.makedirs(DATA_FOLDER, exist_ok=True)

# ----- مدیریت مدل‌ها
def load_car_models():
    if os.path.isfile(CAR_MODELS_FILE):
        with open(CAR_MODELS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    save_car_models(INITIAL_CAR_MODELS)
    return INITIAL_CAR_MODELS

def save_car_models(models):
    with open(CAR_MODELS_FILE, "w", encoding="utf-8") as f:
        json.dump(models, f, ensure_ascii=False, indent=2)

def persian_date_now():
    return jdatetime.datetime.now().strftime("%Y/%m/%d")

# ----- صفحه فرود
@app.route("/")
def index():
    return render_template("index.html")
    
# ----- ورود همکاران
@app.route("/staff/login", methods=["GET", "POST"])
def staff_login():
    if request.method == "POST":
        u = request.form.get("username", "")
        p = request.form.get("password", "")
        if u == STAFF_USERNAME and p == STAFF_PASSWORD:
            session["staff_logged_in"] = True
            return redirect(url_for("staff_form"))
        flash("نام کاربری یا رمز عبور اشتباه است ❌")
        return redirect(url_for("staff_login"))
    return render_template("staff_login.html")

# ----- فرم همکاران
@app.route("/staff", methods=["GET", "POST"])
def staff_form():
    if not session.get("staff_logged_in"):
        return redirect(url_for("staff_login"))
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
        except:
            rows = []

        car_folder = os.path.join(DATA_FOLDER, vehicle_type.upper())
        os.makedirs(car_folder, exist_ok=True)

        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        payload = {
            "meta":{
            "vehicle_type":vehicle_type,
            "vin":vin,
            "eval_date":eval_date,
            "start_time":start_time,
            "end_time":end_time,
            "start_km":start_km,
            "end_km":end_km,
            "distance":distance,
            "evaluator":evaluator,
            "submitted_at": persian_date_now()
        },
            "observations":rows,
            "status":""}

        with open(os.path.join(car_folder, filename),"w",encoding="utf-8") as f:
            json.dump(payload,f,ensure_ascii=False,indent=2)
        flash("فرم با موفقیت ذخیره شد ✅")
        return redirect(url_for("staff_form"))

    car_models = load_car_models()
    return render_template("staff_form.html", car_models=car_models)

# ----- ورود ادمین
@app.route("/admin", methods=["GET","POST"])
def admin_login():
    if request.method=="POST":
        u = request.form.get("username","")
        p = request.form.get("password","")
        if u==ADMIN_USERNAME and p==ADMIN_PASSWORD:
            session["admin_logged_in"]=True
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
    for model in load_car_models():
        car_folder = os.path.join(DATA_FOLDER, model.upper())
        records=[]
        if os.path.isdir(car_folder):
            for fname in sorted(os.listdir(car_folder)):
                if fname.lower().endswith(".json"):
                    fpath = os.path.join(car_folder,fname)
                    with open(fpath,"r",encoding="utf-8") as f:
                        data = json.load(f)
                        data["_filename"]=fname
                        data["_model"]=model
                        records.append(data)
        all_data[model] = list(reversed(records))
    return render_template("admin_panel.html", all_data=all_data)

# ----- تایید رکورد
@app.route("/admin/approve/<model>/<fname>", methods=["POST"])
def admin_approve(model,fname):
    if not session.get("admin_logged_in"): return redirect(url_for("admin_login"))
    fpath=os.path.join(DATA_FOLDER, model.upper(), fname)
    if os.path.isfile(fpath):
        with open(fpath,"r",encoding="utf-8") as f: data=json.load(f)
        data["status"]="approved"
        with open(fpath,"w",encoding="utf-8") as f: json.dump(data,f,ensure_ascii=False,indent=2)
        flash("رکورد تایید شد ✅")
    return redirect(url_for("admin_panel"))

# ----- رد رکورد
@app.route("/admin/reject/<model>/<fname>", methods=["POST"])
def admin_reject(model,fname):
    if not session.get("admin_logged_in"): return redirect(url_for("admin_login"))
    fpath=os.path.join(DATA_FOLDER, model.upper(), fname)
    if os.path.isfile(fpath):
        with open(fpath,"r",encoding="utf-8") as f: data=json.load(f)
        data["status"]="rejected"
        with open(fpath,"w",encoding="utf-8") as f: json.dump(data,f,ensure_ascii=False,indent=2)
        flash("رکورد رد شد ❌")
    return redirect(url_for("admin_panel"))




# ----- دانلود PDF کل فرم
from flask import send_file, flash, redirect, url_for, session
import io, os, json
from weasyprint import HTML, CSS

from flask import send_file, flash, redirect, url_for, session
import io, os, json
from weasyprint import HTML

@app.route("/admin/download_pdf/<model>/<fname>", methods=["POST"])
def download_pdf(model, fname):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    fpath = os.path.join(DATA_FOLDER, model.upper(), fname)
    if not os.path.isfile(fpath):
        flash("فایل پیدا نشد ❌")
        return redirect(url_for("admin_panel"))

    with open(fpath, "r", encoding="utf-8") as f:
        data = json.load(f)

    font_path = os.path.abspath(os.path.join("static", "Vazirmatn-Regular.ttf"))
    
    left_margin = 0
    right_margin = 15
    table_width = 595 - left_margin - right_margin  # عرض A4 ~595pt
    col_ratios = [0.06, 0.32, 0.32, 0.1, 0.2]     # نسبت ستون‌ها به عرض جدول

    html_content = f"""
    <html>
    <head>
    <meta charset="utf-8">
    <style>
        @page {{ margin-top:25px; margin-right:25px; margin-bottom:25px; margin-left:15px; }}
        @font-face {{
            font-family: 'Vazirmatn';
            src: url('file://{font_path}') format('truetype');
        }}
        body {{
            font-family: 'Vazirmatn', sans-serif;
            direction: rtl;
            color: #333;
            line-height: 1.4;
        }}
        h2 {{
            text-align: center;
            color: #005baa;
            font-size: 22px;
            margin-bottom: 15px;
        }}
        .meta {{
            background-color: #f5f5f5;
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 20px;
        }}
        .meta p {{
            margin: 4px 0;
            font-size: 14px;
        }}
        table {{
            border-collapse: collapse;
            width: {table_width}px;
            margin-left: {left_margin}px;
            margin-right: {right_margin}px;
            table-layout: fixed;
            word-wrap: break-word;
            font-size: 13px;
        }}
        th, td {{
            border: 1px solid #ccc;
            padding: 6px;
            vertical-align: top;
            word-wrap: break-word;
        }}
        th {{
            background-color: #005baa;
            color: white;
            text-align: center;
        }}
        td {{
            text-align: right;
        }}
    </style>
    </head>
    <body>
        <h2>فرم ارزیابی خودرو</h2>
        <div class="meta">
            <p><strong>ارزیاب:</strong> {data["meta"]["evaluator"]}</p>
            <p><strong>نوع خودرو:</strong> {data["meta"]["vehicle_type"]}</p>
            <p><strong>VIN:</strong> {data["meta"]["vin"]}</p>
            <p><strong>تاریخ ارزیابی:</strong> {data["meta"]["eval_date"]}</p>
            <p><strong>مسافت طی شده:</strong> {data["meta"]["distance"]}</p>
        </div>
        <h3>جدول مشاهدات:</h3>
        <table>
            <tr>
    """

    headers = ["ردیف", "ایرادات فنی", "شرایط بروز ایراد", "کیلومتر", "نظر سرپرست"]
    for header, ratio in zip(headers, col_ratios):
        width = int(table_width * ratio)
        html_content += f"<th style='width:{width}px'>{header}</th>"
    html_content += "</tr>"

    for r in data["observations"]:
        html_content += "<tr>"
        html_content += f"<td>{r.get('row','')}</td>"
        html_content += f"<td>{r.get('issue','')}</td>"
        html_content += f"<td>{r.get('condition','')}</td>"
        html_content += f"<td>{r.get('km','')}</td>"
        html_content += f"<td>{r.get('supervisor_comment','')}</td>"
        html_content += "</tr>"

    html_content += """
        </table>
    </body>
    </html>
    """

    pdf_io = io.BytesIO()
    HTML(string=html_content, base_url=".").write_pdf(pdf_io)
    pdf_io.seek(0)

    pdf_name = f"{data['meta']['eval_date']}_{data['meta']['vehicle_type']}_{data['meta']['vin']}_{data['meta']['evaluator']}.pdf"
    return send_file(pdf_io, download_name=pdf_name, as_attachment=True, mimetype="application/pdf")









# ----- مدیریت مدل‌ها
@app.route("/admin/car_models", methods=["GET","POST"])
def admin_car_models():
    if not session.get("admin_logged_in"): return redirect(url_for("admin_login"))
    models = load_car_models()
    if request.method=="POST":
        action = request.form.get("action")
        name = request.form.get("name","").strip()
        old_name = request.form.get("old_name","").strip()
        if action=="add" and name and name not in models:
            models.append(name)
            save_car_models(models)
            flash(f"مدل {name} اضافه شد ✅")
        elif action=="edit" and old_name and name:
            if old_name in models:
                idx = models.index(old_name)
                models[idx]=name
                save_car_models(models)
                flash(f"مدل {old_name} به {name} ویرایش شد ✅")
        elif action=="delete" and name in models:
            models.remove(name)
            save_car_models(models)
            flash(f"مدل {name} حذف شد 🗑️")
        return redirect(url_for("admin_car_models"))
    return render_template("admin_car_models.html", models=models)

# ----- پاک کردن کل رکوردها
@app.route("/admin/clear_all_data", methods=["POST"])
def admin_clear_all_data():
    if not session.get("admin_logged_in"): return redirect(url_for("admin_login"))
    if os.path.isdir(DATA_FOLDER):
        shutil.rmtree(DATA_FOLDER)
        os.makedirs(DATA_FOLDER, exist_ok=True)
        flash("تمام رکوردها حذف شدند 🗑️")
    return redirect(url_for("admin_panel"))

# ----- حذف رکورد تک
@app.route("/admin/delete/<model>/<fname>", methods=["POST"])
def admin_delete(model,fname):
    if not session.get("admin_logged_in"): return redirect(url_for("admin_login"))
    fpath=os.path.join(DATA_FOLDER, model.upper(), fname)
    if os.path.isfile(fpath):
        os.remove(fpath)
        flash("رکورد حذف شد 🗑️")
    return redirect(url_for("admin_panel"))
    
# ----- خروج کاربران
@app.route("/staff/logout")
def staff_logout():
    session.pop("staff_logged_in", None)
    return redirect(url_for("index"))

# ----- خروج ادمین
@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("index"))

if __name__=="__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)














































































