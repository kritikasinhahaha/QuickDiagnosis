# 🩺 QuickDiagnosis - Smart Medical Screening Web & Mobile App

**QuickDiagnosis** is a gentle, intelligent preliminary medical screening and health guidance web application. It guides users through an intuitive, step-by-step diagnostic workflow using personal demographics and an interactive faceless human anatomical model to highlight the top 4–5 probable health conditions, along with comprehensive home and medical curing measurements.

---

## 🌟 Key Features

1. **Warm Welcoming Homepage**:
   - Reassuring, empathetic introduction with an inspiring daily health affirmation.
   - Clean 3-step visual preview explaining the screening procedure.

2. **Step 1: Selection-Driven Personal Profile**:
   - Fast selection cards for **Gender** (Female, Male, Non-Binary/Other).
   - Interactive sliders and quick pills for **Age** (Child, Teen, Young Adult, Adult, Senior) and **Weight**.
   - Demographics directly feed into the probabilistic disease scoring engine (incorporating female/male risk factors and pediatric/geriatric prevalence).

3. **Step 2: Interactive Faceless Human Anatomical Model**:
   - Modern, minimalist faceless vector mannequin that dynamically adapts its silhouette based on chosen gender.
   - Clickable interactive hotspots for 8 body systems:
     - 🧠 **Nervous & Head System**
     - 🫁 **Respiratory System**
     - 🫀 **Cardiovascular System**
     - 🫄 **Digestive & Gastrointestinal System**
     - 🦴 **Musculoskeletal System**
     - 🛡️ **Skin & Hair System**
     - 💧 **Urinary & Renal System**
     - 🧬 **Endocrine & Metabolic System**
   - **Common / General Symptoms Section**: Prominently highlights whole-body systemic symptoms (High/Mild Fever, Extreme Fatigue, Chills, Night Sweats, Weight Loss, Body Aches, Dizziness).
   - Real-time reactive counter badge and selected symptoms review box.

4. **Step 3: Probable Disease Results & Empathetic Comfort**:
   - Displays the **top 4 to 5 most probable diseases** ranked by probability percentage.
   - Transparent breakdown of matched symptoms vs missing symptoms.
   - Clear demographic risk explanations (e.g., *"Elevated prevalence in females aged 20–40"*).
   - **Motivational banner**: Comforting words (*"You are stronger than you feel right now. You are never alone on this journey."*) with dynamic affirmation refresh.
   - **Medical Disclaimer**: Clear notification that QuickDiagnosis provides probabilistic screening, not a definitive clinical diagnosis.

5. **Step 4 / Modal: Disease In-Depth Guide & Curing Measures**:
   - Clicking any probable disease opens an extensive care guide:
     - 🩺 **What is this condition?** (Plain-English medical definition)
     - 🔍 **Demographic Rationale & Triggers**
     - 🏠 **Immediate Home Care Measures** (Rest, hydration, compresses, positioning)
     - 🥗 **Dietary & Lifestyle Precautions** (Foods to eat/avoid, daily habits)
     - 🏥 **Typical Medical Treatments** (Tests, prescriptions, clinical therapies)
     - ⚠️ **When to See a Doctor Immediately** (Emergency warning red flags)
     - 🛡️ **Long-Term Prevention Tips**

6. **Installable Progressive Web App (PWA) & Mobile Friendly**:
   - Includes `manifest.json`, Service Worker (`sw.js`), and app icons.
   - Tap **"Install App"** on desktop or **"Add to Home Screen"** on iOS/Android to install QuickDiagnosis as a native app on your device.
   - Fully responsive design with glassmorphism, micro-animations, and high contrast accessibility.

7. **Vercel Ready Deployment**:
   - Configured with `vercel.json`, `requirements.txt`, and serverless entrypoint `api/index.py`.

---

## 🛠️ Technology Stack (Strictly Compliant)

- **Backend**:
  - **Python 3**:
    - **Object-Oriented Programming (OOP)**: `Patient`, `Symptom`, `Disease`, `DiagnosisMatch`, `DiagnosticEngine`, `MedicalKnowledgeBase`.
    - **Data Structures**: Sets (for $O(1)$ symptom intersection/union), Dictionaries/Hash Maps, Priority ranking lists.
    - **File Handling**: JSON reading and session logging in `data/diagnosis_logs.json`.
    - **Flask**: Lightweight RESTful web framework.
- **Frontend**:
  - **HTML5**: Semantic, accessible markup.
  - **Vanilla CSS3**: Custom modern medical design system with glassmorphism and animations.
  - **Vanilla JavaScript (ES6+)**: Dynamic wizard navigation, SVG hotspot mapping, PWA hooks, and modal dialogs.
  - **JSON**: Structured medical databases for symptoms, diseases, systems, and quotes.

---

## 🚀 How to Run Locally

### 1. From the project root or Python folder:
```bash
python f:\Python\run_quickdiagnosis.py
```
Or navigate into `QuickDiagnosis`:
```bash
cd f:\Python\QuickDiagnosis
python app.py
```

### 2. Open in your web browser:
Visit:
```
http://127.0.0.1:5050  (or http://127.0.0.1:5000)
```

---

## ☁️ How to Deploy to Vercel

1. Make sure the Vercel CLI is installed (`npm i -g vercel`) or connect your GitHub repository to Vercel.
2. In the `QuickDiagnosis` folder:
```bash
cd f:\Python\QuickDiagnosis
vercel
```
3. Vercel will automatically detect `vercel.json` and deploy `api/index.py` as a serverless Python web application.

---

## 📁 File Structure

```
QuickDiagnosis/
├── app.py                      # Main Flask application & REST endpoints
├── models.py                   # Pure Python OOP models (Patient, Symptom, Disease, etc.)
├── diagnostic_engine.py        # Probabilistic matching & demographic risk algorithms
├── vercel.json                 # Vercel deployment configuration
├── requirements.txt            # Dependencies (Flask, Werkzeug)
├── api/
│   └── index.py                # Vercel serverless entry point
├── data/
│   ├── body_systems.json       # 8 anatomical body systems definition
│   ├── symptoms.json           # 66+ categorized symptoms & weights
│   ├── diseases.json           # 25+ comprehensive medical disease profiles
│   ├── motivational_quotes.json# Empathetic motivational quotes
│   └── diagnosis_logs.json     # Anonymous screening session history (auto-generated)
├── static/
│   ├── css/
│   │   └── style.css           # Glassmorphic, responsive, mobile-first styles
│   ├── js/
│   │   └── app.js              # Pure JavaScript wizard & interactive SVG logic
│   ├── icons/
│   │   ├── icon.svg            # Vector stethoscope & pulse app icon
│   │   ├── icon-192.png        # PWA 192x192 icon
│   │   └── icon-512.png        # PWA 512x512 icon
│   ├── manifest.json           # Progressive Web App manifest
│   └── sw.js                   # Service Worker for offline & installability
└── templates/
    └── index.html              # Single Page Application HTML5 template
```
