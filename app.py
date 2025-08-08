from flask import Flask, render_template, request, redirect, url_for, send_file, session
from werkzeug.utils import secure_filename
import os
import csv
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # لازم برای session

UPLOAD_FOLDER = 'uploads'
DATA_FILE = 'vehicle_data.csv'
CAR_TYPES_FILE = 'car_types.txt'
ADMIN_PASSWORD = 'kmcadmin123'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def load_car_types():
    if not os.path.exists(CAR_TYPES_FILE):
        return []
    with open(CAR_TYPES_FILE, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def save_car_types(car_types):
    with open(CAR_TYPES_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(car_types))

@app.route('/', methods=['GET', 'POST'])
def vehicle_form():
    car_types = load_car_types()
    if request.method == 'POST':
        car_type = request.form['car_type']
        vin = request.form['vin']
        mileage = request.form['mileage']
        notes = request.form['notes']
        image = request.files['image']

        image_filename = ''
        if image:
            image_filename = datetime.now().strftime('%Y%m%d%H%M%S_') + secure_filename(image.filename)
            image.save(os.path.join(UPLOAD_FOLDER, image_filename))

        with open(DATA_FILE, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([car_type, vin, mileage, notes, image_filename])

        return redirect(url_for('vehicle_form'))
    
    return render_template('form.html', car_types=car_types)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form['password']
        if password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
    return render_template('admin_login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    car_types = load_car_types()

    if request.method == 'POST':
        if 'add_car_type' in request.form:
            new_type = request.form['new_car_type'].strip()
            if new_type and new_type not in car_types:
                car_types.append(new_type)
                save_car_types(car_types)
        elif 'delete_car_type' in request.form:
            delete_type = request.form['delete_car_type'].strip()
            if delete_type in car_types:
                car_types.remove(delete_type)
                save_car_types(car_types)

    return render_template('admin.html', car_types=car_types)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('vehicle_form'))

@app.route('/download')
def download_data():
    return send_file(DATA_FILE, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
