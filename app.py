from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import os, json, io, shutil
from datetime import datetime
import jdatetime
from openpyxl import Workbook
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
    return jdatetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")

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
# ====== بالای فایل app.py این importها را اضافه/بروز کنید
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER
import arabic_reshaper
import io, os, json, re
from flask import send_file, flash, redirect, url_for, session

# کمکی‌ها
def is_farsi(text) -> bool:
    return bool(re.search(r'[\u0600-\u06FF]', str(text)))

def fa_shape(text: str) -> str:
    # فقط شکل‌دهی عربی/فارسی؛ bidi را به Paragraph می‌سپاریم (wordWrap='RTL')
    return arabic_reshaper.reshape(str(text))

# ====== دانلود PDF با چیدمان راست به چپ و سطرشکنی درست
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

    buf = io.BytesIO()

    # سند
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        rightMargin=24, leftMargin=24, topMargin=36, bottomMargin=36
    )
    W, H = A4

    # فونت فارسی (Vazirmatn-Regular.ttf را در static گذاشته‌اید)
    pdfmetrics.registerFont(TTFont("Vazir", os.path.join("static", "Vazirmatn-Regular.ttf")))

    # استایل‌ها
    style_title = ParagraphStyle(
        name="title", fontName="Vazir", fontSize=15, leading=20, alignment=TA_CENTER
    )
    style_fa = ParagraphStyle(
        name="fa", fontName="Vazir", fontSize=11, leading=16,
        alignment=TA_RIGHT, wordWrap='RTL'   # ← سطرشکنی راست‌به‌چپ
    )
    style_en = ParagraphStyle(
        name="en", fontName="Vazir", fontSize=11, leading=16,
        alignment=TA_LEFT
    )
    style_key = ParagraphStyle(
        name="key", fontName="Vazir", fontSize=11, leading=16,
        alignment=TA_LEFT  # لیبل‌های متا همیشه چپ‌چین بمانند (EVALUATOR و…)
    )

    elements = []

    # عنوان
    elements.append(Paragraph(fa_shape("فرم ارزیابی خودرو"), style_title))
    elements.append(Spacer(1, 12))

    # --- جدول متادیتا (۲ ستونه: لیبل، مقدار)؛ جدول را راست‌چین می‌گذاریم
    meta = data.get("meta", {})
    # برای نظم، ترتیبِ نمایش را مشخص کنیم (اگر نبود، همان ترتیب دیکشنری)
    ordered_keys = [
        "vehicle_type", "vin", "eval_date", "start_time", "end_time",
        "start_km", "end_km", "distance", "evaluator", "submitted_at"
    ]
    rows = []
    style_cmds = [
        ('GRID', (0,0), (-1,-1), 0.25, colors.lightgrey),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke)
    ]
    # هدر فارسی/انگلیسی برای ستون لیبل و مقدار
    rows.append([
        Paragraph(fa_shape("فیلد"), style_fa),
        Paragraph(fa_shape("مقدار"), style_fa)
    ])

    r_index = 1
    for k in ordered_keys:
        if k not in meta: 
            continue
        v = meta[k]
        # لیبل را همان کلید خام نمایش می‌دهیم (چپ‌چین)
        key_cell = Paragraph(f"{k}:", style_key)
        # مقدار: اگر فارسی بود راست‌چین و شکل‌دهی، وگرنه چپ‌چین معمولی
        val_cell = Paragraph(fa_shape(v) if is_farsi(v) else str(v),
                             style_fa if is_farsi(v) else style_en)
        rows.append([key_cell, val_cell])
        # تراز هر سطرِ مقدار را به‌صورت سلولی دقیق تنظیم کنیم
        style_cmds.append(('ALIGN', (1, r_index), (1, r_index), 'RIGHT' if is_farsi(v) else 'LEFT'))
        r_index += 1

    meta_tbl = Table(rows, colWidths=[110, doc.width - 110], hAlign='RIGHT')
    meta_tbl.setStyle(TableStyle(style_cmds))
    elements.append(meta_tbl)
    elements.append(Spacer(1, 16))

    # --- جدول مشاهدات (ستون‌ها از راست به چپ، خودِ جدول راست‌چین)
    # ترتیب از راست به چپ مثل فرم: ردیف | ایرادات | شرایط | کیلومتر | نظر سرپرست
    headers = ["ردیف", "ایرادات فنی", "شرایط بروز ایراد", "کیلومتر", "نظر سرپرست"]
    colWidths = [40, 170, 170, 60, 90]   # مجموع <= doc.width باشد
    data_rows = []

    # ردیف هدر
    data_rows.append([Paragraph(fa_shape(h), style_fa) for h in headers])

    # بدنه جدول
    for r in data.get("observations", []):
        cells = [
            r.get("row", ""),
            r.get("issue", ""),
            r.get("condition", ""),
            r.get("km", ""),
            r.get("supervisor_comment", "")
        ]
        row_cells = []
        for c in cells:
            txt = "" if c is None else str(c)
            if is_farsi(txt):
                row_cells.append(Paragraph(fa_shape(txt), style_fa))
            else:
                row_cells.append(Paragraph(txt, style_en))
        data_rows.append(row_cells)

    obs_tbl = Table(data_rows, colWidths=colWidths, hAlign='RIGHT', repeatRows=1)
    obs_tbl.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        # ترازبندی ستونی:
        ('ALIGN', (0,1), (0,-1), 'CENTER'),  # ستون "ردیف"
        ('ALIGN', (3,1), (3,-1), 'CENTER'),  # ستون "کیلومتر"
        # ستون‌های متنی فارسی پیش‌فرض راست هستند چون style_fa راست‌چین است
    ]))
    elements.append(obs_tbl)

    # ساخت PDF
    doc.build(elements)
    buf.seek(0)

    # نام فایل
    meta = data.get("meta", {})
    pdf_filename = f'{meta.get("eval_date","")}_{meta.get("vehicle_type","")}_{meta.get("vin","")}_{meta.get("evaluator","")}.pdf'
    return send_file(buf, download_name=pdf_filename, as_attachment=True, mimetype="application/pdf")




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



























































