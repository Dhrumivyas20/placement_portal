from operator import or_
from sqlite3 import IntegrityError
from flask import Flask, redirect, url_for, render_template, request, session, flash
from sqlalchemy import func
from Models.model import *
from datetime import datetime, date, timedelta

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

@app.route("/admin/dashboard")
def admin_dashboard():
    current_year = datetime.now().year

    if 'user_role' not in session or session['user_role'] != 'admin':
        return redirect(url_for('login'))
    
    total_students = Student.query.count()
    total_companies = Company.query.count()
    total_applications = Application.query.count()
    total_drives = PlacementDrive.query.count()

    # total_students = db.session.query(func.count(Student.student_id)).scalar()
    # total_companies = db.session.query(func.count(Company.company_id)).scalar()
    # total_applications = db.session.query(func.count(Application.application_id)).scalar()
    # total_drives = db.session.query(func.count(PlacementDrive.drive_id)).scalar()
    
    #Search Functionality
    search_query = request.args.get('search', '').strip()

    student_query = Student.query
    company_query = Company.query

    if search_query:
        student_filters = student_query.filter(or_(
            Student.student_name.ilike(f'%{search_query}%'),
            Student.student_email.ilike(f'%{search_query}%')
        ))

        if search_query.isdigit():
            student_filters = student_filters.filter(Student.student_id == int(search_query))
        students = student_query.filter(or_(*student_filters)).all()

        companies = company_query.filter(
            Company.company_name.ilike(f"%{search_query}%")
        ).all()
    else:
        students = student_query.all()
        companies = company_query.all()


    return render_template(
    "admin_dashboard.html",
    students=students,
    current_year=current_year,
    companies=companies,
    total_students=total_students,
    total_companies=total_companies,
    total_applications=total_applications,
    total_drives=total_drives,
    search_query=search_query
)

@app.route("/admin/student/blacklist/<int:student_id>")
def blacklist_student(student_id):
    student = Student.query.get_or_404(student_id)

    student.is_blacklisted = True
    db.session.commit()

    return redirect(url_for("admin_dashboard"))

@app.route("/admin/company/blacklist/<int:company_id>")
def blacklist_company(company_id):
    if 'user_role' not in session or session['user_role'] != 'admin':
        return redirect(url_for('login'))
    
    company = Company.query.get_or_404(company_id)

    company.is_blacklisted = True
    db.session.commit()

    flash("Company blacklisted", "dark")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/company/details/<int:company_id>")
def company_details(company_id):
    if 'user_role' not in session or session['user_role'] != 'admin':
        return redirect(url_for('login'))

    company = Company.query.get_or_404(company_id)
    return render_template("company_details.html", company=company)

@app.route("/admin/company/approve/<int:company_id>")
def approve_company(company_id):
    if 'user_role' not in session or session['user_role'] != 'admin':
        return redirect(url_for('login'))
    
    company = Company.query.get_or_404(company_id)
    company.is_approved = True
    company.is_rejected = False
    db.session.commit()

    flash("Company approved successfully!", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/company/reject/<int:company_id>")
def reject_company(company_id):
    if 'user_role' not in session or session['user_role'] != 'admin':
        return redirect(url_for('login'))
    
    company = Company.query.get_or_404(company_id)

    company.is_rejected = True
    company.is_approved = False
    db.session.commit()

    flash("Company is Rejected", "danger")
    return redirect(url_for("admin_dashboard"))

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