from flask import Flask, render_template, request, redirect, url_for, send_file
import os
import pandas as pd
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['EXCEL_FILE'] = 'vehicle_data.xlsx'
app.config['CAR_TYPES_FILE'] = 'car_types.txt'

# Ensure uploads directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Load or create car types list
def load_car_types():
    if not os.path.exists(app.config['CAR_TYPES_FILE']):
        return []
    with open(app.config['CAR_TYPES_FILE'], 'r', encoding='utf-8') as f:
        return [line.strip() for line in f.readlines()]

def save_car_type(car_type):
    car_type = car_type.strip()
    if car_type and car_type not in load_car_types():
        with open(app.config['CAR_TYPES_FILE'], 'a', encoding='utf-8') as f:
            f.write(f"{car_type}\n")

@app.route('/', methods=['GET', 'POST'])
def form():
    car_types = load_car_types()
    if request.method == 'POST':
        car_type = request.form['car_type']
        vin = request.form['vin']
        mileage = request.form['mileage']
        notes = request.form['notes']
        photo = request.files['photo']

        if photo.filename:
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            filename = f"{vin}_{timestamp}_{photo.filename}"
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            photo.save(photo_path)
        else:
            filename = ''

        # Save to Excel
        data = {
            'Date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Car Type': car_type,
            'VIN': vin,
            'Mileage': mileage,
            'Notes': notes,
            'Photo': filename
        }

        if os.path.exists(app.config['EXCEL_FILE']):
            df = pd.read_excel(app.config['EXCEL_FILE'])
            df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
        else:
            df = pd.DataFrame([data])

        df.to_excel(app.config['EXCEL_FILE'], index=False)

        return redirect(url_for('form'))

    return render_template('form.html', car_types=car_types)

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    df = None
    car_types = load_car_types()

    if os.path.exists(app.config['EXCEL_FILE']):
        df = pd.read_excel(app.config['EXCEL_FILE'])

    if request.method == 'POST':
        new_type = request.form.get('new_car_type', '').strip()
        if new_type:
            save_car_type(new_type)
        return redirect(url_for('dashboard'))

    return render_template('dashboard.html', df=df, car_types=car_types)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
