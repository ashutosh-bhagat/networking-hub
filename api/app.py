import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.consumer import oauth_authorized
from flask_dance.consumer.storage.sqla import SQLAlchemyStorage
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import timedelta
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Security configuration
app.secret_key = os.environ.get('SECRET_KEY', 'supersecretkey')  # Use environment variable in production
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['SESSION_COOKIE_SECURE'] = True  # Only send cookie over HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access to session cookie

# Database setup
engine = create_engine('sqlite:///database.db')
Session = sessionmaker(bind=engine)
db_session = Session()

# Google OAuth Blueprint
google_bp = make_google_blueprint(
    client_id=os.environ.get('GOOGLE_CLIENT_ID', '8855868303-rmfau2vjpvo8ono3lm3048plru5qcb0e.apps.googleusercontent.com'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET', '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'),
    scope=["profile", "email"],
    redirect_url="/login/google/authorized"
)
app.register_blueprint(google_bp, url_prefix="/login")

UPLOAD_FOLDER = os.path.join('static', 'profile_pics')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@oauth_authorized.connect_via(google_bp)
def google_logged_in(blueprint, token):
    if not token:
        flash("Failed to log in with Google.", category="error")
        return False

    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        flash("Failed to fetch user info from Google.", category="error")
        return False

    google_info = resp.json()
    google_user_id = google_info["id"]
    email = google_info["email"]
    name = google_info["name"]

    # Get or create user
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = c.fetchone()

    if not user:
        c.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", 
                 (name, email, 'google_oauth'))
        conn.commit()
        user_id = c.lastrowid
    else:
        user_id = user[0]

    conn.close()

    # Store user info in session
    session['user'] = user_id
    session['name'] = name
    session['email'] = email
    session.permanent = True

    flash("Successfully signed in with Google.", category="success")
    return False  # Don't redirect, let the route handle it

@app.route('/google_login')
def google_login():
    if not google.authorized:
        return redirect(url_for("google.login"))
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form.get('confirm_password')
        github = ''
        linkedin = ''
        twitter = ''
        portfolio = ''
        profile_pic = None
        # Backend validation
        if not name or not email or not password or not confirm_password:
            flash('Name, Email, and Password fields are required.', category='error')
            return redirect(url_for('signup'))
        if password != confirm_password:
            flash('Passwords do not match.', category='error')
            return redirect(url_for('signup'))
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        # Check if email already exists
        c.execute('SELECT * FROM users WHERE email = ?', (email,))
        if c.fetchone():
            flash("Email already registered. Please login instead.", category="error")
            return redirect(url_for('login'))
        c.execute('''
            INSERT INTO users (name, email, password, github, linkedin, twitter, portfolio, profile_pic)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, email, password, github, linkedin, twitter, portfolio, profile_pic))
        user_id = c.lastrowid
        conn.commit()
        conn.close()
        # Log in the user and redirect to complete_profile
        session['user'] = user_id
        session['name'] = name
        session['email'] = email
        session.permanent = True
        flash("Registration successful! Please complete your profile.", category="success")
        return redirect(url_for('complete_profile'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if not email or not password:
            flash('Email and password are required.', category='error')
            return redirect(url_for('login'))
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE email = ? AND password = ?', (email, password))
        user = c.fetchone()
        conn.close()
        if user:
            session['user'] = user[0]
            session['name'] = user[1]
            session['email'] = user[2]
            session.permanent = True
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password.", category="error")
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        flash("Please login to access the dashboard.", category="error")
        return redirect(url_for('login'))
    user_id = session['user']
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = c.fetchone()
    conn.close()
    activities = []  # Placeholder for user activities
    return render_template('dashboard.html', user=user, activities=activities)

@app.route('/myblock')
def myblock():
    if 'user' not in session:
        flash("Please login to access your profile.", category="error")
        return redirect(url_for('login'))

    user_id = session['user']
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = c.fetchone()
    conn.close()

    return render_template('myblock.html', user=user)

@app.route('/edit', methods=['GET', 'POST'])
def edit():
    if 'user' not in session:
        flash("Please login to edit your profile.", category="error")
        return redirect(url_for('login'))
    user_id = session['user']
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    if request.method == 'POST':
        github = request.form['github']
        linkedin = request.form['linkedin']
        twitter = request.form['twitter']
        portfolio = request.form['portfolio']
        profile_pic = None
        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                profile_pic = f'profile_pics/{filename}'
        if profile_pic:
            c.execute('''
                UPDATE users SET github = ?, linkedin = ?, twitter = ?, portfolio = ?, profile_pic = ?
                WHERE id = ?
            ''', (github, linkedin, twitter, portfolio, profile_pic, user_id))
        else:
            c.execute('''
                UPDATE users SET github = ?, linkedin = ?, twitter = ?, portfolio = ?
                WHERE id = ?
            ''', (github, linkedin, twitter, portfolio, user_id))
        conn.commit()
        flash("Profile updated successfully!", category="success")
        return redirect(url_for('myblock'))
    c.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = c.fetchone()
    conn.close()
    return render_template('edit.html', user=user)

@app.route('/users')
def users():
    if 'user' not in session:
        flash("Please login to view users.", category="error")
        return redirect(url_for('login'))
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM users')
    all_users = c.fetchall()
    conn.close()
    return render_template('users.html', users=all_users)

@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'user' not in session:
        flash('You must be logged in to delete your account.', category='error')
        return redirect(url_for('login'))
    user_id = session['user']
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    session.clear()
    flash('Your account has been deleted.', category='success')
    return redirect(url_for('home'))

@app.route('/complete_profile', methods=['GET', 'POST'])
def complete_profile():
    if 'user' not in session:
        flash('Please login to complete your profile.', category='error')
        return redirect(url_for('login'))
    user_id = session['user']
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if request.method == 'POST':
        github = request.form['github']
        linkedin = request.form['linkedin']
        twitter = request.form['twitter']
        portfolio = request.form['portfolio']
        profile_pic = None
        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                profile_pic = f'profile_pics/{filename}'
        if profile_pic:
            c.execute('''
                UPDATE users SET github = ?, linkedin = ?, twitter = ?, portfolio = ?, profile_pic = ?
                WHERE id = ?
            ''', (github, linkedin, twitter, portfolio, profile_pic, user_id))
        else:
            c.execute('''
                UPDATE users SET github = ?, linkedin = ?, twitter = ?, portfolio = ?
                WHERE id = ?
            ''', (github, linkedin, twitter, portfolio, user_id))
        conn.commit()
        flash('Profile completed successfully!', category='success')
        return redirect(url_for('dashboard'))
    c.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = c.fetchone()
    conn.close()
    return render_template('complete_profile.html', user=user)

# if __name__ == '__main__':
#     app.run(debug=True)