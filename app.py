import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'supersecretkey'

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        github = request.form['github']
        linkedin = request.form['linkedin']
        twitter = request.form['twitter']
        portfolio = request.form['portfolio']

        # Insert into database
        import sqlite3
        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        c.execute('''
            INSERT INTO users (name, email, password, github, linkedin, twitter, portfolio)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, email, password, github, linkedin, twitter, portfolio))

        conn.commit()
        conn.close()

        return redirect(url_for('home'))

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        import sqlite3
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE email = ? AND password = ?', (email, password))
        user = c.fetchone()
        conn.close()

        if user:
            session['user'] = user[0]  # Store user ID in session
            return redirect(url_for('dashboard'))
        else:
            return "Login failed. Please try again."

    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/myblock')
def myblock():
    if 'user' not in session:
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
        return redirect(url_for('login'))

    user_id = session['user']
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    if request.method == 'POST':
        github = request.form['github']
        linkedin = request.form['linkedin']
        twitter = request.form['twitter']
        portfolio = request.form['portfolio']

        c.execute('''
            UPDATE users SET github = ?, linkedin = ?, twitter = ?, portfolio = ?
            WHERE id = ?
        ''', (github, linkedin, twitter, portfolio, user_id))
        conn.commit()
        conn.close()
        return redirect(url_for('myblock'))

    c.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = c.fetchone()
    conn.close()
    return render_template('edit.html', user=user)

@app.route('/users')
def users():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users')
    all_users = c.fetchall()
    conn.close()
    return render_template('users.html', users=all_users)


if __name__ == '__main__':
    app.run(debug=True)