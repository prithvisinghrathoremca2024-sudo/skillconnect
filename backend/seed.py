import sqlite3
import os
from werkzeug.security import generate_password_hash

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE = os.path.join(PROJECT_ROOT, 'skillconnect.db')

def seed_database():
    if not os.path.exists(DATABASE):
        print("Database not found. Start the app with 'python backend/app.py' first.")
        return

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    print("Seeding SkillConnect database...")

    # Clear existing data
    cursor.execute("DELETE FROM reviews")
    cursor.execute("DELETE FROM bookings")
    cursor.execute("DELETE FROM workers")
    cursor.execute("DELETE FROM users")
    cursor.execute("DELETE FROM categories")
    cursor.execute("DELETE FROM notifications")

    # Categories
    categories = [
        ("Tailoring", "Custom clothing stitching, alterations, and repairs"),
        ("Carpentry", "Furniture repair, custom woodwork, and fittings"),
        ("Plumbing", "Pipe repairs, leak fixing, and fixture installation"),
        ("Electrical Work", "Wiring, appliance setup, and fault repairs"),
        ("Cleaning", "Home deep cleaning, sofa cleaning, and sanitation"),
        ("Painting", "Interior, exterior home painting, and touch-ups"),
        ("Cooking", "Home cooking, catering, and meal preparation"),
        ("Appliance Repair", "Washing machine, refrigerator, and AC repair")
    ]
    cursor.executemany("INSERT INTO categories (name, description) VALUES (?, ?)", categories)

    # Admin User
    admin_hash = generate_password_hash("admin123")
    cursor.execute("""
        INSERT INTO users (name, email, phone, password_hash, role, city, area)
        VALUES ('Platform Admin', 'admin@skillconnect.com', '9876543210', ?, 'admin', 'Jaipur', 'Central')
    """, (admin_hash,))

    # Demo Customers
    customers_data = [
        ("Rahul Mehta", "rahul@gmail.com", "9811122233", "Malviya Nagar", "Jaipur"),
        ("Priya Sharma", "priya@gmail.com", "9822233344", "Vaishali Nagar", "Jaipur"),
        ("Anil Kapoor", "anil@gmail.com", "9833344455", "Raja Park", "Jaipur"),
        ("Sangeeta Roy", "sangeeta@gmail.com", "9844455566", "Mansarovar", "Jaipur"),
        ("Vikas Gupta", "vikas@gmail.com", "9855566677", "C-Scheme", "Jaipur")
    ]

    customer_ids = []
    for name, email, phone, area, city in customers_data:
        hashed = generate_password_hash("password123")
        cursor.execute("""
            INSERT INTO users (name, email, phone, password_hash, role, city, area)
            VALUES (?, ?, ?, ?, 'customer', ?, ?)
        """, (name, email, phone, hashed, city, area))
        customer_ids.append(cursor.lastrowid)

    # Demo Workers
    workers_data = [
        ("Ramesh Kumar", "ramesh@skillconnect.com", "9911100011", "Carpentry", "Furniture, Woodwork", 8, "Expert in wooden table repairs and doors.", 350, "9 AM - 6 PM", "Verified"),
        ("Sunita Devi", "sunita@skillconnect.com", "9922200022", "Tailoring", "Alterations, Suits", 6, "Specialized in traditional dress tailoring.", 250, "10 AM - 7 PM", "Verified"),
        ("Amit Sharma", "amit@skillconnect.com", "9933300033", "Electrical Work", "Short Circuit, Wiring", 10, "Certified home electrician for all major repairs.", 400, "8 AM - 8 PM", "Verified"),
        ("Pooja Verma", "pooja@skillconnect.com", "9944400044", "Cleaning", "Deep Cleaning, Kitchen", 4, "High quality home and office cleaning service.", 300, "8 AM - 4 PM", "Verified"),
        ("Rahul Khan", "rahul.k@skillconnect.com", "9955500055", "Plumbing", "Tap repair, Leakage", 7, "Prompt emergency plumbing services.", 350, "7 AM - 9 PM", "Verified"),
        ("Meena Kumari", "meena@skillconnect.com", "9966600066", "Cooking", "North Indian, Snacks", 9, "Hygiene-focused home cook for family events.", 500, "6 AM - 2 PM", "Verified"),
        ("Suresh Patel", "suresh@skillconnect.com", "9977700077", "Painting", "Wall painting, Polish", 5, "Neat painting with quick completion.", 450, "9 AM - 6 PM", "Pending"),
        ("Dinesh Saini", "dinesh@skillconnect.com", "9988800088", "Appliance Repair", "AC, Refrigerator", 11, "Multi-appliance expert repair technician.", 500, "9 AM - 7 PM", "Verified")
    ]

    worker_ids = []
    for name, email, phone, primary_skill, add_skill, exp, about, price, hours, v_status in workers_data:
        hashed = generate_password_hash("password123")
        cursor.execute("""
            INSERT INTO users (name, email, phone, password_hash, role, city, area, address)
            VALUES (?, ?, ?, ?, 'worker', 'Jaipur', 'Local Market Area', 'Street 4, Sector 2')
        """, (name, email, phone, hashed))
        uid = cursor.lastrowid

        cursor.execute("""
            INSERT INTO workers (user_id, primary_skill, additional_skills, experience_years, about, price_per_hour, working_hours, verification_status, rating, completed_jobs)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0.0, 0)
        """, (uid, primary_skill, add_skill, exp, about, price, hours, v_status))
        worker_ids.append(cursor.lastrowid)

    # Demo Bookings & Reviews
    bookings_data = [
        (customer_ids[0], worker_ids[0], "Carpentry Repair", "2026-10-05", "10:00 AM", "1000.0", "COMPLETED", 5, "Excellent woodwork! Highly recommended."),
        (customer_ids[1], worker_ids[1], "Dress Tailoring", "2026-10-06", "02:00 PM", "600.0", "COMPLETED", 5, "Sunita ji stitched my outfit perfectly."),
        (customer_ids[2], worker_ids[2], "Fan & Switch Repair", "2026-10-07", "11:00 AM", "800.0", "COMPLETED", 4, "Prompt response and fixed quickly."),
        (customer_ids[3], worker_ids[3], "Kitchen Deep Cleaning", "2026-10-08", "09:00 AM", "1200.0", "ACCEPTED", None, None),
        (customer_ids[4], worker_ids[4], "Bathroom Plumbing Leakage", "2026-10-09", "04:00 PM", "750.0", "PENDING", None, None)
    ]

    for cid, wid, service, date, time, budget, status, rating, comment in bookings_data:
        b_amount = float(budget)
        comm = round(b_amount * 0.10, 2)
        w_amount = round(b_amount - comm, 2)

        cursor.execute("""
            INSERT INTO bookings (customer_id, worker_id, service_name, booking_date, booking_time, address, work_description, estimated_budget, commission, worker_amount, status)
            VALUES (?, ?, ?, ?, ?, 'Customer Address', 'Demo request description', ?, ?, ?, ?)
        """, (cid, wid, service, date, time, b_amount, comm, w_amount, status))
        bid = cursor.lastrowid

        if status == 'COMPLETED' and rating:
            cursor.execute("""
                INSERT INTO reviews (booking_id, customer_id, worker_id, rating, comment)
                VALUES (?, ?, ?, ?, ?)
            """, (bid, cid, wid, rating, comment))

            # Update worker metrics
            cursor.execute("""
                UPDATE workers 
                SET completed_jobs = completed_jobs + 1, rating = ?
                WHERE id = ?
            """, (float(rating), wid))

    conn.commit()
    conn.close()
    print("Database successfully seeded!")

if __name__ == '__main__':
    seed_database()