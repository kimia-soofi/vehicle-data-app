import os
import json
import csv
from datetime import datetime, timezone
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, abort, flash

APP_TITLE = "سیستم ثبت اطلاعات خودرو"
DATA_ROOT = os.path.join(os.getcwd(), "data")
CAR_TYPES_FILE = "car_types.txt"
SCHEMA_FILE = "form_schema.json"
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASSWORD", "admin123")
SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-please")

app = Flask(__name__)
app.secret_key = SECRET_KEY

# --- helpers ----------------------------------------------------

def ensure_dirs():
    os.makedirs(DATA_ROOT, exist_ok=True)
    if not os.path.exists(CAR_TYPES_FILE):
        with open(CAR_TYPES_FILE, "w", encoding="utf-8") as f:
            f.write("J4\nX5\n")

def load_car_types():
    ensure_dirs()
    with open(CAR_TYPES_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def add_car_type(name: str):
    name = name.strip()
    if not name:
        return
    cars = set(load_car_types())
    if name not in cars:
        with open(CAR_TYPES_FILE, "a", encoding="utf-8") as f:
            f.write(name + "\n")

def remove_car_type(name: str):
    cars = [c for c in load_car_types() if c != name]
    with open(CAR_TYPES_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(cars) + ("\n" if cars else ""))

def safe_key(s: str):
    return "".join(ch for ch in s if ch.isalnum() or ch in ("-", "_", ".")).strip()

def now_stamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")

def get_model_dir(model: str):
    d = os.path.join(DATA_ROOT, model)
    os.makedirs(d, exist_ok=True)
    return d

def append_index_row(model: str, row: dict):
    model_dir = get_model_dir(model)
    index_path = os.path.join(model_dir, "index.csv")
    write_header = not os.path.exists(index_path)
    keys = [k for k in row.keys() if k not in ("timestamp", "model")]
    fieldnames = ["timestamp", "model"] + keys
    with open(index_path, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            w.writeheader()
        w.writerow(row)

def load_schema():
    default_schema = {
        "title": APP_TITLE,
        "rows": [
            [
                {"label": "تاریخ", "name": "date", "type": "date", "required": True},
                {"label": "نوع خودرو", "name": "car_model", "type": "select", "source": "car_types", "required": True}
            ],
            [
                {"label": "شماره شاسی (VIN)", "name": "vin", "type": "text", "required": True},
                {"label": "کارکرد (کیلومتر)", "name": "mileage", "type": "number", "required": True}
            ],
            [
                {"label": "شماره پلاک", "name": "plate", "type": "text", "required": True},
                {"label": "نام مشتری", "name": "customer_name", "type": "text", "required": True}
            ],
            [
                {"label": "شماره تماس", "name": "phone", "type": "tel", "required": True},
                {"label": "شهر/نمایندگی", "name": "branch", "type": "text", "required": False}
            ]
        ],
        "submit": {"label": "ذخیره"}
    }
    if os.path.exists(SCHEMA_FILE):
        try:
            with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default_schema
    return default_schema

# --- routes -----------------------------------------------------

@app.route("/", methods=["GET"])
def form_view():
    schema = load_schema()
    car_types = load_car_types()
    return render_template("form.html", schema=schema, car_types=car_types)

@app.route("/submit", methods=["POST"])
def submit_form():
    schema = load_schema()
    payload = {}
    for row in schema.get("rows", []):
        for cell in row:
            name = cell.get("name")
            if not name:
                continue
            payload[name] = request.form.get(name, "").strip()

    model = request.form.get("car_model") or payload.get("car_model")
    if not model:
        flash("انتخاب نوع خودرو الزامی است.", "danger")
        return redirect(url_for("form_view"))

    model = safe_key(model)
    stamp = now_stamp()

    record = {"timestamp": stamp, "model": model}
    record.update(payload)

    model_dir = get_model_dir(model)
    file_name = f"{stamp}_form.json"
    file_path = os.path.join(model_dir, file_name)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

    append_index_row(model, record)
    return redirect(url_for("form_success"))

@app.route("/success")
def form_success():
    return "<h3 style='font-family:tahoma;direction:rtl;text-align:center;margin-top:40px'>اطلاعات با موفقیت ذخیره شد ✅</h3>"

# --- admin ------------------------------------------------------

@app.route("/dashboard", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        u = request.form.get("username", "")
        p = request.form.get("password", "")
        if u == ADMIN_USER and p == ADMIN_PASS:
            session["is_admin"] = True
            return redirect(url_for("admin_panel"))
        flash("نام کاربری یا رمز عبور نادرست است", "danger")
    return render_template("admin_login.html")

@app.route("/admin")
def admin_panel():
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))
    car_types = load_car_types()
    selected = request.args.get("model") or (car_types[0] if car_types else None)
    records = []
    if selected:
        model_dir = get_model_dir(selected)
        for fname in sorted(os.listdir(model_dir)):
            if fname.endswith(".json"):
                records.append(fname)
    return render_template("admin.html", car_types=car_types, selected=selected, records=records)

@app.route("/admin/add_model", methods=["POST"])
def admin_add_model():
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))
    new_model = request.form.get("new_model", "").strip()
    if new_model:
        add_car_type(new_model)
    return redirect(url_for("admin_panel"))

@app.route("/admin/remove_model", methods=["POST"])
def admin_remove_model():
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))
    model = request.form.get("model", "").strip()
    if model:
        remove_car_type(model)
    return redirect(url_for("admin_panel"))

@app.route("/download/<model>/<path:filename>")
def download_record(model, filename):
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))
    model = safe_key(model)
    model_dir = get_model_dir(model)
    path = os.path.join(model_dir, filename)
    if not os.path.isfile(path):
        abort(404)
    return send_from_directory(model_dir, filename, as_attachment=True)

@app.route("/download_index/<model>")
def download_index(model):
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))
    model = safe_key(model)
    model_dir = get_model_dir(model)
    index_path = os.path.join(model_dir, "index.csv")
    if not os.path.exists(index_path):
        abort(404)
    return send_from_directory(model_dir, "index.csv", as_attachment=True)

if __name__ == "__main__":
    ensure_dirs()
    app.run(host="0.0.0.0", port=5000)
