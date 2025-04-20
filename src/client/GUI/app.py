# web/app.py
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import threading
import os
import io
import contextlib
import time

# Import client module without modifying it
tf_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
import sys
sys.path.insert(0, tf_path)
from client import client

SERVER_IP = os.environ.get("SERVER_IP", "localhost")
SERVER_PORT = int(os.environ.get("SERVER_PORT", 4444))
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "CAMBIA_ESTA_CLAVE")

# Helper to call client functions and capture their stdout
def capture(func, *args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        func(*args)
    return buf.getvalue().splitlines()

# API endpoint: get list of users
@app.route('/api/users')
def api_users():
    if 'username' not in session:
        return jsonify([]), 401
    client._server = SERVER_IP
    client._port = SERVER_PORT
    lines = capture(client.listusers)
    users = []
    for line in lines:
        line = line.strip()
        if line.startswith('USER'):
            parts = line.split()
            users.append({'name': parts[1]})
    return jsonify(users)

# API endpoint: get content for a user
@app.route('/api/content/<target>')
def api_content(target):
    if 'username' not in session:
        return jsonify([]), 401
    client._server = SERVER_IP
    client._port = SERVER_PORT
    lines = capture(client.listcontent, target)
    files = []
    for line in lines:
        print(line)
        line = line.strip()
        if line.startswith('FILE'):
            parts = line.split()
            files.append({'name': parts[1]})
    return jsonify(files)

# Login/Logout
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('username','').strip()
        if user:
            try:
                session['username'] = user
                client._server = SERVER_IP
                client._port = SERVER_PORT
                client.register(user)
                client.connect(user)
            except Exception as e:
                session.pop('username', None)
                return render_template('login.html', error=str(e))
            return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    user = session.pop('username', None)
    if user:
        client._server = SERVER_IP
        client._port = SERVER_PORT
        client.disconnect(user)
        client.unregister(user)
    return redirect(url_for('login'))

# Dashboard page
@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', username=session['username'])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
