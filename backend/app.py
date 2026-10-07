import mimetypes
import os
import sqlite3
from datetime import datetime
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for, flash, session, g
)
from werkzeug.security import generate_password_hash, check_password_hash

mimetypes.add_type('text/css', '.css')
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_ROOT = os.path.join(PROJECT_ROOT, 'frontend')
app = Flask(
    __name__,
    template_folder=os.path.join(FRONTEND_ROOT, 'templates'),
    static_folder=os.path.join(FRONTEND_ROOT, 'static'),
    static_url_path='/static',
)
app.secret_key = os.environ.get('SECRET_KEY', 'skillconnect_secret_key_change_in_production')
DATABASE = os.path.join(PROJECT_ROOT, 'skillconnect.db')

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    cursor = db.cursor()
    
    # Users Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('customer', 'worker', 'admin')),
        city TEXT,
        area TEXT,
        address TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    ''')

    # Workers Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS workers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        primary_skill TEXT NOT NULL,
        additional_skills TEXT,
        experience_years INTEGER DEFAULT 0,
        about TEXT,
        price_per_hour REAL DEFAULT 0.0,
        working_hours TEXT,
        verification_status TEXT DEFAULT 'Pending' CHECK(verification_status IN ('Pending', 'Verified', 'Rejected')),
        rating REAL DEFAULT 0.0,
        completed_jobs INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );
    ''')

    # Categories Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT
    );
    ''')

    # Bookings Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        worker_id INTEGER NOT NULL,
        service_name TEXT NOT NULL,
        booking_date TEXT NOT NULL,
        booking_time TEXT NOT NULL,
        address TEXT NOT NULL,
        work_description TEXT,
        estimated_budget REAL NOT NULL,
        commission REAL NOT NULL,
        worker_amount REAL NOT NULL,
        status TEXT DEFAULT 'PENDING' CHECK(status IN ('PENDING', 'ACCEPTED', 'REJECTED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES users (id),
        FOREIGN KEY (worker_id) REFERENCES workers (id)
    );
    ''')

    # Reviews Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id INTEGER UNIQUE NOT NULL,
        customer_id INTEGER NOT NULL,
        worker_id INTEGER NOT NULL,
        rating INTEGER CHECK(rating >= 1 AND rating <= 5),
        comment TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (booking_id) REFERENCES bookings (id),
        FOREIGN KEY (customer_id) REFERENCES users (id),
        FOREIGN KEY (worker_id) REFERENCES workers (id)
    );
    ''')

    # Notifications Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        is_read INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    );
    ''')

    admin = cursor.execute(
        'SELECT id FROM users WHERE email = ?', ('admin@skillconnect.com',)
    ).fetchone()
    if admin is None:
        cursor.execute('''
            INSERT INTO users (name, email, phone, password_hash, role, city, area)
            VALUES (?, ?, ?, ?, 'admin', ?, ?)
        ''', (
            'Platform Admin',
            'admin@skillconnect.com',
            '9876543210',
            generate_password_hash('admin123'),
            'Jaipur',
            'Central',
        ))

    db.commit()

# Initialize DB on start
with app.app_context():
    init_db()

# Decorators for auth
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in first.', 'warning')
                return redirect(url_for('login'))
            if session.get('role') != role and session.get('role') != 'admin':
                flash('Unauthorized access.', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def add_notification(user_id, title, message):
    db = get_db()
    db.execute('INSERT INTO notifications (user_id, title, message) VALUES (?, ?, ?)', (user_id, title, message))
    db.commit()

@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
        g.notifications = []
    else:
        db = get_db()
        g.user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        g.notifications = db.execute(
            'SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 5',
            (user_id,)
        ).fetchall()

# Helper function to recalculate ratings
def update_worker_stats(worker_id):
    db = get_db()
    stats = db.execute('''
        SELECT AVG(rating) as avg_rating, COUNT(r.id) as review_cnt 
        FROM reviews r 
        WHERE worker_id = ?
    ''', (worker_id,)).fetchone()
    
    completed_jobs = db.execute('''
        SELECT COUNT(*) as completed_cnt 
        FROM bookings 
        WHERE worker_id = ? AND status = 'COMPLETED'
    ''', (worker_id,)).fetchone()['completed_cnt']

    avg_rating = round(stats['avg_rating'], 1) if stats['avg_rating'] else 0.0

    db.execute('''
        UPDATE workers 
        SET rating = ?, completed_jobs = ? 
        WHERE id = ?
    ''', (avg_rating, completed_jobs, worker_id))
    db.commit()

# Routes
@app.route('/')
def index():
    db = get_db()
    categories = db.execute('SELECT * FROM categories LIMIT 6').fetchall()

    # Platform counts
    stats = {
        'workers': db.execute('SELECT COUNT(*) FROM workers').fetchone()[0],
        'jobs': db.execute("SELECT COUNT(*) FROM bookings WHERE status='COMPLETED'").fetchone()[0],
        'earnings': db.execute("SELECT COALESCE(SUM(worker_amount), 0) FROM bookings WHERE status='COMPLETED'").fetchone()[0]
    }
    return render_template('index.html', categories=categories, stats=stats)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/services')
def services():
    db = get_db()
    categories = db.execute('SELECT * FROM categories').fetchall()
    return render_template('services.html', categories=categories)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        city = request.form['city']
        area = request.form['area']

        db = get_db()
        existing = db.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
        if existing:
            flash('Email address is already registered.', 'danger')
            return redirect(url_for('register'))

        hashed_pw = generate_password_hash(password)
        db.execute('''
            INSERT INTO users (name, email, phone, password_hash, role, city, area)
            VALUES (?, ?, ?, ?, 'customer', ?, ?)
        ''', (name, email, phone, hashed_pw, city, area))
        db.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/register-worker', methods=['GET', 'POST'])
def register_worker():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        city = request.form['city']
        area = request.form['area']
        address = request.form['address']
        primary_skill = request.form['primary_skill']
        additional_skills = request.form.get('additional_skills', '')
        experience_years = request.form.get('experience_years', 0)
        about = request.form.get('about', '')
        price_per_hour = request.form.get('price_per_hour', 0.0)
        working_hours = request.form.get('working_hours', '9:00 AM - 6:00 PM')

        db = get_db()
        existing = db.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
        if existing:
            flash('Email address is already registered.', 'danger')
            return redirect(url_for('register_worker'))

        hashed_pw = generate_password_hash(password)
        cursor = db.cursor()
        cursor.execute('''
            INSERT INTO users (name, email, phone, password_hash, role, city, area, address)
            VALUES (?, ?, ?, ?, 'worker', ?, ?, ?)
        ''', (name, email, phone, hashed_pw, city, area, address))
        user_id = cursor.lastrowid

        cursor.execute('''
            INSERT INTO workers (user_id, primary_skill, additional_skills, experience_years, about, price_per_hour, working_hours)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, primary_skill, additional_skills, experience_years, about, price_per_hour, working_hours))
        db.commit()

        flash('Worker account created successfully! Pending admin verification.', 'info')
        return redirect(url_for('login'))
    return render_template('register_worker.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        db = get_db()
        user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['name'] = user['name']
            
            if user['role'] == 'worker':
                worker = db.execute('SELECT id FROM workers WHERE user_id = ?', (user['id'],)).fetchone()
                if worker:
                    session['worker_id'] = worker['id']

            flash(f'Welcome back, {user["name"]}!', 'success')
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user['role'] == 'worker':
                return redirect(url_for('worker_dashboard'))
            else:
                return redirect(url_for('customer_dashboard'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/workers')
def workers():
    skill_filter = request.args.get('skill', '')
    city_filter = request.args.get('city', '')
    search_query = request.args.get('q', '')

    db = get_db()
    query = '''
        SELECT w.*, u.name, u.city, u.area, u.phone 
        FROM workers w 
        JOIN users u ON w.user_id = u.id 
        WHERE 1=1
    '''
    params = []

    if skill_filter:
        query += ' AND (w.primary_skill LIKE ? OR w.additional_skills LIKE ?)'
        params.extend([f'%{skill_filter}%', f'%{skill_filter}%'])

    if city_filter:
        query += ' AND u.city LIKE ?'
        params.append(f'%{city_filter}%')

    if search_query:
        query += ' AND (u.name LIKE ? OR w.primary_skill LIKE ? OR u.city LIKE ? OR u.area LIKE ?)'
        params.extend([f'%{search_query}%', f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'])

    query += ' ORDER BY w.rating DESC'
    workers_list = db.execute(query, params).fetchall()

    return render_template('workers.html', workers=workers_list, skill_filter=skill_filter, city_filter=city_filter, search_query=search_query)

@app.route('/worker/<int:worker_id>')
def worker_profile(worker_id):
    db = get_db()
    worker = db.execute('''
        SELECT w.*, u.name, u.email, u.phone, u.city, u.area, u.address 
        FROM workers w 
        JOIN users u ON w.user_id = u.id 
        WHERE w.id = ?
    ''', (worker_id,)).fetchone()

    if not worker:
        flash('Worker not found.', 'danger')
        return redirect(url_for('workers'))

    reviews = db.execute('''
        SELECT r.*, u.name as customer_name 
        FROM reviews r 
        JOIN users u ON r.customer_id = u.id 
        WHERE r.worker_id = ? 
        ORDER BY r.created_at DESC
    ''', (worker_id,)).fetchall()

    return render_template('worker_profile.html', worker=worker, reviews=reviews)

@app.route('/book/<int:worker_id>', methods=['GET', 'POST'])
@login_required
def book_worker(worker_id):
    db = get_db()
    worker = db.execute('''
        SELECT w.*, u.name as worker_name, u.city, u.area 
        FROM workers w 
        JOIN users u ON w.user_id = u.id 
        WHERE w.id = ?
    ''', (worker_id,)).fetchone()

    if not worker:
        flash('Worker not found.', 'danger')
        return redirect(url_for('workers'))

    if request.method == 'POST':
        service_name = request.form['service_name']
        booking_date = request.form['booking_date']
        booking_time = request.form['booking_time']
        address = request.form['address']
        work_description = request.form['work_description']
        estimated_budget = float(request.form['estimated_budget'])

        commission = round(estimated_budget * 0.10, 2)
        worker_amount = round(estimated_budget - commission, 2)

        cursor = db.cursor()
        cursor.execute('''
            INSERT INTO bookings (customer_id, worker_id, service_name, booking_date, booking_time, address, work_description, estimated_budget, commission, worker_amount, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')
        ''', (session['user_id'], worker_id, service_name, booking_date, booking_time, address, work_description, estimated_budget, commission, worker_amount))
        
        booking_id = cursor.lastrowid
        db.commit()

        # Notify Worker
        add_notification(worker['user_id'], "New Booking Request", f"You have received a new booking request for {service_name}.")

        flash('Booking request submitted successfully!', 'success')
        return redirect(url_for('booking_detail', booking_id=booking_id))

    return render_template('book.html', worker=worker)

@app.route('/booking/<int:booking_id>')
@login_required
def booking_detail(booking_id):
    db = get_db()
    booking = db.execute('''
        SELECT b.*, 
               u_cust.name as customer_name, u_cust.phone as customer_phone, u_cust.email as customer_email,
               u_work.name as worker_name, u_work.phone as worker_phone, w.id as worker_id
        FROM bookings b
        JOIN users u_cust ON b.customer_id = u_cust.id
        JOIN workers w ON b.worker_id = w.id
        JOIN users u_work ON w.user_id = u_work.id
        WHERE b.id = ?
    ''', (booking_id,)).fetchone()

    if not booking:
        flash('Booking not found.', 'danger')
        return redirect(url_for('customer_dashboard'))

    # Access check
    if session['role'] == 'customer' and booking['customer_id'] != session['user_id']:
        flash('Unauthorized view.', 'danger')
        return redirect(url_for('customer_dashboard'))

    review = db.execute('SELECT * FROM reviews WHERE booking_id = ?', (booking_id,)).fetchone()

    return render_template('booking_detail.html', booking=booking, review=review)

@app.route('/booking/<int:booking_id>/action/<action>', methods=['POST'])
@login_required
def booking_action(booking_id, action):
    db = get_db()
    booking = db.execute('SELECT * FROM bookings WHERE id = ?', (booking_id,)).fetchone()
    
    if not booking:
        flash('Booking not found.', 'danger')
        return redirect(url_for('index'))

    if action == 'accept' and session.get('worker_id') == booking['worker_id']:
        db.execute("UPDATE bookings SET status = 'ACCEPTED' WHERE id = ?", (booking_id,))
        add_notification(booking['customer_id'], "Booking Accepted", f"Your booking #{booking['id']} has been accepted by the worker.")
        flash('Booking accepted!', 'success')

    elif action == 'reject' and session.get('worker_id') == booking['worker_id']:
        db.execute("UPDATE bookings SET status = 'REJECTED' WHERE id = ?", (booking_id,))
        add_notification(booking['customer_id'], "Booking Rejected", f"Your booking #{booking['id']} was rejected.")
        flash('Booking rejected.', 'info')

    elif action == 'complete' and session.get('worker_id') == booking['worker_id']:
        db.execute("UPDATE bookings SET status = 'COMPLETED' WHERE id = ?", (booking_id,))
        update_worker_stats(booking['worker_id'])
        add_notification(booking['customer_id'], "Service Completed", f"Booking #{booking['id']} marked as completed by worker. Please leave a review!")
        flash('Booking marked as completed!', 'success')

    elif action == 'cancel':
        db.execute("UPDATE bookings SET status = 'CANCELLED' WHERE id = ?", (booking_id,))
        flash('Booking cancelled.', 'warning')

    db.commit()
    return redirect(url_for('booking_detail', booking_id=booking_id))

@app.route('/booking/<int:booking_id>/review', methods=['POST'])
@role_required('customer')
def add_review(booking_id):
    db = get_db()
    booking = db.execute('SELECT * FROM bookings WHERE id = ?', (booking_id,)).fetchone()

    if not booking or booking['customer_id'] != session['user_id'] or booking['status'] != 'COMPLETED':
        flash('Cannot review this booking.', 'danger')
        return redirect(url_for('customer_dashboard'))

    rating = int(request.form['rating'])
    comment = request.form['comment']

    try:
        db.execute('''
            INSERT INTO reviews (booking_id, customer_id, worker_id, rating, comment)
            VALUES (?, ?, ?, ?, ?)
        ''', (booking_id, session['user_id'], booking['worker_id'], rating, comment))
        db.commit()

        update_worker_stats(booking['worker_id'])
        flash('Thank you for your rating and review!', 'success')
    except sqlite3.IntegrityError:
        flash('Review already submitted for this booking.', 'info')

    return redirect(url_for('booking_detail', booking_id=booking_id))

@app.route('/customer/dashboard')
@role_required('customer')
def customer_dashboard():
    db = get_db()
    bookings = db.execute('''
        SELECT b.*, u_work.name as worker_name, w.primary_skill
        FROM bookings b
        JOIN workers w ON b.worker_id = w.id
        JOIN users u_work ON w.user_id = u_work.id
        WHERE b.customer_id = ?
        ORDER BY b.created_at DESC
    ''', (session['user_id'],)).fetchall()

    return render_template('customer_dashboard.html', bookings=bookings)

@app.route('/worker/dashboard')
@role_required('worker')
def worker_dashboard():
    db = get_db()
    worker_id = session.get('worker_id')
    
    worker = db.execute('SELECT * FROM workers WHERE id = ?', (worker_id,)).fetchone()
    bookings = db.execute('''
        SELECT b.*, u.name as customer_name, u.phone as customer_phone
        FROM bookings b
        JOIN users u ON b.customer_id = u.id
        WHERE b.worker_id = ?
        ORDER BY b.created_at DESC
    ''', (worker_id,)).fetchall()

    earnings_data = db.execute('''
        SELECT COALESCE(SUM(worker_amount), 0) as total_earnings,
               COUNT(CASE WHEN status='COMPLETED' THEN 1 END) as completed_count,
               COUNT(CASE WHEN status='PENDING' THEN 1 END) as pending_count
        FROM bookings
        WHERE worker_id = ?
    ''', (worker_id,)).fetchone()

    return render_template('worker_dashboard.html', worker=worker, bookings=bookings, stats=earnings_data)

@app.route('/admin')
@role_required('admin')
def admin_dashboard():
    db = get_db()
    
    stats = {
        'total_customers': db.execute("SELECT COUNT(*) FROM users WHERE role='customer'").fetchone()[0],
        'total_workers': db.execute("SELECT COUNT(*) FROM workers").fetchone()[0],
        'pending_workers': db.execute("SELECT COUNT(*) FROM workers WHERE verification_status='Pending'").fetchone()[0],
        'total_bookings': db.execute("SELECT COUNT(*) FROM bookings").fetchone()[0],
        'completed_bookings': db.execute("SELECT COUNT(*) FROM bookings WHERE status='COMPLETED'").fetchone()[0],
        'total_commission': db.execute("SELECT COALESCE(SUM(commission), 0) FROM bookings WHERE status='COMPLETED'").fetchone()[0]
    }

    workers_list = db.execute('''
        SELECT w.*, u.name, u.email, u.phone, u.city 
        FROM workers w 
        JOIN users u ON w.user_id = u.id 
        ORDER BY w.id DESC
    ''').fetchall()

    bookings = db.execute('''
        SELECT b.*, u_cust.name as customer_name, u_work.name as worker_name
        FROM bookings b
        JOIN users u_cust ON b.customer_id = u_cust.id
        JOIN workers w ON b.worker_id = w.id
        JOIN users u_work ON w.user_id = u_work.id
        ORDER BY b.created_at DESC LIMIT 10
    ''').fetchall()

    return render_template('admin_dashboard.html', stats=stats, workers=workers_list, bookings=bookings)

@app.route('/admin/worker/<int:worker_id>/status/<status>', methods=['POST'])
@role_required('admin')
def admin_update_worker_status(worker_id, status):
    if status in ['Verified', 'Rejected', 'Pending']:
        db = get_db()
        db.execute('UPDATE workers SET verification_status = ? WHERE id = ?', (status, worker_id))
        db.commit()
        
        worker = db.execute('SELECT user_id FROM workers WHERE id = ?', (worker_id,)).fetchone()
        if worker:
            add_notification(worker['user_id'], "Verification Update", f"Your account status has been updated to: {status}")

        flash(f'Worker status updated to {status}.', 'success')
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)