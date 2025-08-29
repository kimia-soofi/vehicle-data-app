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
    try:
        reshaped_text = arabic_reshaper.reshape(str(text))
        return get_display(reshaped_text)
    except:
        return str(text)

class RTLParagraph(Paragraph):
    """کلاس سفارشی برای پاراگراف‌های راست‌چین"""
    def __init__(self, text, style, **kwargs):
        if is_farsi(text):
            text = reshape_text(text)
        super().__init__(text, style, **kwargs)

def create_custom_paragraph(text, style, is_rtl=False):
    """ایجاد پاراگراف با پشتیبانی از RTL"""
    if text is None:
        text = ""
    
    if is_rtl or is_farsi(str(text)):
        text = reshape_text(str(text))
        # برای متن فارسی از تراز راست استفاده می‌کنیم
        style = style.clone('temp', alignment=TA_RIGHT)
    else:
        # برای متن انگلیسی از تراز چپ استفاده می‌کنیم
        style = style.clone('temp', alignment=TA_LEFT)
    
    return Paragraph(text, style)

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
    base_style = ParagraphStyle(
        name='Base', 
        fontName='Vazir', 
        fontSize=10,
        leading=14,
        wordWrap='CJK'  # برای پشتیبانی از wrap کردن متن فارسی
    )
    
    farsi_style = base_style.clone(
        'Farsi',
        alignment=TA_RIGHT,
        spaceBefore=3,
        spaceAfter=3
    )
    
    eng_style = base_style.clone(
        'Eng',
        alignment=TA_LEFT,
        spaceBefore=3,
        spaceAfter=3
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
        backColor=colors.darkblue,
        spaceBefore=5,
        spaceAfter=5
    )

    doc = SimpleDocTemplate(
        pdf_io, 
        pagesize=A4, 
        rightMargin=20*mm, 
        leftMargin=20*mm, 
        topMargin=15*mm, 
        bottomMargin=15*mm
    )
    elements = []

    # عنوان
    elements.append(Paragraph(reshape_text("فرم ارزیابی خودرو"), title_style))
    elements.append(Spacer(1, 15))

    # اطلاعات متا
    meta_style = ParagraphStyle(
        name='Meta',
        fontName='Vazir',
        fontSize=10,
        alignment=TA_RIGHT,
        leading=16
    )
    
    for k, v in data["meta"].items():
        key_text = f"<b>{k}:</b>"
        val_text = str(v) if v is not None else ""
        
        if is_farsi(val_text):
            full_text = f"{key_text} {reshape_text(val_text)}"
        else:
            full_text = f"{key_text} {val_text}"
        
        elements.append(Paragraph(full_text, meta_style))
        elements.append(Spacer(1, 5))

    elements.append(Spacer(1, 15))

    # عنوان جدول مشاهدات
    elements.append(Paragraph(reshape_text("جدول مشاهدات:"), farsi_style))
    elements.append(Spacer(1, 8))

    # جدول مشاهدات - ترتیب ستون‌ها از چپ به راست
    col_specs = [
        ("ردیف", 15*mm),
        ("ایرادات فنی", 45*mm),
        ("شرایط بروز ایراد", 45*mm),
        ("کیلومتر", 25*mm),
        ("نظر سرپرست", 40*mm),
    ]

    # هدر جدول
    table_data = []
    headers = [Paragraph(reshape_text(h), header_style) for h, w in col_specs]
    table_data.append(headers)

    # ردیف‌ها
    for idx, r in enumerate(data["observations"], 1):
        row_data = [
            create_custom_paragraph(str(idx), eng_style),  # شماره ردیف - چپ‌چین
            create_custom_paragraph(r.get("issue", ""), farsi_style, True),  # فارسی - راست‌چین
            create_custom_paragraph(r.get("condition", ""), farsi_style, True),  # فارسی - راست‌چین
            create_custom_paragraph(r.get("km", ""), eng_style),  # عدد - چپ‌چین
            create_custom_paragraph(r.get("supervisor_comment", ""), farsi_style, True)  # فارسی - راست‌چین
        ]
        table_data.append(row_data)

    col_widths = [w for h, w in col_specs]
    table = Table(
        table_data, 
        colWidths=col_widths,
        repeatRows=1  # تکرار هدر در صفحات بعدی
    )
    
    # استایل جدول
    table_style = TableStyle([
        # استایل هدر
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('VALIGN', (0,0), (-1,0), 'MIDDLE'),
        ('FONTNAME', (0,0), (-1,0), 'Vazir'),
        ('FONTSIZE', (0,0), (-1,0), 11),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
        ('TOPPADDING', (0,0), (-1,0), 8),
        
        # استایل داده‌ها
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#ecf0f1')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#bdc3c7')),
        ('VALIGN', (0,1), (-1,-1), 'TOP'),
        ('FONTNAME', (0,1), (-1,-1), 'Vazir'),
        ('FONTSIZE', (0,1), (-1,-1), 10),
        ('LEADING', (0,1), (-1,-1), 14),
        ('TOPPADDING', (0,1), (-1,-1), 6),
        ('BOTTOMPADDING', (0,1), (-1,-1), 6),
        ('LEFTPADDING', (0,1), (-1,-1), 4),
        ('RIGHTPADDING', (0,1), (-1,-1), 4),
        
        # تراز ستون‌ها
        ('ALIGN', (0,1), (0,-1), 'CENTER'),  # ستون ردیف - وسط‌چین
        ('ALIGN', (1,1), (1,-1), 'RIGHT'),   # ستون ایرادات - راست‌چین
        ('ALIGN', (2,1), (2,-1), 'RIGHT'),   # ستون شرایط - راست‌چین
        ('ALIGN', (3,1), (3,-1), 'CENTER'),  # ستون کیلومتر - وسط‌چین
        ('ALIGN', (4,1), (4,-1), 'RIGHT'),   # ستون نظر - راست‌چین
    ])
    
    table.setStyle(table_style)
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
















































