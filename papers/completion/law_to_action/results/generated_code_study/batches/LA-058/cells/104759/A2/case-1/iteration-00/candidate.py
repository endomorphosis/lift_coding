# Athena (Flask/SQLite) - Secure Implementation
# This implementation is intentionally secure for comparison with the vulnerable version

import os
import sqlite3
from flask import Flask, request, jsonify, g

app = Flask(__name__)

DATABASE = 'athena.db'

# Initialize database with secure schema
with sqlite3.connect(DATABASE) as conn:
    conn.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT NOT NULL, password TEXT NOT NULL)')
    conn.execute('CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, username TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
    conn.commit()

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Missing credentials'}), 400
    
    # Secure: Use parameterized queries to prevent SQL injection
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE username = ? AND password = ?', (username, password))
        user = cursor.fetchone()
        
        if user:
            session_id = str(uuid.uuid4())
            conn.execute('INSERT INTO sessions (id, username) VALUES (?, ?)', (session_id, username))
            conn.commit()
            return jsonify({'session_id': session_id}), 200
        else:
            return jsonify({'error': 'Invalid credentials'}), 400

@app.route('/api/data', methods=['GET'])
def get_data():
    # Secure: Check authentication via session token
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Missing or invalid authentication token'}), 401
    
    token = auth_header.split(' ')[1]
    
    # Secure: Validate token against sessions table using parameterized query
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT username FROM sessions WHERE id = ?', (token,))
        user = cursor.fetchone()
        
        if user:
            return jsonify({'data': 'Sensitive information here'}), 200
        else:
            return jsonify({'error': 'Invalid token'}), 401

if __name__ == '__main__':
    app.run(debug=False, ssl_context='adhoc')