#  APPLICATION FLASK_Diabet_Predict

from flask import Flask, render_template, request, jsonify, redirect, url_for
import numpy as np
import joblib
import os
import sqlite3
from datetime import datetime

BASE_DIR = 'C:/Users/Pigeon/Desktop/Projet_Diabete_App'
TEMPLATE_DIR = os.path.join(BASE_DIR, 'app', 'templates')
DB_PATH = os.path.join(BASE_DIR, 'database', 'predictions.db')
MODEL_PATH = os.path.join(BASE_DIR, 'models', 'best_model.pkl')
SCALER_PATH = os.path.join(BASE_DIR, 'models', 'scaler.pkl')

app = Flask(__name__, template_folder=TEMPLATE_DIR)

print(" APPLICATION DE PRÉDICTION DU DIABÈTE")
print("--"*30)

model = joblib.load(MODEL_PATH)
scaler = joblib.load(SCALER_PATH)
print(f" Modèle chargé")

def get_connection():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Base de données non trouvée : {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def save_patient(data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO patients (nom, postnom, pregnancies, glucose, blood_pressure, skin_thickness,
                         insulin, bmi, dpf, age)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (data['nom'], data['postnom'], data['pregnancies'], data['glucose'], data['blood_pressure'],
          data['skin_thickness'], data['insulin'], data['bmi'],
          data['dpf'], data['age']))
    patient_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return patient_id

def save_prediction(patient_id, prediction, probability, model_used='XGBoost'):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO predictions (patient_id, prediction, probability, model_used)
    VALUES (?, ?, ?, ?)
    ''', (patient_id, prediction, probability, model_used))
    conn.commit()
    conn.close()

def get_statistics():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM v_statistics')
        stats = cursor.fetchone()
        conn.close()
        if stats:
            return dict(stats)
        else:
            return {
                'total_predictions': 0,
                'total_patients': 0,
                'diabetics': 0,
                'non_diabetics': 0,
                'diabetes_rate': 0.0
            }
    except Exception as e:
        return {
            'total_predictions': 0,
            'total_patients': 0,
            'diabetics': 0,
            'non_diabetics': 0,
            'diabetes_rate': 0.0
        }

def get_history(page=1, per_page=5):
    offset = (page - 1) * per_page
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as total FROM v_predictions_complete')
    total = cursor.fetchone()['total']
    cursor.execute('''
    SELECT * FROM v_predictions_complete 
    ORDER BY prediction_date DESC 
    LIMIT ? OFFSET ?
    ''', (per_page, offset))
    history = cursor.fetchall()
    conn.close()
    return history, total

def get_all_patients(limit=100):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM patients ORDER BY created_at DESC LIMIT ?', (limit,))
    patients = cursor.fetchall()
    conn.close()
    return patients

def get_patient_by_id(patient_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT p.*, pr.id as prediction_id, pr.prediction, pr.probability, pr.created_at as prediction_date
    FROM patients p
    JOIN predictions pr ON p.id = pr.patient_id
    WHERE p.id = ?
    ORDER BY pr.created_at DESC
    LIMIT 1
    ''', (patient_id,))
    patient = cursor.fetchone()
    conn.close()
    return patient

def delete_prediction(prediction_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT patient_id FROM predictions WHERE id = ?', (prediction_id,))
    result = cursor.fetchone()
    if result:
        patient_id = result['patient_id']
        cursor.execute('DELETE FROM predictions WHERE id = ?', (prediction_id,))
        cursor.execute('DELETE FROM patients WHERE id = ?', (patient_id,))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def update_patient(prediction_id, data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT patient_id FROM predictions WHERE id = ?', (prediction_id,))
    result = cursor.fetchone()
    if result:
        patient_id = result['patient_id']
        cursor.execute('''
        UPDATE patients 
        SET nom = ?, postnom = ?, pregnancies = ?, glucose = ?, 
            blood_pressure = ?, skin_thickness = ?, insulin = ?, 
            bmi = ?, dpf = ?, age = ?
        WHERE id = ?
        ''', (data['nom'], data['postnom'], data['pregnancies'], 
              data['glucose'], data['blood_pressure'], data['skin_thickness'],
              data['insulin'], data['bmi'], data['dpf'], data['age'],
              patient_id))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

# LES ROUTES


@app.route('/')
def home():
    stats = get_statistics()
    return render_template('index.html', stats=stats)

@app.route('/form')
def form():
    stats = get_statistics()
    return render_template('form.html', stats=stats)

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = {
            'nom': request.form['nom'],
            'postnom': request.form['postnom'],
            'pregnancies': float(request.form['pregnancies']),
            'glucose': float(request.form['glucose']),
            'blood_pressure': float(request.form['blood_pressure']),
            'skin_thickness': float(request.form['skin_thickness']),
            'insulin': float(request.form['insulin']),
            'bmi': float(request.form['bmi']),
            'dpf': float(request.form['dpf']),
            'age': float(request.form['age'])
        }
        input_data = np.array([[
            data['pregnancies'], data['glucose'], data['blood_pressure'],
            data['skin_thickness'], data['insulin'], data['bmi'],
            data['dpf'], data['age']
        ]])
        input_scaled = scaler.transform(input_data)
        prediction = int(model.predict(input_scaled)[0])
        probability = float(model.predict_proba(input_scaled)[0][1])
        patient_id = save_patient(data)
        save_prediction(patient_id, prediction, probability)
        if prediction == 0:
            result = "Non-diabétique "
            color = "green"
            advice = "Vous êtes en bonne santé ! Continuez à maintenir un mode de vie sain."
            result_class = "success"
        else:
            result = "Diabétique "
            color = "red"
            advice = " Consultez un médecin pour un diagnostic plus approfondi."
            result_class = "danger"
        stats = get_statistics()
        return render_template('form.html', 
                             prediction=result,
                             probability=f"{probability*100:.2f}%",
                             nom=data['nom'],
                             postnom=data['postnom'],
                             age=data['age'],
                             bmi=data['bmi'],
                             glucose=data['glucose'],
                             blood_pressure=data['blood_pressure'],
                             pregnancies=data['pregnancies'],
                             insulin=data['insulin'],
                             dpf=data['dpf'],
                             date=datetime.now().strftime('%d/%m/%Y %H:%M'),
                             color=color,
                             advice=advice,
                             result_class=result_class,
                             show_result=True,
                             stats=stats)
    except Exception as e:
        return render_template('form.html', 
                             error=f"Erreur : {str(e)}",
                             show_result=False,
                             stats=get_statistics())

@app.route('/history')
def history():
    page = request.args.get('page', 1, type=int)
    per_page = 5
    predictions, total = get_history(page, per_page)
    stats = get_statistics()
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    return render_template('history.html', 
                         predictions=predictions,
                         stats=stats,
                         page=page,
                         total_pages=total_pages,
                         total=total,
                         per_page=per_page)

@app.route('/rapport/<int:patient_id>')
def rapport(patient_id):
    patient = get_patient_by_id(patient_id)
    if patient is None:
        return "Patient non trouvé", 404
    data = dict(patient)
    if data['prediction'] == 0:
        result = "Non-diabétique "
        color = "green"
        advice = "Le patient est en bonne santé ! Continuez à maintenir un mode de vie sain."
        result_class = "success"
    else:
        result = "Diabétique "
        color = "red"
        advice = "Le patient présente un risque de diabète. Consultez un médecin."
        result_class = "danger"
    return render_template('rapport.html',
                         nom=data['nom'],
                         postnom=data['postnom'],
                         age=data['age'],
                         bmi=data['bmi'],
                         glucose=data['glucose'],
                         blood_pressure=data['blood_pressure'],
                         pregnancies=data['pregnancies'],
                         insulin=data['insulin'],
                         dpf=data['dpf'],
                         date=data['prediction_date'],
                         prediction=result,
                         probability=f"{data['probability']*100:.2f}%",
                         color=color,
                         advice=advice,
                         result_class=result_class)

@app.route('/stats')
def stats():
    stats = get_statistics()
    return render_template('stats.html', stats=stats)

@app.route('/patients')
def patients():
    patients_list = get_all_patients()
    return render_template('patients.html', patients=patients_list)

#  ROUTE RAPPORT GLOBAL


@app.route('/rapport_global')
def rapport_global():
    """Rapport global avec toutes les statistiques."""
    stats = get_statistics()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT * FROM v_predictions_complete 
    ORDER BY prediction_date DESC
    ''')
    predictions = cursor.fetchall()
    conn.close()
    date = datetime.now().strftime('%d/%m/%Y %H:%M')
    return render_template('rapport_global.html', 
                         stats=stats,
                         predictions=predictions,
                         total=len(predictions),
                         date=date)

# ROUTES POUR LES ACTIONS


@app.route('/delete/<int:prediction_id>')
def delete_prediction_route(prediction_id):
    try:
        if delete_prediction(prediction_id):
            return redirect(url_for('history'))
        return "Erreur : Prédiction non trouvée", 404
    except Exception as e:
        return f"Erreur : {str(e)}", 500

@app.route('/edit/<int:prediction_id>', methods=['GET', 'POST'])
def edit_prediction(prediction_id):
    if request.method == 'POST':
        try:
            data = {
                'nom': request.form['nom'],
                'postnom': request.form['postnom'],
                'pregnancies': float(request.form['pregnancies']),
                'glucose': float(request.form['glucose']),
                'blood_pressure': float(request.form['blood_pressure']),
                'skin_thickness': float(request.form['skin_thickness']),
                'insulin': float(request.form['insulin']),
                'bmi': float(request.form['bmi']),
                'dpf': float(request.form['dpf']),
                'age': float(request.form['age'])
            }
            if update_patient(prediction_id, data):
                return redirect(url_for('history'))
            return "Erreur lors de la modification", 404
        except Exception as e:
            return f"Erreur : {str(e)}", 500
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        SELECT p.*, pr.id as prediction_id 
        FROM patients p
        JOIN predictions pr ON p.id = pr.patient_id
        WHERE pr.id = ?
        ''', (prediction_id,))
        patient = cursor.fetchone()
        conn.close()
        if patient:
            return render_template('edit.html', patient=dict(patient))
        return "Patient non trouvé", 404
    except Exception as e:
        return f"Erreur : {str(e)}", 500

# API ENDPOINTS


@app.route('/api/predict', methods=['POST'])
def api_predict():
    try:
        data = request.get_json()
        input_data = np.array([[
            data['pregnancies'], data['glucose'], data['blood_pressure'],
            data['skin_thickness'], data['insulin'], data['bmi'],
            data['diabetes_pedigree_function'], data['age']
        ]])
        input_scaled = scaler.transform(input_data)
        prediction = int(model.predict(input_scaled)[0])
        probability = float(model.predict_proba(input_scaled)[0][1])
        patient_id = save_patient(data)
        save_prediction(patient_id, prediction, probability)
        return jsonify({
            'success': True,
            'prediction': prediction,
            'probability': probability,
            'result': 'Diabétique' if prediction == 1 else 'Non-diabétique'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/stats')
def api_stats():
    stats = get_statistics()
    return jsonify(stats)

#  LANCEMENT DE L'APPLICATION


if __name__ == '__main__':

    print(" APPLICATION LANCÉE !")
    print("--"*20)
    
    print(" Accéder à l'application : http://127.0.0.1:5000")
    print(" Formulaire : http://127.0.0.1:5000/form")
    print(" Historique : http://127.0.0.1:5000/history")
    print(" Statistiques : http://127.0.0.1:5000/stats")
    print(" Patients : http://127.0.0.1:5000/patients")
    print(" Rapport Global : http://127.0.0.1:5000/rapport_global")

    app.run(debug=True, host='0.0.0.0', port=5000)