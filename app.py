from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = '+8*09H{5Rb*m'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

UPLOAD_FOLDER = 'static/profile_pics'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_db():
    with sqlite3.connect('connectmed.db') as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                email TEXT NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS user_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                birth_date TEXT NOT NULL,
                age INTEGER NOT NULL,
                gender TEXT NOT NULL,
                profile_picture TEXT,
                terms_accepted INTEGER NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        conn.commit()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        hashed_password = generate_password_hash(password)  # <-- Aquí se hace el hash
        
        with sqlite3.connect('connectmed.db') as conn:
            c = conn.cursor()
            c.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                      (username, email, hashed_password))
            user_id = c.lastrowid
            conn.commit()
        session['user_id'] = user_id
        return redirect(url_for('registro_info'))
    return render_template('index.html')


@app.route('/registro_info', methods=['GET', 'POST'])
def registro_info():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('index'))

    if request.method == 'POST':
        first_name = request.form.get('nombre', '').strip()
        last_name = request.form.get('apellido', '').strip()
        birth_date = request.form.get('fecha_nacimiento', '').strip()
        gender = request.form.get('genero', '').strip()
        terms = 'terminos' in request.form

        if not (first_name and last_name and birth_date and gender and terms):
            return render_template('registro_info.html', error="Por favor, complete todos los campos y acepte los términos.")

        try:
            birth = datetime.strptime(birth_date, '%Y-%m-%d')
            today = datetime.today()
            age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
        except ValueError:
            return render_template('registro_info.html', error="Formato de fecha inválido.")

        with sqlite3.connect('connectmed.db') as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO user_profiles 
                (user_id, first_name, last_name, birth_date, age, gender, terms_accepted)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, first_name, last_name, birth_date, age, gender, int(terms)))
            conn.commit()

        return redirect(url_for('dashboard'))

    # 👇 Agregado para mostrar mensaje si viene desde el login
    mensaje_incompleto = request.args.get('mensaje_incompleto')
    return render_template('registro_info.html', mensaje_incompleto=mensaje_incompleto)


@app.route('/dashboard')
def dashboard():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('index'))

    with sqlite3.connect('connectmed.db') as conn:
        c = conn.cursor()
        c.execute("SELECT username, email FROM users WHERE id = ?", (user_id,))
        user_data = c.fetchone()
        c.execute("SELECT first_name, last_name, age, gender, profile_picture FROM user_profiles WHERE user_id = ?", (user_id,))
        profile_data = c.fetchone()

    first_name, last_name, age, gender, profile_picture = profile_data

    return render_template('dashboard.html',
                           username=user_data[0],
                           email=user_data[1],
                           first_name=first_name,
                           last_name=last_name,
                           age=age,
                           gender=gender,
                           profile_picture=profile_picture)

@app.route('/editar_info', methods=['GET', 'POST'])
def editar_info():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    user_id = session['user_id']
    conn = sqlite3.connect('connectmed.db')
    c = conn.cursor()

    if request.method == 'POST':
        first_name = request.form.get('nombre', '').strip()
        last_name = request.form.get('apellido', '').strip()
        birth_date = request.form.get('fecha_nacimiento', '').strip()
        gender = request.form.get('genero', '').strip()

        if not (first_name and last_name and birth_date and gender):
            conn.close()
            return render_template('editar_info.html', perfil=None, error="Complete todos los campos")

        try:
            birth = datetime.strptime(birth_date, '%Y-%m-%d')
            today = datetime.today()
            age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
        except ValueError:
            conn.close()
            return render_template('editar_info.html', perfil=None, error="Formato de fecha inválido")

        file = request.files.get('foto_perfil')

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            try:
                file.save(filepath)
            except Exception as e:
                conn.close()
                return render_template('editar_info.html', perfil=None, error=f"Error guardando la imagen: {str(e)}")

            c.execute('''
                UPDATE user_profiles
                SET first_name = ?, last_name = ?, birth_date = ?, age = ?, gender = ?, profile_picture = ?
                WHERE user_id = ?
            ''', (first_name, last_name, birth_date, age, gender, filename, user_id))
        else:
            c.execute('''
                UPDATE user_profiles
                SET first_name = ?, last_name = ?, birth_date = ?, age = ?, gender = ?
                WHERE user_id = ?
            ''', (first_name, last_name, birth_date, age, gender, user_id))

        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))

    # GET
    c.execute('SELECT first_name, last_name, birth_date, gender, profile_picture FROM user_profiles WHERE user_id = ?', (user_id,))
    perfil = c.fetchone()
    conn.close()

    if not perfil:
        perfil = (None, None, None, None, None)

    return render_template('editar_info.html', perfil=perfil)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        print(f"Intento login -> usuario: '{username}', password: '{password}'")

        with sqlite3.connect('connectmed.db') as conn:
            c = conn.cursor()
            c.execute("SELECT id, password FROM users WHERE username = ?", (username,))
            user = c.fetchone()

        if user:
            print("Usuario encontrado:", user[0])
            print("Hash guardado:", user[1])
            from werkzeug.security import check_password_hash
            if check_password_hash(user[1], password):
                print("Contraseña correcta")
                session['user_id'] = user[0]
            with sqlite3.connect('connectmed.db') as conn:
                c = conn.cursor()
                c.execute("SELECT id FROM user_profiles WHERE user_id = ?", (user[0],))
                profile = c.fetchone()
            if profile:
                return redirect(url_for('dashboard'))
            else:
                return redirect(url_for('registro_info', mensaje_incompleto=1))

        return render_template('login.html', error="Usuario o contraseña incorrectos.")

    return render_template('login.html')

@app.errorhandler(404)
def page_not_found(e):
    print("ConnectMed - NO ENCONTRADO xd")
    return render_template('404.html'), 404

@app.errorhandler(TypeError)
def handle_type_error(e):
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
