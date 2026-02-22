from sqlalchemy import or_
from sqlite3 import IntegrityError
from flask import Flask, redirect, url_for, render_template, request, session, flash
from sqlalchemy import func
from Models.model import *
from datetime import datetime, date, timedelta
from functools import wraps

app = Flask(__name__)

app.config['SECRET_KEY'] = 'SecretKey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///placement_portal.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Create tables and default admin
with app.app_context():
    db.create_all()
    
    admin = Admin.query.filter_by(admin_role='admin').first()
    if not admin:
        admin = Admin(
            admin_username='admin',
            admin_email='admin@gmail.com',
            admin_role='admin'
        )

        admin.set_password("admin123")
        
        db.session.add(admin)
        db.session.commit()
        print("Default admin created!")
    else:
        print("Admin already exists!")

@app.route('/',methods=['GET','POST'])
def landing_page():
    return render_template('landing_page.html')

@app.route("/signup", methods=["GET", "POST"])
def signup():
    role = request.args.get("role", "student")
    return render_template("signup.html", role=role)

@app.route("/student/signup", methods=["POST", "GET"])
def student_signup():
    if request.method == "POST":
        student_name = request.form.get("student_name")
        student_email = request.form.get("student_email")
        student_password = request.form.get("student_password")
        student_department = request.form.get("student_department")
        student_cgpa = float(request.form.get("student_cgpa"))
        student_joining_year = int(request.form.get("student_joining_year"))
        student_graduation_year = int(request.form.get("student_graduation_year"))

        new_student = Student(
            student_name=student_name,
            student_email=student_email,
            student_department=student_department,
            student_cgpa=student_cgpa,
            student_joining_year=student_joining_year,
            student_graduation_year=student_graduation_year
        )

        new_student.set_password(student_password)

        try:
            db.session.add(new_student)
            db.session.commit()
            flash("Student registered successfully!", "success")
            return redirect(url_for('login'))
        except IntegrityError:
            db.session.rollback()
            flash("Email already exists. Please use a different email.", "danger")
    return redirect(url_for('signup', role='student'))

@app.route("/company/signup", methods=["POST"])
def company_signup():
    if request.method == "POST":
        company_name = request.form.get("company_name")
        company_email = request.form.get("company_email")
        company_password = request.form.get("company_password")
        company_hr_contact_name = request.form.get("company_hr_contact_name")
        company_hr_contact_email = request.form.get("company_hr_contact_email")
        company_industry = request.form.get("company_industry")

        new_company = Company(
            company_name=company_name,
            company_email=company_email,
            company_hr_contact_name=company_hr_contact_name,
            company_hr_contact_email=company_hr_contact_email,
            company_industry=company_industry
        )

        new_company.set_password(company_password)

        try:
            db.session.add(new_company)
            db.session.commit()
            flash("Company registered successfully! Awaiting admin approval.", "success")
            return redirect(url_for('login'))
        except IntegrityError:
            db.session.rollback()
            flash("Email already exists. Please use a different email.", "danger")
    return redirect(url_for('signup', role='company'))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    if request.method == "POST":
        session.clear() 

        email = request.form.get("email")
        password = request.form.get("password")

        # Check if user is a student
        student = Student.query.filter_by(student_email=email).first()
        if student and student.check_password(password):
            session['user_id'] = student.student_id
            session['user_role'] = 'student'
            flash("Logged in successfully as student!", "success")
            return redirect(url_for('student_dashboard'))

        # Check if user is a company
        company = Company.query.filter_by(company_email=email).first()
        if company and company.check_password(password):
            if company.approval_status != "approved":
                flash("Your account is pending admin approval.", "warning")
                return redirect(url_for('login'))
            session['user_id'] = company.company_id
            session['user_role'] = 'company'
            flash("Logged in successfully as company!", "success")
            return redirect(url_for('company_dashboard'))

        # Check if user is an admin
        admin = Admin.query.filter_by(admin_email=email).first()
        if admin and admin.check_password(password):
            session['user_id'] = admin.admin_id
            session['user_role'] = 'admin'
            flash("Logged in successfully as admin!", "success")
            return redirect(url_for('admin_dashboard'))

        flash("Invalid email or password. Please try again.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully!", "success")
    return redirect(url_for('login'))

@app.context_processor
def inject_user():
    if 'user_role' in session:
        if session['user_role'] == 'student':
            user = Student.query.get(session['user_id'])
            return dict(username=user.student_name)

        elif session['user_role'] == 'company':
            user = Company.query.get(session['user_id'])
            return dict(username=user.company_name)

        elif session['user_role'] == 'admin':
            user = Admin.query.get(session['user_id'])
            return dict(username=user.admin_username)

    return dict(username=None)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_role' not in session or session['user_role'] != 'admin':
            flash("Unauthorized access!", "danger")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

#Admin Dashboard
@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    current_year = datetime.now().year
    
    #Statistics
    total_students = Student.query.count()
    total_companies = Company.query.count()
    total_applications = Application.query.count()
    total_drives = PlacementDrive.query.count()

    #Search Functionality
    search_query = request.args.get('search', '').strip()

    student_query = Student.query
    registered_company_query = Company.query.filter_by(company_is_approved=True)
    application_company_query = Company.query

    if search_query:
        student_conditions = [
            Student.student_name.ilike(f"%{search_query}%"),
            Student.student_email.ilike(f"%{search_query}%"),
            Student.student_phone.ilike(f"%{search_query}%"),
            Student.student_department.ilike(f"%{search_query}%")
        ]

        if search_query.isdigit():
            student_conditions.append(Student.student_id == int(search_query))

        students = student_query.filter(or_(*student_conditions)).all()

        company_conditions = [
            Company.company_name.ilike(f"%{search_query}%"),
            Company.company_email.ilike(f"%{search_query}%"),
            Company.company_industry.ilike(f"%{search_query}%")
        ]

        registered_companies = registered_company_query.filter(
            or_(*company_conditions)
        ).all()

        companies = application_company_query.filter(
            or_(*company_conditions)
        ).all()

    else:
        students = student_query.all()
        registered_companies = registered_company_query.all()
        companies = application_company_query.all()


    return render_template(
    "admin_dashboard.html",
    students=students,
    current_year=current_year,
    companies=companies,
    registered_companies=registered_companies,
    total_students=total_students,
    total_companies=total_companies,
    total_applications=total_applications,
    total_drives=total_drives,
    search_query=search_query,
)

#Student Management Routes
@app.route("/admin/student/blacklist/<int:student_id>", methods=["POST"])
def blacklist_student(student_id):
    student = Student.query.get_or_404(student_id)

    if student:
        student.student_is_blacklisted = True
        db.session.commit()
        flash(f"{student.student_name} is blacklisted", "dark")
    else:
        flash("Student not found", "danger")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/student/toggle_blacklist/<int:student_id>", methods=["POST"])
@admin_required
def toggle_blacklist_student(student_id):

    student = Student.query.get_or_404(student_id)

    student.student_is_blacklisted = not student.student_is_blacklisted
    db.session.commit()

    if student.student_is_blacklisted:
        flash(f"{student.student_name} has been blacklisted.", "danger")
    else:
        flash(f"{student.student_name} has been unblacklisted.", "success")

    return redirect(url_for("admin_dashboard"))

#Company Management Routes
@app.route("/admin/company/approve/<int:company_id>", methods=["POST"])
@admin_required
def approve_company(company_id):

    company = Company.query.get_or_404(company_id)

    if company.company_is_blacklisted:
        flash("Cannot approve a blacklisted company.", "danger")
        return redirect(url_for("admin_dashboard"))

    company.company_is_approved = True
    company.company_is_rejected = False

    db.session.commit()

    flash("Company approved successfully!", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/company/reject/<int:company_id>", methods=["POST"])
@admin_required
def reject_company(company_id):

    company = Company.query.get_or_404(company_id)

    if company.company_is_blacklisted:
        flash("Cannot reject a blacklisted company.", "danger")
        return redirect(url_for("admin_dashboard"))

    company.company_is_rejected = True
    company.company_is_approved = False   

    db.session.commit()

    flash("Company rejected successfully!", "warning")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/company/blacklist/<int:company_id>", methods=["POST"])
@admin_required
def blacklist_company(company_id):

    company = Company.query.get_or_404(company_id)

    company.company_is_blacklisted = True
    company.company_is_approved = False  # remove active status

    db.session.commit()

    flash("Company blacklisted.", "danger")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/company/unblacklist/<int:company_id>", methods=["POST"])
@admin_required
def unblacklist_company(company_id):

    company = Company.query.get_or_404(company_id)

    company.company_is_blacklisted = False
    company.company_is_approved = True  # make active again

    db.session.commit()

    flash("Company unblacklisted successfully.", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/company/toggle_blacklist/<int:company_id>", methods=["POST"])
@admin_required
def toggle_blacklist_company(company_id):
    company = Company.query.get_or_404(company_id)

    company.company_is_blacklisted = not company.company_is_blacklisted
    db.session.commit()

    flash("Company status updated!", "success")
    return redirect(url_for("admin_dashboard"))

#Drives
@app.route("/admin/drive/details/<int:drive_id>")
def drive_details(drive_id):
    if 'user_role' not in session or session['user_role'] != 'admin':
        return redirect(url_for('login'))

    drive = PlacementDrive.query.get_or_404(drive_id)
    return render_template("drive_details.html", drive=drive)

@app.route("/admin/drive/approve/<int:drive_id>")
def approve_drive(drive_id):
    if 'user_role' not in session or session['user_role'] != 'admin':
        return redirect(url_for('login'))

    drive = PlacementDrive.query.get_or_404(drive_id)
    drive.status = "approved"
    db.session.commit()

    flash("Drive approved successfully!", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/drive/reject/<int:drive_id>")
def reject_drive(drive_id):
    if 'user_role' not in session or session['user_role'] != 'admin':
        return redirect(url_for('login'))

    drive = PlacementDrive.query.get_or_404(drive_id)
    drive.status = "rejected"
    db.session.commit()

    flash("Drive rejected!", "danger")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/student_applications/<int:student_id>")
def view_student_applications(student_id):
    if 'user_role' not in session or session['user_role'] != 'admin':
        return redirect(url_for('login'))

    student = Student.query.get_or_404(student_id)
    applications = Application.query.filter_by(student_id=student_id).all()
    return render_template("student_applications.html", student=student, applications=applications)



#Student 
@app.route("/student/dashboard")
def student_dashboard():
    if 'user_role' not in session or session['user_role'] != 'student':
        return redirect(url_for('login'))
    return render_template("student_dashboard.html")

#Company 
@app.route("/company/dashboard")
def company_dashboard():
    if 'user_role' not in session or session['user_role'] != 'company':
        return redirect(url_for('login'))
    return render_template("company_dashboard.html")

if __name__ == "__main__":
    app.run(debug=True)