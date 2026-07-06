# ============================================================
# OPÉRATIONS SUR LA BASE DE DONNÉES
#

from connexion_db import get_connection

def save_patient(data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO patients (pregnancies, glucose, blood_pressure, skin_thickness,
                         insulin, bmi, dpf, age)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (data['pregnancies'], data['glucose'], data['blood_pressure'],
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
    pred_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return pred_id

def get_history(limit=100):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT * FROM v_predictions_complete 
    ORDER BY prediction_date DESC 
    LIMIT ?
    ''', (limit,))
    history = cursor.fetchall()
    conn.close()
    return history

def get_statistics():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM v_statistics')
    stats = cursor.fetchone()
    conn.close()
    return dict(stats) if stats else None

def get_all_patients(limit=100):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT * FROM patients ORDER BY created_at DESC LIMIT ?
    ''', (limit,))
    patients = cursor.fetchall()
    conn.close()
    return patients

def get_model_performance():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT model_used, COUNT(*) as total,
           ROUND(AVG(probability) * 100, 2) as avg_probability
    FROM predictions GROUP BY model_used
    ''')
    return cursor.fetchall()

if __name__ == '__main__':
    from connexion_db import test_connection
    test_connection()
    stats = get_statistics()
    if stats:
        print(f" Prédictions : {stats['total_predictions']}")
        print(f" Diabétiques : {stats['diabetics']}")