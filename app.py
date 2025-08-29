from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import os, json, io, shutil
from datetime import datetime
import jdatetime
from openpyxl import Workbook
from config import ADMIN_USERNAME, ADMIN_PASSWORD, STAFF_USERNAME, STAFF_PASSWORD, CAR_MODELS_FILE, INITIAL_CAR_MODELS
from fpdf import FPDF
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
from flask import send_file, flash, redirect, url_for, session
import io, os, json, re
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER
import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.platypus.flowables import KeepInFrame
from reportlab.lib.units import mm

def is_farsi(text):
    return bool(re.search(r'[\u0600-\u06FF]', str(text)))

def reshape_text(text):
    if text is None:
        return ""
    reshaped_text = arabic_reshaper.reshape(str(text))
    return get_display(reshaped_text)

def create_farsi_paragraph(text, style, max_width=None):
    """ایجاد پاراگراف فارسی با قابلیت نگهداری در قاب"""
    if text is None:
        text = ""
    
    if is_farsi(str(text)):
        text = reshape_text(str(text))
        para = Paragraph(text, style)
    else:
        para = Paragraph(str(text), style)
    
    if max_width:
        return KeepInFrame(max_width, 1000, [para])
    return para

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

    pdf_io = io.BytesIO()

    # ثبت فونت
    pdfmetrics.registerFont(TTFont('Vazir', os.path.join("static", "Vazirmatn-Regular.ttf")))

    # تنظیمات سبک‌ها
    farsi_style = ParagraphStyle(
        name='Farsi', 
        fontName='Vazir', 
        fontSize=10, 
        alignment=TA_RIGHT,
        wordWrap='RTL',
        leading=14
    )
    
    eng_style = ParagraphStyle(
        name='Eng', 
        fontName='Vazir', 
        fontSize=10, 
        alignment=TA_LEFT,
        leading=14
    )
    
    title_style = ParagraphStyle(
        name='Title', 
        fontName='Vazir', 
        fontSize=16, 
        alignment=TA_RIGHT,
        textColor=colors.darkblue,
        spaceAfter=12
    )
    
    header_style = ParagraphStyle(
        name='Header', 
        fontName='Vazir', 
        fontSize=11, 
        alignment=TA_CENTER,
        textColor=colors.white,
        backColor=colors.darkblue
    )

    doc = SimpleDocTemplate(
        pdf_io, 
        pagesize=A4, 
        rightMargin=30*mm, 
        leftMargin=30*mm, 
        topMargin=20*mm, 
        bottomMargin=20*mm
    )
    elements = []

    # عنوان
    elements.append(Paragraph(reshape_text("فرم ارزیابی خودرو"), title_style))

    # اطلاعات متا
    meta_table_data = []
    for k, v in data["meta"].items():
        key_text = create_farsi_paragraph(f"{k}:", eng_style)
        val_text = create_farsi_paragraph(v, farsi_style if is_farsi(str(v)) else eng_style)
        meta_table_data.append([key_text, val_text])
    
    meta_table = Table(
        meta_table_data, 
        colWidths=[40*mm, 100*mm],
        hAlign='RIGHT'
    )
    meta_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (0,0), (0,-1), 'LEFT'),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('FONTNAME', (0,0), (-1,-1), 'Vazir'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    
    elements.append(meta_table)
    elements.append(Spacer(1, 15))

    # عنوان جدول مشاهدات
    elements.append(Paragraph(reshape_text("جدول مشاهدات:"), farsi_style))
    elements.append(Spacer(1, 8))

    # جدول مشاهدات
    col_specs = [
        ("ردیف", 15*mm),
        ("ایرادات فنی", 40*mm),
        ("شرایط بروز ایراد", 40*mm),
        ("کیلومتر", 20*mm),
        ("نظر سرپرست", 35*mm),
    ]

    # هدر جدول
    table_data = []
    headers = [create_farsi_paragraph(h, header_style) for h, w in col_specs]
    table_data.append(headers)

    # ردیف‌ها
    for idx, r in enumerate(data["observations"], 1):
        row_data = [
            create_farsi_paragraph(idx, eng_style),  # شماره ردیف
            create_farsi_paragraph(r.get("issue", ""), farsi_style, 40*mm),
            create_farsi_paragraph(r.get("condition", ""), farsi_style, 40*mm),
            create_farsi_paragraph(r.get("km", ""), eng_style, 20*mm),
            create_farsi_paragraph(r.get("supervisor_comment", ""), farsi_style, 35*mm)
        ]
        table_data.append(row_data)

    col_widths = [w for h, w in col_specs]
    table = Table(
        table_data, 
        colWidths=col_widths, 
        hAlign='RIGHT',
        repeatRows=1  # تکرار هدر در صفحات بعدی
    )
    
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.darkblue),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Vazir'),
        ('FONTSIZE', (0,0), (-1,0), 11),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
        ('BACKGROUND', (0,1), (-1,-1), colors.beige),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (0,1), (-1,-1), 'RIGHT'),
        ('ALIGN', (3,1), (3,-1), 'CENTER'),  # ستون کیلومتر
        ('FONTNAME', (0,1), (-1,-1), 'Vazir'),
        ('FONTSIZE', (0,1), (-1,-1), 10),
        ('LEADING', (0,1), (-1,-1), 14),
        ('TOPPADDING', (0,1), (-1,-1), 4),
        ('BOTTOMPADDING', (0,1), (-1,-1), 4),
    ]))
    
    elements.append(table)

    doc.build(elements)
    pdf_io.seek(0)

    pdf_filename = f'{data["meta"]["eval_date"]}_{data["meta"]["vehicle_type"]}_{data["meta"]["vin"]}_{data["meta"]["evaluator"]}.pdf'
    return send_file(pdf_io, download_name=pdf_filename, as_attachment=True, mimetype="application/pdf")







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















































