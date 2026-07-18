import os
import json
import base64
import csv
import io
from datetime import datetime, date
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for,
                   flash, jsonify, session, send_file, make_response)
from flask_login import (LoginManager, UserMixin, login_user, logout_user,
                         login_required, current_user)
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv
import sqlite3
from werkzeug.utils import secure_filename
from google import genai
from google.genai import types
from PIL import Image

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fasalguru_dev_key_2024')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Pehle login karein!'
login_manager.login_message_category = 'warning'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'jfif'}

INDIAN_STATES = [
    "Andhra Pradesh","Arunachal Pradesh","Assam","Bihar","Chhattisgarh",
    "Goa","Gujarat","Haryana","Himachal Pradesh","Jharkhand","Karnataka",
    "Kerala","Madhya Pradesh","Maharashtra","Manipur","Meghalaya","Mizoram",
    "Nagaland","Odisha","Punjab","Rajasthan","Sikkim","Tamil Nadu",
    "Telangana","Tripura","Uttar Pradesh","Uttarakhand","West Bengal",
    "Delhi","Jammu & Kashmir","Ladakh","Chandigarh","Puducherry"
]

CROPS = ["Wheat","Rice","Cotton","Tomato","Potato","Sugarcane","Onion","Maize","Others"]

# ── Database ──────────────────────────────────────────────────────────────────

def get_db():
    db = sqlite3.connect('fasalguru.db')
    db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    c = db.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        state TEXT,
        crops TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS detections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        crop_type TEXT,
        image_path TEXT,
        disease_name TEXT,
        confidence REAL,
        severity TEXT,
        treatment_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS advisories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        city TEXT,
        season TEXT,
        advisory_text TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    # Seed demo users
    users = [
        ('Rahul Sharma', 'rahul@demo.com', 'demo123', 'Uttar Pradesh', 'Wheat,Rice,Potato'),
        ('Madeen Khan',  'madeen@demo.com', 'demo123', 'Rajasthan',    'Cotton,Onion,Maize'),
        ('Adil Patel',   'adil@demo.com',   'demo123', 'Gujarat',      'Cotton,Sugarcane'),
        ('Arif Sheikh',  'arif@demo.com',    'demo123', 'Punjab',       'Wheat,Rice'),
        ('Fayaz Ahmed',  'fayaz@demo.com',   'demo123', 'Karnataka',    'Tomato,Maize'),
    ]
    for name, email, pw, state, crops in users:
        existing = c.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone()
        if not existing:
            h = bcrypt.generate_password_hash(pw).decode('utf-8')
            c.execute('INSERT INTO users (name,email,password_hash,state,crops) VALUES (?,?,?,?,?)',
                      (name, email, h, state, crops))

    db.commit()

    # Seed demo detections for rahul (id=1)
    u = c.execute('SELECT id FROM users WHERE email=?', ('rahul@demo.com',)).fetchone()
    if u:
        uid = u['id']
        det_count = c.execute('SELECT COUNT(*) FROM detections WHERE user_id=?', (uid,)).fetchone()[0]
        if det_count == 0:
            sample_detections = [
                (uid,'Wheat','uploads/demo1.jpg','Yellow Rust',82,'Moderate',
                 json.dumps({"symptoms":["Yellow streaks on leaves","Powdery yellow pustules"],
                             "cause":"Fungal pathogen Puccinia striiformis",
                             "organic_treatment":["Neem oil spray 3%","Trichoderma viride application"],
                             "chemical_treatment":["Propiconazole 25 EC @ 0.1%","Tebuconazole 250 EW"],
                             "prevention_tips":["Use resistant varieties","Avoid excess nitrogen"],
                             "confidence":82,"severity":"Moderate","disease_name":"Yellow Rust"})),
                (uid,'Tomato','uploads/demo2.jpg','Late Blight',91,'Severe',
                 json.dumps({"symptoms":["Dark water-soaked lesions","White mold on leaf underside"],
                             "cause":"Oomycete Phytophthora infestans",
                             "organic_treatment":["Copper oxychloride spray","Bordeaux mixture"],
                             "chemical_treatment":["Mancozeb 75 WP @ 0.25%","Metalaxyl 8%+Mancozeb 64%"],
                             "prevention_tips":["Avoid overhead irrigation","Remove infected plants"],
                             "confidence":91,"severity":"Severe","disease_name":"Late Blight"})),
                (uid,'Potato','uploads/demo3.jpg','Early Blight',67,'Mild',
                 json.dumps({"symptoms":["Circular brown spots with concentric rings","Lower leaves affected first"],
                             "cause":"Fungal pathogen Alternaria solani",
                             "organic_treatment":["Neem oil 2% spray","Garlic extract spray"],
                             "chemical_treatment":["Chlorothalonil 75 WP","Azoxystrobin 23 SC"],
                             "prevention_tips":["Proper spacing for airflow","Balanced fertilization"],
                             "confidence":67,"severity":"Mild","disease_name":"Early Blight"})),
                (uid,'Rice','uploads/demo4.jpg','Blast Disease',88,'Severe',
                 json.dumps({"symptoms":["Diamond-shaped lesions on leaves","Neck rot causing panicle death"],
                             "cause":"Fungal pathogen Magnaporthe oryzae",
                             "organic_treatment":["Silicon-based fertilizers","Trichoderma application"],
                             "chemical_treatment":["Tricyclazole 75 WP @ 0.06%","Isoprothiolane 40 EC"],
                             "prevention_tips":["Use blast-resistant varieties","Balanced N application"],
                             "confidence":88,"severity":"Severe","disease_name":"Blast Disease"})),
                (uid,'Cotton','uploads/demo5.jpg','Leaf Curl Virus',74,'Moderate',
                 json.dumps({"symptoms":["Upward curling of leaves","Vein darkening and thickening"],
                             "cause":"Tomato Leaf Curl New Delhi Virus (ToLCNDV)",
                             "organic_treatment":["Neem seed kernel extract 5%","Yellow sticky traps"],
                             "chemical_treatment":["Imidacloprid 17.8 SL","Thiamethoxam 25 WG"],
                             "prevention_tips":["Control whitefly vectors","Remove infected plants"],
                             "confidence":74,"severity":"Moderate","disease_name":"Leaf Curl Virus"})),
                (uid,'Maize','uploads/demo6.jpg','Fall Armyworm',79,'Moderate',
                 json.dumps({"symptoms":["Ragged leaf feeding","Frass inside whorl"],
                             "cause":"Spodoptera frugiperda larval infestation",
                             "organic_treatment":["Beauveria bassiana spray","Neem oil 5%"],
                             "chemical_treatment":["Emamectin benzoate 5 SG","Spinetoram 11.7 SC"],
                             "prevention_tips":["Early planting to avoid pest peak","Pheromone traps"],
                             "confidence":79,"severity":"Moderate","disease_name":"Fall Armyworm"})),
            ]
            for d in sample_detections:
                c.execute('''INSERT INTO detections
                    (user_id,crop_type,image_path,disease_name,confidence,severity,treatment_json)
                    VALUES (?,?,?,?,?,?,?)''', d)
            db.commit()

    db.close()

# ── Flask-Login User ──────────────────────────────────────────────────────────

class User(UserMixin):
    def __init__(self, id, name, email, state, crops):
        self.id = id
        self.name = name
        self.email = email
        self.state = state
        self.crops = crops

@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    u = db.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
    db.close()
    if u:
        return User(u['id'], u['name'], u['email'], u['state'], u['crops'])
    return None

# ── Helpers ───────────────────────────────────────────────────────────────────

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_current_season():
    m = datetime.now().month
    if m in [3, 4, 5]:   return 'Spring (Vasant)'
    if m in [6, 7, 8]:   return 'Monsoon (Kharif)'
    if m in [9, 10, 11]: return 'Autumn (Rabi Prep)'
    return 'Winter (Rabi)'

def get_gemini_client():
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        return None
    return genai.Client(api_key=api_key)

# ── Mandi Price Data ──────────────────────────────────────────────────────────

MANDI_DATA = [
    # (mandi, state, crop, min_price, max_price, modal_price, unit, trend)
    ("Azadpur Mandi","Delhi","Tomato",800,2200,1600,"quintal","up"),
    ("Azadpur Mandi","Delhi","Potato",600,900,750,"quintal","down"),
    ("Azadpur Mandi","Delhi","Onion",700,1400,1100,"quintal","up"),
    ("Azadpur Mandi","Delhi","Wheat",1900,2100,2015,"quintal","stable"),
    ("Azadpur Mandi","Delhi","Rice",2800,3400,3100,"quintal","up"),
    ("Azadpur Mandi","Delhi","Maize",1400,1700,1550,"quintal","down"),
    ("Vashi APMC","Maharashtra","Tomato",900,2000,1500,"quintal","up"),
    ("Vashi APMC","Maharashtra","Potato",700,1000,850,"quintal","stable"),
    ("Vashi APMC","Maharashtra","Onion",800,1600,1200,"quintal","up"),
    ("Vashi APMC","Maharashtra","Rice",2600,3200,2900,"quintal","stable"),
    ("Vashi APMC","Maharashtra","Sugarcane",280,320,300,"quintal","stable"),
    ("Vashi APMC","Maharashtra","Cotton",6200,6800,6500,"quintal","up"),
    ("Pune APMC","Maharashtra","Wheat",1950,2150,2050,"quintal","stable"),
    ("Pune APMC","Maharashtra","Potato",650,950,800,"quintal","down"),
    ("Pune APMC","Maharashtra","Onion",750,1500,1150,"quintal","up"),
    ("Pune APMC","Maharashtra","Tomato",850,1900,1400,"quintal","up"),
    ("Koyambedu","Tamil Nadu","Tomato",700,1800,1300,"quintal","stable"),
    ("Koyambedu","Tamil Nadu","Rice",2700,3300,3000,"quintal","stable"),
    ("Koyambedu","Tamil Nadu","Onion",650,1350,1000,"quintal","down"),
    ("Koyambedu","Tamil Nadu","Potato",750,1050,900,"quintal","stable"),
    ("Koyambedu","Tamil Nadu","Maize",1350,1650,1500,"quintal","up"),
    ("Kolkata Koley","West Bengal","Rice",2500,3100,2800,"quintal","stable"),
    ("Kolkata Koley","West Bengal","Potato",550,850,700,"quintal","down"),
    ("Kolkata Koley","West Bengal","Onion",700,1400,1050,"quintal","stable"),
    ("Kolkata Koley","West Bengal","Maize",1300,1600,1450,"quintal","up"),
    ("Kolkata Koley","West Bengal","Tomato",800,2000,1400,"quintal","up"),
    ("Indore Mandi","Madhya Pradesh","Wheat",1900,2100,2000,"quintal","stable"),
    ("Indore Mandi","Madhya Pradesh","Soybean",4200,4800,4500,"quintal","up"),
    ("Indore Mandi","Madhya Pradesh","Onion",700,1300,1000,"quintal","down"),
    ("Indore Mandi","Madhya Pradesh","Potato",600,900,750,"quintal","down"),
    ("Indore Mandi","Madhya Pradesh","Maize",1350,1650,1500,"quintal","stable"),
    ("Indore Mandi","Madhya Pradesh","Cotton",6000,6600,6300,"quintal","up"),
    ("Ahmedabad APMC","Gujarat","Cotton",6400,7000,6700,"quintal","up"),
    ("Ahmedabad APMC","Gujarat","Wheat",2000,2200,2100,"quintal","stable"),
    ("Ahmedabad APMC","Gujarat","Potato",700,1000,850,"quintal","stable"),
    ("Ahmedabad APMC","Gujarat","Onion",750,1450,1100,"quintal","up"),
    ("Ahmedabad APMC","Gujarat","Rice",2800,3400,3100,"quintal","stable"),
    ("Muhana Mandi","Rajasthan","Wheat",1950,2150,2050,"quintal","stable"),
    ("Muhana Mandi","Rajasthan","Maize",1400,1700,1550,"quintal","up"),
    ("Muhana Mandi","Rajasthan","Onion",800,1500,1200,"quintal","up"),
    ("Muhana Mandi","Rajasthan","Potato",650,950,800,"quintal","stable"),
    ("Muhana Mandi","Rajasthan","Cotton",6100,6700,6400,"quintal","up"),
    ("Lucknow Mandi","Uttar Pradesh","Wheat",1900,2100,2000,"quintal","stable"),
    ("Lucknow Mandi","Uttar Pradesh","Rice",2700,3300,3000,"quintal","stable"),
    ("Lucknow Mandi","Uttar Pradesh","Sugarcane",290,330,310,"quintal","stable"),
    ("Lucknow Mandi","Uttar Pradesh","Potato",600,900,750,"quintal","down"),
    ("Lucknow Mandi","Uttar Pradesh","Onion",700,1400,1050,"quintal","stable"),
    ("Gaddiannaram","Telangana","Rice",2600,3200,2900,"quintal","up"),
    ("Gaddiannaram","Telangana","Cotton",6200,6900,6550,"quintal","up"),
    ("Gaddiannaram","Telangana","Maize",1350,1650,1500,"quintal","stable"),
    ("Gaddiannaram","Telangana","Tomato",700,1900,1300,"quintal","up"),
    ("Gaddiannaram","Telangana","Onion",650,1300,975,"quintal","down"),
    ("Yeshwanthpur APMC","Karnataka","Tomato",800,2100,1500,"quintal","up"),
    ("Yeshwanthpur APMC","Karnataka","Potato",700,1000,850,"quintal","stable"),
    ("Yeshwanthpur APMC","Karnataka","Onion",750,1450,1100,"quintal","up"),
    ("Yeshwanthpur APMC","Karnataka","Rice",2700,3300,3000,"quintal","stable"),
    ("Yeshwanthpur APMC","Karnataka","Maize",1400,1700,1550,"quintal","up"),
    ("Amritsar Mandi","Punjab","Wheat",2000,2200,2100,"quintal","stable"),
    ("Amritsar Mandi","Punjab","Rice",2800,3400,3100,"quintal","up"),
    ("Amritsar Mandi","Punjab","Potato",600,900,750,"quintal","down"),
    ("Karnal Mandi","Haryana","Wheat",1950,2200,2075,"quintal","stable"),
    ("Karnal Mandi","Haryana","Rice",2700,3300,3000,"quintal","stable"),
    ("Karnal Mandi","Haryana","Sugarcane",285,325,305,"quintal","stable"),
    ("Nashik APMC","Maharashtra","Onion",600,1600,1100,"quintal","up"),
    ("Nashik APMC","Maharashtra","Tomato",700,2000,1350,"quintal","up"),
    ("Nashik APMC","Maharashtra","Grapes",4000,8000,6000,"quintal","stable"),
    ("Hubli Mandi","Karnataka","Cotton",6100,6800,6450,"quintal","up"),
    ("Hubli Mandi","Karnataka","Maize",1350,1650,1500,"quintal","stable"),
    ("Hubli Mandi","Karnataka","Onion",700,1400,1050,"quintal","down"),
    ("Patna Mandi","Bihar","Rice",2600,3200,2900,"quintal","stable"),
    ("Patna Mandi","Bihar","Wheat",1900,2100,2000,"quintal","stable"),
    ("Patna Mandi","Bihar","Maize",1300,1600,1450,"quintal","up"),
    ("Bhubaneswar APMC","Odisha","Rice",2500,3100,2800,"quintal","stable"),
    ("Bhubaneswar APMC","Odisha","Potato",600,900,750,"quintal","stable"),
    ("Bhubaneswar APMC","Odisha","Tomato",750,1900,1300,"quintal","up"),
    ("Guwahati Mandi","Assam","Rice",2700,3400,3050,"quintal","up"),
    ("Guwahati Mandi","Assam","Potato",700,1000,850,"quintal","stable"),
    ("Raipur Mandi","Chhattisgarh","Rice",2500,3100,2800,"quintal","stable"),
    ("Raipur Mandi","Chhattisgarh","Wheat",1900,2100,2000,"quintal","stable"),
    ("Raipur Mandi","Chhattisgarh","Maize",1300,1600,1450,"quintal","up"),
]

# ── Crop Calendar Data ────────────────────────────────────────────────────────

CROP_CALENDAR = {
    1:  {"north":{"plant":["Mustard","Peas"],"harvest":["Wheat (late)","Barley"],"prepare":["Summer vegetable beds"]},
         "south":{"plant":["Rice (Rabi)","Banana"],"harvest":["Groundnut","Sunflower"],"prepare":["Canal irrigation"]},
         "east": {"plant":["Mustard","Lentil"],"harvest":["Paddy"],"prepare":["Soil testing"]},
         "west": {"plant":["Cumin","Fennel"],"harvest":["Cotton","Castor"],"prepare":["Compost pits"]},
         "central":{"plant":["Chickpea","Lentil"],"harvest":["Soybean"],"prepare":["Rabi field prep"]},
         "tips":"Winter crops need irrigation every 15-20 days. Apply potassium fertilizer for frost resistance."},
    2:  {"north":{"plant":["Spring Maize","Sunflower"],"harvest":["Mustard","Potato"],"prepare":["Kharif land prep"]},
         "south":{"plant":["Groundnut","Sesame"],"harvest":["Rice","Banana"],"prepare":["Summer irrigation"]},
         "east": {"plant":["Summer Vegetables","Jute nursery"],"harvest":["Mustard","Wheat"],"prepare":["Green manure crops"]},
         "west": {"plant":["Watermelon","Muskmelon"],"harvest":["Cumin","Fennel"],"prepare":["Drip irrigation setup"]},
         "central":{"plant":["Linseed","Sunflower"],"harvest":["Chickpea","Lentil"],"prepare":["Summer plowing"]},
         "tips":"Valentine month for crops! Check soil moisture. Prune fruit trees before new growth."},
    3:  {"north":{"plant":["Okra","Bitter Gourd"],"harvest":["Wheat","Mustard"],"prepare":["Paddy nursery beds"]},
         "south":{"plant":["Paddy Nursery","Vegetables"],"harvest":["Groundnut","Mango (early)"],"prepare":["Kharif preparation"]},
         "east": {"plant":["Jute","Summer Vegetables"],"harvest":["Lentil","Mustard"],"prepare":["Paddy nursery"]},
         "west": {"plant":["Mung Bean","Cotton nursery"],"harvest":["Wheat","Chickpea"],"prepare":["Cotton field prep"]},
         "central":{"plant":["Sesame","Mung Bean"],"harvest":["Wheat","Chickpea"],"prepare":["Black soil plowing"]},
         "tips":"Rabi harvest season. Store grains properly with neem leaves to prevent pests."},
    4:  {"north":{"plant":["Cotton","Maize","Groundnut"],"harvest":["Rabi crops complete"],"prepare":["Kharif beds"]},
         "south":{"plant":["Paddy (transplant)","Cotton"],"harvest":["Rabi vegetables"],"prepare":["Bund repair"]},
         "east": {"plant":["Jute","Aus Paddy"],"harvest":["Rabi complete"],"prepare":["Aman paddy nursery"]},
         "west": {"plant":["Cotton","Groundnut"],"harvest":["Wheat","Rabi done"],"prepare":["Moisture conservation"]},
         "central":{"plant":["Soybean nursery","Arhar"],"harvest":["Rabi complete"],"prepare":["Deep plowing"]},
         "tips":"Hot and dry. Mulch fields to conserve moisture. Start cotton sowing with good pre-monsoon showers."},
    5:  {"north":{"plant":["Paddy nursery","Arhar"],"harvest":["Maize (spring)"],"prepare":["Monsoon channel repair"]},
         "south":{"plant":["Paddy","Sugarcane"],"harvest":["Summer vegetables"],"prepare":["Water harvesting"]},
         "east": {"plant":["Jute main","Aus Paddy"],"harvest":["Early vegetables"],"prepare":["Flood control bunds"]},
         "west": {"plant":["Sesame","Bajra"],"harvest":["Summer crops"],"prepare":["Rainwater harvesting"]},
         "central":{"plant":["Soybean","Arhar"],"harvest":["Summer paddy"],"prepare":["Kharif land final"]},
         "tips":"Pre-monsoon activity. Check and clean irrigation channels. Apply organic matter to fields."},
    6:  {"north":{"plant":["Rice transplant","Bajra","Arhar"],"harvest":[],"prepare":["Kharif fertilizer"]},
         "south":{"plant":["Paddy main sowing","Groundnut"],"harvest":["Mango","Jackfruit"],"prepare":["Drainage channels"]},
         "east": {"plant":["Aman Paddy","Jute harvest early"],"harvest":["Garlic","Onion"],"prepare":["Flood-proof storage"]},
         "west": {"plant":["Cotton main","Groundnut","Bajra"],"harvest":[],"prepare":["Monsoon drainage"]},
         "central":{"plant":["Soybean main","Maize","Cotton"],"harvest":[],"prepare":["Weed management"]},
         "tips":"Monsoon begins! First rains — sow Kharif crops. Ensure field drainage to prevent waterlogging."},
    7:  {"north":{"plant":["Late Maize","Vegetables"],"harvest":[],"prepare":["Top dressing nitrogen"]},
         "south":{"plant":["Vegetables","Ginger","Turmeric"],"harvest":["Early mango done"],"prepare":["Weed control paddy"]},
         "east": {"plant":["Aman Paddy transplant"],"harvest":["Jute (early)"],"prepare":["Pest scouting"]},
         "west": {"plant":["Sesame","Castor"],"harvest":[],"prepare":["Drainage management"]},
         "central":{"plant":["Late Soybean","Arhar"],"harvest":[],"prepare":["Intercropping weeding"]},
         "tips":"Peak monsoon. Control weeds before they establish. Apply Urea top dressing to paddy."},
    8:  {"north":{"plant":["Radish","Spinach (late)"],"harvest":[],"prepare":["Rabi planning"]},
         "south":{"plant":["Turmeric","Banana suckers"],"harvest":["Early Kharif veggies"],"prepare":["Drainage improvement"]},
         "east": {"plant":["Late vegetables","Onion nursery"],"harvest":["Jute main"],"prepare":["Rabi land prep"]},
         "west": {"plant":["Late Cotton areas"],"harvest":["Early Groundnut"],"prepare":["Rabi crop plan"]},
         "central":{"plant":["Late Arhar","Vegetables"],"harvest":["Early Soybean"],"prepare":["Rabi soil prep"]},
         "tips":"Monsoon tapering. Scout for pests and diseases actively. Plan Rabi crop procurement."},
    9:  {"north":{"plant":["Potato","Cauliflower","Mustard nursery"],"harvest":["Arhar (early)","Maize"],"prepare":["Rabi land final"]},
         "south":{"plant":["Rabi Paddy","Vegetables"],"harvest":["Kharif Paddy begins"],"prepare":["Rabi irrigation"]},
         "east": {"plant":["Potato nursery","Mustard"],"harvest":["Aman Paddy early"],"prepare":["Rabi preparation"]},
         "west": {"plant":["Cumin nursery","Isabgol"],"harvest":["Cotton begins","Groundnut"],"prepare":["Winter crop beds"]},
         "central":{"plant":["Chickpea","Wheat nursery"],"harvest":["Soybean main","Maize"],"prepare":["Rabi fertilizer"]},
         "tips":"Kharif harvest begins! Proper drying and storage is crucial. Start Rabi planning now."},
    10: {"north":{"plant":["Wheat","Potato main","Peas"],"harvest":["Kharif complete","Cotton"],"prepare":["Winter storage"]},
         "south":{"plant":["Groundnut","Sunflower"],"harvest":["Kharif Paddy main"],"prepare":["Rabi irrigation ready"]},
         "east": {"plant":["Wheat","Potato","Mustard"],"harvest":["Aman Paddy main"],"prepare":["Winter crop storage"]},
         "west": {"plant":["Wheat","Cumin","Mustard"],"harvest":["Cotton","Groundnut"],"prepare":["Rabi fertilizer application"]},
         "central":{"plant":["Wheat","Chickpea main"],"harvest":["Arhar","Soybean complete"],"prepare":["Wheat bed final"]},
         "tips":"Biggest harvest month! Ensure mechanical threshers are ready. Store Kharif produce safely."},
    11: {"north":{"plant":["Garlic","Onion","Barley"],"harvest":["Late Cotton","Early Potato"],"prepare":["Irrigation scheduling"]},
         "south":{"plant":["Paddy (late Rabi)","Vegetables"],"harvest":["Groundnut","Sunflower"],"prepare":["Water management"]},
         "east": {"plant":["Lentil","Peas","Potato main"],"harvest":["Paddy complete"],"prepare":["Cold storage check"]},
         "west": {"plant":["Isabgol","Fennel","Garlic"],"harvest":["Late Cotton"],"prepare":["Drip irrigation winter"]},
         "central":{"plant":["Linseed","Safflower"],"harvest":["Cotton","Arhar"],"prepare":["Rabi irrigation"]},
         "tips":"Cool weather arrives. Apply phosphorus for root crops. Protect seedlings from frost in hilly areas."},
    12: {"north":{"plant":["Spring Vegetables (protected)"],"harvest":["Early Wheat areas","Mustard"],"prepare":["New year crop plan"]},
         "south":{"plant":["Sugarcane","Banana"],"harvest":["Rabi Paddy","Groundnut"],"prepare":["Annual soil testing"]},
         "east": {"plant":["Spring Onion","Garlic"],"harvest":["Potato (early)","Mustard"],"prepare":["Soil health card"]},
         "west": {"plant":["Spring crops"],"harvest":["Cumin","Isabgol"],"prepare":["Annual farm audit"]},
         "central":{"plant":["Late Rabi crops"],"harvest":["Chickpea early"],"prepare":["Annual soil testing"]},
         "tips":"Year-end planning. Get soil health card tested. Plan next year crop rotation. Apply FYM to fields."},
}

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        email = request.form.get('email','').strip().lower()
        password = request.form.get('password','')
        state = request.form.get('state','')
        crops = request.form.getlist('crops')

        if not all([name, email, password, state]):
            flash('Sare fields bharna zaroori hai!', 'danger')
            return render_template('register.html', states=INDIAN_STATES, crops=CROPS)

        db = get_db()
        existing = db.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone()
        if existing:
            db.close()
            flash('Yeh email already registered hai!', 'danger')
            return render_template('register.html', states=INDIAN_STATES, crops=CROPS)

        ph = bcrypt.generate_password_hash(password).decode('utf-8')
        db.execute('INSERT INTO users (name,email,password_hash,state,crops) VALUES (?,?,?,?,?)',
                   (name, email, ph, state, ','.join(crops)))
        db.commit()
        db.close()
        flash('Registration ho gayi! Ab login karein.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', states=INDIAN_STATES, crops=CROPS)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email','').strip().lower()
        password = request.form.get('password','')
        db = get_db()
        u = db.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
        db.close()
        if u and bcrypt.check_password_hash(u['password_hash'], password):
            user_obj = User(u['id'], u['name'], u['email'], u['state'], u['crops'])
            login_user(user_obj)
            flash(f'Swagat hai, {u["name"]}! 🌱', 'success')
            return redirect(url_for('dashboard'))
        flash('Email ya password galat hai!', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Aap logout ho gaye. Phir milenge!', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    uid = current_user.id
    total = db.execute('SELECT COUNT(*) FROM detections WHERE user_id=?', (uid,)).fetchone()[0]
    diseases = db.execute('SELECT COUNT(DISTINCT disease_name) FROM detections WHERE user_id=?', (uid,)).fetchone()[0]
    crops_count = db.execute('SELECT COUNT(DISTINCT crop_type) FROM detections WHERE user_id=?', (uid,)).fetchone()[0]
    advisories = db.execute('SELECT COUNT(*) FROM advisories WHERE user_id=?', (uid,)).fetchone()[0]
    recent = db.execute('''SELECT * FROM detections WHERE user_id=? ORDER BY created_at DESC LIMIT 5''', (uid,)).fetchall()
    db.close()
    season = get_current_season()
    tips = [
        "🌿 Neem oil spray har 15 din mein ek baar karein pest control ke liye.",
        "💧 Drip irrigation se 40% paani ki bachat hoti hai — zaroor sochein.",
        "🧪 Mitti ka test kare bhar ek baar — sahi nutrients ke liye.",
        "🌡️ Subah jaldi irrigation karein — evaporation kam hoti hai.",
        "🐝 Pollinators ke liye kheton ke paas phool lagaein.",
        "♻️ Crop rotation se mitti ki sehat badhti hai aur pests kam hote hain.",
        "📱 FasalGuru ko bookmark karein — fasal ki jankari hamesha saath rahegi!",
        "🌾 Beej ka selection sabse zaroori — certified seeds hi use karein.",
    ]
    return render_template('dashboard.html', total=total, diseases=diseases,
                           crops_count=crops_count, advisories_count=advisories,
                           recent=recent, season=season, tips=tips)

@app.route('/disease-detect', methods=['GET', 'POST'])
@login_required
def disease_detect():
    if request.method == 'POST':
        print("=== DEBUG ===")
        print("FILES:", dict(request.files))
        print("FORM:", dict(request.form))
        print("=============")
        crop_type = request.form.get('crop_type', 'Unknown')
        if 'image' not in request.files:
            return jsonify({'error': 'Koi image upload nahi ki!'}), 400
        file = request.files['image']
        if not file or not allowed_file(file.filename):
            return jsonify({'error': 'Galat file format! JPG/PNG use karein.'}), 400

        filename = secure_filename(f"{current_user.id}_{int(datetime.now().timestamp())}_{file.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(filepath)

        client = get_gemini_client()
        if not client:
            return jsonify({'error': 'GEMINI_API_KEY .env mein set nahi hai!'}), 500

        try:
            with open(filepath, 'rb') as f:
                img_data = f.read()

            img_b64 = base64.b64encode(img_data).decode()
            ext = filename.rsplit('.', 1)[1].lower()
            mime_map = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                        'png': 'image/png', 'gif': 'image/gif', 'webp': 'image/webp'}
            mime_type = mime_map.get(ext, 'image/jpeg')

            prompt = f"""You are an expert Indian agricultural scientist and crop disease specialist. 
Analyze this {crop_type} plant image for diseases.

Return ONLY a valid JSON object (no markdown, no code blocks) with exactly these fields:
{{
  "disease_name": "name of the disease or 'Healthy Plant' if no disease found",
  "confidence": <number 0-100>,
  "symptoms": ["symptom1", "symptom2", "symptom3"],
  "cause": "detailed cause of the disease",
  "organic_treatment": ["step1", "step2", "step3"],
  "chemical_treatment": ["product and dosage1", "product and dosage2"],
  "prevention_tips": ["tip1", "tip2", "tip3"],
  "severity": "Mild" or "Moderate" or "Severe" or "None"
}}

If the image is not a plant or crop, return confidence as 0 and disease_name as "Image Not Recognized".
Be specific to Indian farming conditions and use products available in India."""

            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[
                    types.Part.from_bytes(data=img_data, mime_type=mime_type),
                    types.Part.from_text(text=prompt)
                ]
            )

            raw = response.text.strip()
            raw = raw.replace('```json', '').replace('```', '').strip()
            result = json.loads(raw)

            db = get_db()
            db.execute('''INSERT INTO detections
                (user_id, crop_type, image_path, disease_name, confidence, severity, treatment_json)
                VALUES (?,?,?,?,?,?,?)''',
                (current_user.id, crop_type, filepath, result.get('disease_name','Unknown'),
                 result.get('confidence', 0), result.get('severity','Unknown'), json.dumps(result)))
            db.commit()
            db.close()

            return jsonify({'success': True, 'result': result})

        except json.JSONDecodeError:
            return jsonify({'error': 'AI response parse nahi ho saka. Phir try karein.'}), 500
        except Exception as e:
            return jsonify({'error': f'AI Error: {str(e)}'}), 500

    return render_template('disease_detect.html', crops=CROPS)

@app.route('/mandi-prices')
@login_required
def mandi_prices():
    crop_filter = request.args.get('crop', '')
    state_filter = request.args.get('state', '')
    data = MANDI_DATA
    if crop_filter:
        data = [d for d in data if d[2].lower() == crop_filter.lower()]
    if state_filter:
        data = [d for d in data if d[1].lower() == state_filter.lower()]

    states = sorted(set(d[1] for d in MANDI_DATA))
    crops_list = sorted(set(d[2] for d in MANDI_DATA))

    # Best mandi = highest modal price for each crop
    best = {}
    for row in MANDI_DATA:
        crop = row[2]
        if crop not in best or row[4] > best[crop][4]:
            best[crop] = row

    return render_template('mandi_prices.html', data=data, states=states,
                           crops_list=crops_list, best=best,
                           crop_filter=crop_filter, state_filter=state_filter)

@app.route('/weather-advisory', methods=['GET', 'POST'])
@login_required
def weather_advisory():
    advisory = None
    city = ''
    if request.method == 'POST':
        city = request.form.get('city', '').strip()
        if not city:
            flash('City ka naam daalna zaroori hai!', 'warning')
            return redirect(url_for('weather_advisory'))

        season = get_current_season()
        month_name = datetime.now().strftime('%B')
        client = get_gemini_client()

        if not client:
            flash('GEMINI_API_KEY set nahi hai!', 'danger')
            return redirect(url_for('weather_advisory'))

        prompt = f"""You are an expert Indian agricultural extension officer providing farm advisory.

Location: {city}, India
Current Month: {month_name}
Current Season: {season}
Farmer's crops: {current_user.crops or 'Mixed crops'}

Write a detailed 400-word farm advisory in simple Hindi-English mixed language (Hinglish) covering:
1. Is mahine ka mausam aur fasal par asar
2. Sinchai ka schedule (irrigation timing)
3. Khad/Urvarak application timing and recommendations
4. Keede-makode aur bimari ka khatra is season mein
5. Fasal ki katai/harvesting tips (if applicable)
6. Koi special advice for {city} region

Write in a warm, helpful tone like a knowledgeable friend. Use bullet points where helpful.
End with an encouraging message for the farmer."""

        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[types.Part.from_text(text=prompt)]
            )
            advisory = response.text

            db = get_db()
            db.execute('INSERT INTO advisories (user_id, city, season, advisory_text) VALUES (?,?,?,?)',
                       (current_user.id, city, season, advisory))
            db.commit()
            db.close()
        except Exception as e:
            flash(f'Advisory generate nahi ho saki: {str(e)}', 'danger')

    past = []
    db = get_db()
    past = db.execute('SELECT * FROM advisories WHERE user_id=? ORDER BY created_at DESC LIMIT 5',
                      (current_user.id,)).fetchall()
    db.close()

    return render_template('weather_advisory.html', advisory=advisory, city=city,
                           season=get_current_season(), past=past)

@app.route('/crop-calendar')
@login_required
def crop_calendar():
    region = request.args.get('region', 'north')
    current_month = datetime.now().month
    return render_template('crop_calendar.html', calendar=CROP_CALENDAR,
                           region=region, current_month=current_month)

@app.route('/history')
@login_required
def history():
    crop_filter = request.args.get('crop', '')
    db = get_db()
    if crop_filter:
        records = db.execute(
            'SELECT * FROM detections WHERE user_id=? AND crop_type=? ORDER BY created_at DESC',
            (current_user.id, crop_filter)).fetchall()
    else:
        records = db.execute(
            'SELECT * FROM detections WHERE user_id=? ORDER BY created_at DESC',
            (current_user.id,)).fetchall()

    crops_used = db.execute(
        'SELECT DISTINCT crop_type FROM detections WHERE user_id=?',
        (current_user.id,)).fetchall()
    db.close()

    parsed = []
    for r in records:
        d = dict(r)
        try:
            d['treatment'] = json.loads(r['treatment_json'] or '{}')
        except:
            d['treatment'] = {}
        parsed.append(d)

    return render_template('history.html', records=parsed,
                           crops_used=[c['crop_type'] for c in crops_used],
                           crop_filter=crop_filter)

@app.route('/delete-detection/<int:det_id>', methods=['POST'])
@login_required
def delete_detection(det_id):
    db = get_db()
    db.execute('DELETE FROM detections WHERE id=? AND user_id=?', (det_id, current_user.id))
    db.commit()
    db.close()
    flash('Record delete ho gaya!', 'success')
    return redirect(url_for('history'))

@app.route('/export-history')
@login_required
def export_history():
    db = get_db()
    records = db.execute(
        'SELECT * FROM detections WHERE user_id=? ORDER BY created_at DESC',
        (current_user.id,)).fetchall()
    db.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Crop', 'Disease', 'Confidence', 'Severity'])
    for r in records:
        writer.writerow([r['created_at'], r['crop_type'], r['disease_name'],
                         f"{r['confidence']:.0f}%", r['severity']])

    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=fasalguru_history.csv'
    response.headers['Content-Type'] = 'text/csv'
    return response

init_db()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
