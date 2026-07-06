# 🌾 FasalGuru — Apni Fasal Ka Smart Doctor

AI-powered crop disease detection and smart farm advisory platform for Indian farmers.

## Features
- 🔬 **AI Crop Disease Detector** — Upload plant photo → Gemini Vision analyzes → instant diagnosis + treatment
- 📊 **Mandi Price Tracker** — Live prices from 15+ mandis across India
- 🌦️ **Weather-Based Advisory** — AI-generated personalized farm advisory for your region
- 📅 **Crop Calendar** — Month-wise planting/harvesting guide for all regions
- 📋 **Detection History** — All past detections saved with full reports

## Setup

### 1. Install Dependencies
```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
copy .env.example .env         # Windows
```
Edit `.env` and add your Gemini API key:
```
GEMINI_API_KEY=your_key_here
SECRET_KEY=fasalguru_secret_2024
```

Get free Gemini API key: https://aistudio.google.com/apikey

### 3. Run
```bash
python app.py
```
Open: http://localhost:5000

## Demo Accounts
| Email | Password |
|-------|----------|
| rahul@demo.com | demo123 |
| madeen@demo.com | demo123 |

## Tech Stack
- **Backend:** Python Flask + SQLite
- **Frontend:** HTML + CSS + Vanilla JS
- **AI:** Google Gemini 2.0 Flash (Vision)
- **Auth:** Flask-Login + Flask-Bcrypt

## Project Structure
```
fasalguru/
├── app.py              # Main Flask app
├── requirements.txt
├── .env.example
├── uploads/            # User uploaded images
├── templates/          # Jinja2 HTML templates
└── static/
    ├── css/style.css
    └── js/main.js
```
