from flask import Flask, render_template, request, send_from_directory, redirect, url_for, session, flash
import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

from lang_zh import translations as zh
from lang_en import translations as en

app = Flask(__name__)
app.secret_key = 'secret_key_for_session'
UPLOAD_FOLDER = 'static/files'
DB = 'database.db'

def get_translation():
    lang = session.get('lang', 'zh')
    return zh if lang == 'zh' else en

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            category TEXT,
            filename TEXT,
            thumbnail TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()

    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        hashed_pw = generate_password_hash('123456')
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", ('admin', hashed_pw))
        conn.commit()
    conn.close()

@app.route('/setlang/<lang>')
def setlang(lang):
    session['lang'] = lang if lang in ['zh', 'en'] else 'zh'
    return redirect(request.referrer or url_for('index'))

@app.route('/')
def index():
    t = get_translation()
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    keyword = request.args.get('q', '')
    if keyword:
        c.execute("SELECT * FROM materials WHERE title LIKE ?", ('%' + keyword + '%',))
    else:
        c.execute("SELECT * FROM materials")
    materials = c.fetchall()
    conn.close()
    return render_template('index.html', materials=materials, keyword=keyword, user=session.get('user'), t=t)

@app.route('/detail/<int:material_id>')
def detail(material_id):
    t = get_translation()
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM materials WHERE id=?", (material_id,))
    material = c.fetchone()
    conn.close()
    return render_template('detail.html', material=material, t=t)

@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user' not in session or session['user'] != 'admin':
        return redirect(url_for('login'))
    t = get_translation()
    if request.method == 'POST':
        title = request.form['title']
        category = request.form['category']
        file = request.files['file']
        thumb = request.files['thumbnail']
        if file and thumb:
            filepath = os.path.join(UPLOAD_FOLDER, file.filename)
            thumbpath = os.path.join('static/thumbnails', thumb.filename)
            file.save(filepath)
            thumb.save(thumbpath)
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            c.execute("INSERT INTO materials (title, category, filename, thumbnail) VALUES (?, ?, ?, ?)",
                      (title, category, file.filename, thumb.filename))
            conn.commit()
            conn.close()
            return redirect(url_for('index'))
    return render_template('upload.html', t=t)

@app.route('/login', methods=['GET', 'POST'])
def login():
    t = get_translation()
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT password FROM users WHERE username=?", (username,))
        result = c.fetchone()
        conn.close()
        if result and check_password_hash(result[0], password):
            session['user'] = username
            return redirect(url_for('index'))
        else:
            flash(t["invalid"])
    return render_template('login.html', t=t)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    init_db()
    app.run(debug=True)

@app.route('/admin')
def admin():
    if 'username' not in session or session['username'] != 'admin':
        return redirect(url_for('login'))
    files = os.listdir(UPLOAD_FOLDER)
    users = list(users_db.keys())
    return render_template('admin.html', files=files, users=users)

@app.route('/delete/<filename>')
def delete_file(filename):
    if 'username' not in session or session['username'] != 'admin':
        return redirect(url_for('login'))
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    return redirect(url_for('admin'))