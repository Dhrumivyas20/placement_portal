from sqlalchemy import or_
from sqlite3 import IntegrityError
from flask import Flask, redirect, send_from_directory, url_for, render_template, request, session, flash
from sqlalchemy import func
from Models.model import *
from datetime import datetime, date, timedelta
from functools import wraps
from werkzeug.security import generate_password_hash

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

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_role' not in session or session['user_role'] != 'admin':
            flash("Unauthorized access!", "danger")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def company_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_role' not in session or session['user_role'] != 'company':
            flash("Unauthorized access!", "danger")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
    
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
    if session.get("user_id") and session.get("user_role"):
        if session["user_role"] == "admin":
            return redirect(url_for("admin_dashboard"))
        elif session["user_role"] == "company":
            return redirect(url_for("company_dashboard"))
        elif session["user_role"] == "student":
            return redirect(url_for("student_dashboard"))

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

            # Blacklisted
            if company.company_is_blacklisted:
                flash("Your account has been blacklisted by admin.", "dark")
                return redirect(url_for('login'))

            # Rejected
            if company.company_is_rejected:
                flash("Your registration was rejected by admin.", "danger")
                return redirect(url_for('login'))

            # Not Approved Yet
            if not company.company_is_approved:
                flash("Your account is pending admin approval.", "warning")
                return redirect(url_for('login'))

            # Approved → Login Allowed
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

#Admin Dashboard
@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    current_year = datetime.now().year
    
    #Statistics
    total_students = Student.query.count()
    total_companies = Company.query.filter(Company.company_is_approved == True).count()
    total_student_applications = Application.query.count()
    total_drives = PlacementDrive.query.count()

    #Search Functionality
    search_query = request.args.get('search', '').strip()

    student_query = Student.query
    registered_company_query = Company.query.filter(Company.company_is_approved == True)
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

    #Drives
    drives = PlacementDrive.query.order_by(
        PlacementDrive.created_at.desc()
    ).all()

    #Student Applications
    applications = Application.query.order_by(
        Application.application_date.desc()
    ).all()

    return render_template(
    "admin_dashboard.html",
    students=students,
    current_year=current_year,
    companies=companies,
    registered_companies=registered_companies,
    total_students=total_students,
    total_companies=total_companies,
    total_student_applications=total_student_applications,
    total_drives=total_drives,
    search_query=search_query,
    drives=drives,
    applications=applications
)

#Admin-Student Management Routes
@app.route("/admin/student/blacklist/<int:student_id>", methods=["POST"])
@admin_required
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

#Admin-Company Management Routes
@app.route("/admin/company/approve/<int:company_id>", methods=["POST"])
@admin_required
def approve_company(company_id):

    company = Company.query.get_or_404(company_id)

    if company.company_is_blacklisted:
        flash("Cannot approve a blacklisted company.", "danger")
        return redirect(url_for("admin_dashboard"))

    company.company_is_approved = True
    company.approval_status = "approved"
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
    company.approval_status = "rejected"
    company.company_is_approved = False   

    db.session.commit()

    flash("Company rejected successfully!", "warning")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/company/blacklist/<int:company_id>", methods=["POST"])
@admin_required
def blacklist_company(company_id):

    company = Company.query.get_or_404(company_id)

    company.company_is_blacklisted = True
    company.approval_status = "blacklisted"
    company.company_is_approved = False  

    db.session.commit()

    flash("Company blacklisted.", "danger")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/company/unblacklist/<int:company_id>", methods=["POST"])
@admin_required
def unblacklist_company(company_id):

    company = Company.query.get_or_404(company_id)

    company.company_is_blacklisted = False
    company.approval_status = "approved"
    company.company_is_approved = True  

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

#Admin-Drives
@app.route("/admin/drive/approve/<int:drive_id>", methods=["POST"])
@admin_required
def approve_drive(drive_id):

    drive = PlacementDrive.query.get_or_404(drive_id)

    if drive.drive_is_rejected :
        flash("Rejected drive cannot be approved.", "danger")
        return redirect(url_for("admin_dashboard"))

    drive.drive_is_approved = True
    drive.drive_is_rejected = False
    drive.drive_status = "open"

    db.session.commit()

    flash("Drive approved successfully!", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/drive/reject/<int:drive_id>", methods=["POST"])
@admin_required
def reject_drive(drive_id):

    drive = PlacementDrive.query.get_or_404(drive_id)

    drive.drive_is_rejected = True
    drive.drive_is_approved = False
    drive.drive_status = "rejected"

    db.session.commit()

    flash("Drive rejected successfully!", "warning")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/drive/close/<int:drive_id>", methods=["POST"])
@admin_required
def close_drive(drive_id):

    drive = PlacementDrive.query.get_or_404(drive_id)

    if not drive.drive_is_approved:
        flash("Only approved drives can be closed.", "danger")
        return redirect(url_for("admin_dashboard"))

    if drive.drive_status == "closed":
        flash("Drive already closed.", "info")
        return redirect(url_for("admin_dashboard"))

    drive.drive_status = "closed"

    db.session.commit()

    flash("Drive marked as completed.", "success")
    return redirect(url_for("admin_dashboard"))

#Admin-Student Application Details Modal
@app.route("/admin/view_resume/<int:application_id>")
@admin_required
def view_resume(application_id):

    application = Application.query.get_or_404(application_id)

    resume_filename = application.student.student_resume_filename

    if not resume_filename:
        flash("Resume not uploaded.", "warning")
        return redirect(url_for("admin_dashboard"))

    return send_from_directory(
        "static/uploads/resumes",  # folder where resumes stored
        resume_filename
    )

#Company 
@app.route("/company/dashboard")
@company_required
def company_dashboard():

    company_id = session["user_id"]

    expired_drives = PlacementDrive.query.filter(
        PlacementDrive.company_id == company_id,
        PlacementDrive.drive_status == "open",
        PlacementDrive.application_deadline < date.today()
    ).all()

    for drive in expired_drives:
        drive.drive_status = "closed"

    if expired_drives:
        db.session.commit()

    pending_drives = PlacementDrive.query.filter_by(
        company_id=company_id,
        drive_status="pending"
    ).all()

    approved_drives = PlacementDrive.query.filter_by(
        company_id=company_id,
        drive_status="open"
    ).all()

    rejected_drives = PlacementDrive.query.filter_by(
        company_id=company_id,
        drive_status="rejected"
    ).all()

    closed_drives = PlacementDrive.query.filter_by(
        company_id=company_id,
        drive_status="closed"
    ).all()

    for drive in approved_drives:
        drive.total_applicants = len(drive.applications)
        drive.shortlisted = len([a for a in drive.applications if a.application_status == "Shortlisted"])
        drive.selected = len([a for a in drive.applications if a.application_status == "Selected"])

    return render_template(
        "company_dashboard.html",
        pending_drives=pending_drives,
        approved_drives=approved_drives,
        rejected_drives=rejected_drives,
        closed_drives=closed_drives,
        total_applicants=sum(len(drive.applications) for drive in approved_drives),
        total_shortlisted=sum(len([a for a in drive.applications if a.application_status == "Shortlisted"]) for drive in approved_drives),
        total_selected=sum(len([a for a in drive.applications if a.application_status == "Selected"]) for drive in approved_drives)
    )

#Create Drive
@app.route("/company/drive/create", methods=["POST"])
@company_required
def create_drive():
    try:
        # Convert deadline safely
        deadline_str = request.form.get("application_deadline")
        deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()

        if deadline < date.today():
            flash("Application deadline cannot be in the past.", "danger")
            return redirect(url_for("company_dashboard"))

        drive = PlacementDrive(
            company_id=session['user_id'],   
            drive_name=request.form.get("drive_name"),
            job_title=request.form.get("job_title"),
            job_description=request.form.get("job_description"),
            job_location=request.form.get("job_location"),
            job_type=request.form.get("job_type"),
            job_salary_range=request.form.get("job_salary_range"),
            job_eligibility_criteria=request.form.get("job_eligibility_criteria"),
            job_no_of_positions=request.form.get("job_no_of_positions") or 1,
            application_deadline=deadline,
            drive_is_approved=False,
            drive_is_rejected=False,
            drive_status="pending"  
        )

        db.session.add(drive)
        db.session.commit()

        flash("Drive created successfully! Awaiting admin approval.", "success")

    except Exception as e:
        db.session.rollback()
        flash("Error creating drive. Please try again.", "danger")

    return redirect(url_for("company_dashboard"))
    
@app.route("/company/application/update/<int:application_id>", methods=["POST"])
@company_required
def update_application_status(application_id):

    application = Application.query.get_or_404(application_id)

    # SECURITY CHECK → ensure application belongs to this company
    if application.placement_drive.company_id != session["user_id"]:
        flash("Unauthorized action.", "danger")
        return redirect(url_for("company_dashboard"))

    new_status = request.form.get("status")

    if new_status not in ["Shortlisted", "Selected", "Rejected"]:
        flash("Invalid status value.", "danger")
        return redirect(url_for("company_dashboard"))

    application.application_status = new_status
    db.session.commit()

    flash("Application status updated successfully.", "success")
    return redirect(url_for("company_dashboard"))

#View Drive Details
@app.route("/company/drive/<int:drive_id>")
@company_required
def view_drive(drive_id):

    drive = PlacementDrive.query.get_or_404(drive_id)

    # security check (important)
    if drive.company_id != session["user_id"]:
        flash("Unauthorized access.", "danger")
        return redirect(url_for("company_dashboard"))

    return render_template("company_dashboard.html", drive=drive)

#Mark As Done
@app.route("/company/drive/complete/<int:drive_id>")
@company_required
def mark_drive_complete(drive_id):

    drive = PlacementDrive.query.get_or_404(drive_id)

    if drive.company_id != session["user_id"]:
        flash("Unauthorized action.", "danger")
        return redirect(url_for("company_dashboard"))

    if drive.drive_status != "open":
        flash("Only ongoing drives can be closed.", "warning")
        return redirect(url_for("company_dashboard"))

    drive.drive_status = "closed"
    db.session.commit()

    flash("Drive marked as completed.", "success")
    return redirect(url_for("company_dashboard"))

#Update Drive Details
@app.route("/company/drive/update/<int:drive_id>", methods=["POST"])
@company_required
def update_drive(drive_id):

    drive = PlacementDrive.query.get_or_404(drive_id)

    if drive.company_id != session["user_id"]:
        flash("Unauthorized action.", "danger")
        return redirect(url_for("company_dashboard"))

    drive.job_title = request.form.get("job_title")
    drive.job_description = request.form.get("job_description")
    drive.job_location = request.form.get("job_location")
    drive.job_salary_range = request.form.get("job_salary_range")
    drive.job_eligibility_criteria = request.form.get("job_eligibility_criteria")
    drive.job_type = request.form.get("job_type")
    drive.drive_name = request.form.get("drive_name")

    drive.drive_is_approved = False
    drive.drive_is_rejected = False
    drive.drive_status = "pending"

    drive.job_no_of_positions = int(request.form.get("job_no_of_positions") or 1)

    deadline_str = request.form.get("application_deadline")
    if deadline_str:
        drive.application_deadline = datetime.strptime(
            deadline_str, "%Y-%m-%d"
        ).date()

    db.session.commit()

    flash("Drive updated successfully! Awaiting admin re-approval.", "success")
    return redirect(url_for("company_dashboard"))

#Student 
@app.route("/student/dashboard")
def student_dashboard():
    if 'user_role' not in session or session['user_role'] != 'student':
        return redirect(url_for('login'))
    return render_template("student_dashboard.html")

if __name__ == "__main__":
    app.run(debug=True)