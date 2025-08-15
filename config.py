# نام کاربری و رمز عبور ادمین (می‌توانی اینجا عوض کنی یا ENV ست کنی)
import os

# نام کاربری و رمز عبور ادمین و همکاران از ENV گرفته می‌شود
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin_default")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin_pass_default")

STAFF_USERNAME = os.environ.get("STAFF_USERNAME", "staff_default")
STAFF_PASSWORD = os.environ.get("STAFF_PASSWORD", "staff_pass_default")

# فایل مدل‌های خودرو
CAR_MODELS_FILE = "car_models.json"

# مدل‌های اولیه در صورت نبود فایل
INITIAL_CAR_MODELS = ["J4", "X5", "T9", "EAGLE"]

