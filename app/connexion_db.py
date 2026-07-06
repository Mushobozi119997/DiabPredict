
# CONNEXION À LA BASE DE DONNÉES


import sqlite3
import os

# Chemin de la base de données
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'predictions.db')

def get_connection():
    """
    Établit une connexion à la base de données SQLite.
    Retourne l'objet de connexion.
    """
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f" Base de données non trouvée : {DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def test_connection():
    """Teste la connexion à la base de données."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        table_names = [t['name'] for t in tables]
        
        print("="*60)
        print(" TEST DE CONNEXION À LA BASE DE DONNÉES")
        print("="*60)
        print(f" Connexion réussie !")
        print(f" Base : {DB_PATH}")
        print(f" Tables : {', '.join(table_names)}")
        conn.close()
        return True
    except Exception as e:
        print(f" Erreur : {e}")
        return False

if __name__ == '__main__':
    test_connection() 
