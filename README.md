# 🌾 FasalGuru — AI-Powered Crop Health & Farm Advisory Platform

> An applied GenAI solution helping Indian farmers detect crop diseases instantly and make smarter farming decisions — powered by computer vision and generative AI.

## 🎯 Overview

FasalGuru bridges the gap between traditional farming and AI-powered agriculture. 
Farmers often lack timely access to agricultural experts for diagnosing crop diseases 
or planning based on weather and market conditions. FasalGuru solves this using 
**Google Gemini's multimodal AI** — farmers simply upload a photo of their crop and 
get instant diagnosis, treatment advice, and region-specific farming guidance.

## ✨ Key Features

| Feature | Description |
|---|---|
| 🔬 AI Crop Disease Detector | Upload a plant photo → Gemini Vision analyzes → instant diagnosis + treatment plan |
| 📊 Mandi Price Tracker | Live crop prices aggregated from 15+ mandis across India |
| 🌦️ Weather-Based Advisory | AI-generated, region-specific farming advisory using weather data |
| 📅 Crop Calendar | Month-wise planting/harvesting guide tailored to region |
| 📋 Detection History | Full history of past disease detections with saved reports |

## 🧠 AI/GenAI Architecture

| Component | Role |
|---|---|
| **Google Gemini 2.0 Flash (Vision)** | Multimodal AI for image-based disease detection and diagnosis |
| **Prompt Engineering** | Domain-tuned prompts for accurate agricultural diagnosis in simple language |
| **Weather Advisory Engine** | LLM-generated personalized recommendations based on live weather data |
| **Flask-Login + Bcrypt** | Secure user authentication and session management |

## 🛠️ Tech Stack

**Backend:** Python, Flask, SQLite  
**Frontend:** HTML, CSS, Vanilla JS  
**AI:** Google Gemini 2.0 Flash (Vision)  
**Auth:** Flask-Login, Flask-Bcrypt

## 📂 Project Structure

```
fasalguru/
├── app.py              # Main Flask application
├── requirements.txt
├── .env.example
├── uploads/            # User-uploaded crop images
├── templates/          # Jinja2 HTML templates
└── static/
    ├── css/style.css
    └── js/main.js
```

## 🚀 Getting Started

### 1. Install Dependencies
```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
copy .env.example .env          # Windows
```

Edit `.env` and add your Gemini API key:
```
GEMINI_API_KEY=your_key_here
SECRET_KEY=your_secret_key_here
```

Get a free Gemini API key: https://aistudio.google.com/apikey

### 3. Run the App
```bash
python app.py
```
Visit: http://localhost:5000

## 📌 Roadmap / Future Improvements

- [ ] Multilingual support for regional language farmers
- [ ] Offline-first mode for low-connectivity rural areas
- [ ] Integration with government crop insurance schemes

## 👤 About the Developer

Built by **Imran Khan** — BCA final-year student specializing in **Applied AI Engineering** 
and **Generative AI solution development**, focused on building AI products that solve 
real-world problems for underserved communities.

📫 Open to **AI Solution Developer** / **Applied AI Engineer** roles.  
🔗 [GitHub](https://github.com/Rev-ImranKhan)
```
