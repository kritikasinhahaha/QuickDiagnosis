"""
QuickDiagnosis - Main Flask Application
Provides RESTful APIs and UI rendering for medical symptom assessment.
Compliant with Vercel serverless deployment and local standalone execution.
"""

import os
from flask import Flask, render_template, request, jsonify, send_from_directory
from diagnostic_engine import MedicalKnowledgeBase, DiagnosticEngine
from models import Patient

# Configure application directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")

app = Flask(
    __name__,
    static_folder=STATIC_DIR,
    template_folder=TEMPLATE_DIR
)

# Initialize medical knowledge base and diagnostic engine
kb = MedicalKnowledgeBase(DATA_DIR)
engine = DiagnosticEngine(kb)


@app.route("/")
def index():
    """Renders the single-page application homepage."""
    return render_template("index.html")


@app.route("/manifest.json")
def manifest():
    """Serves the Progressive Web App manifest for desktop & mobile installation."""
    return send_from_directory(STATIC_DIR, "manifest.json", mimetype="application/manifest+json")


@app.route("/sw.js")
def service_worker():
    """Serves the Service Worker for offline resilience and PWA functionality."""
    return send_from_directory(STATIC_DIR, "sw.js", mimetype="application/javascript")


@app.route("/static/<path:filename>")
def serve_static(filename):
    """Explicitly serves static assets (CSS, JS, images, icons) with proper headers."""
    return send_from_directory(STATIC_DIR, filename)

@app.route("/api/config", methods=["GET"])
def get_config():
    """
    Returns setup configuration, personal detail options,
    body systems, and general symptoms.
    """
    general_symptoms = [s.to_dict() for s in kb.symptoms_by_system.get("general", [])]
    return jsonify({
        "app_name": "QuickDiagnosis",
        "tagline": "Gentle, Intelligent & Privacy-First Medical Symptom Screening",
        "gender_options": [
            {"id": "female", "label": "Female", "icon": "👩", "desc": "Includes female-specific and hormonal risk profiles"},
            {"id": "male", "label": "Male", "icon": "👨", "desc": "Includes male-specific and hormonal risk profiles"},
            {"id": "other", "label": "Non-Binary / Other", "icon": "🧑", "desc": "Standard inclusive biological screening"}
        ],
        "age_brackets": [
            {"label": "Child (1-12 yrs)", "min": 1, "max": 12, "default": 8},
            {"label": "Teen (13-19 yrs)", "min": 13, "max": 19, "default": 16},
            {"label": "Young Adult (20-39 yrs)", "min": 20, "max": 39, "default": 26},
            {"label": "Adult (40-59 yrs)", "min": 40, "max": 59, "default": 48},
            {"label": "Senior (60+ yrs)", "min": 60, "max": 100, "default": 68}
        ],
        "weight_ranges": [
            {"id": "underweight", "label": "Light / Under 50 kg", "min": 35, "max": 49, "default": 45},
            {"id": "normal", "label": "Standard (50 - 70 kg)", "min": 50, "max": 70, "default": 62},
            {"id": "moderate", "label": "Moderate (71 - 85 kg)", "min": 71, "max": 85, "default": 78},
            {"id": "heavy", "label": "Above 85 kg", "min": 86, "max": 130, "default": 95}
        ],
        "body_systems": kb.systems,
        "general_symptoms": general_symptoms,
        "welcome_quote": kb.get_motivational_quote("step_transition")
    })


@app.route("/api/symptoms", methods=["GET"])
def get_all_symptoms():
    """Returns all symptoms organized by body system."""
    categorized = {}
    for system_id, symptom_list in kb.symptoms_by_system.items():
        categorized[system_id] = [s.to_dict() for s in symptom_list]
    return jsonify({
        "systems": kb.systems,
        "symptoms_by_system": categorized,
        "total_count": len(kb.symptoms_by_id)
    })


@app.route("/api/diagnose", methods=["POST"])
def run_diagnosis():
    """
    Executes probabilistic medical analysis based on personal details and symptoms.
    Returns the top 4-5 probable diseases with probability percentages.
    """
    data = request.get_json(force=True, silent=True) or {}
    
    gender = data.get("gender", "female")
    age = data.get("age", 25)
    weight = data.get("weight", 60.0)
    selected_symptoms = data.get("symptoms", [])

    try:
        age_int = int(age)
    except (ValueError, TypeError):
        age_int = 25

    try:
        weight_float = float(weight)
    except (ValueError, TypeError):
        weight_float = 60.0

    patient = Patient(gender=gender, age=age_int, weight=weight_float)
    diagnosis_output = engine.diagnose(patient, selected_symptoms)
    
    return jsonify(diagnosis_output)


@app.route("/api/disease/<disease_id>", methods=["GET"])
def get_disease_detail(disease_id: str):
    """
    Returns comprehensive educational information, root causes,
    and action measurements (home cures, diet, when to see doctor, medical care)
    for a selected probable disease.
    """
    disease = kb.get_disease_by_id(disease_id)
    if not disease:
        return jsonify({"error": f"Disease with ID '{disease_id}' not found."}), 404
    
    data = disease.to_full_dict()
    # Resolve symptom names for readability
    data["core_symptom_names"] = [kb.symptom_name_map.get(s, s) for s in disease.core_symptoms]
    data["secondary_symptom_names"] = [kb.symptom_name_map.get(s, s) for s in disease.secondary_symptoms]
    data["motivational_message"] = kb.get_motivational_quote("general_comfort")
    
    return jsonify(data)


@app.route("/api/quote", methods=["GET"])
def get_quote():
    """Returns an empathetic supportive message."""
    context = request.args.get("context", "after_result")
    quote = kb.get_motivational_quote(context)
    return jsonify({"quote": quote})


if __name__ == "__main__":
    # Local development server
    port = int(os.environ.get("PORT", 5000))
    print(f"QuickDiagnosis server running on http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)
