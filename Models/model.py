from sqlalchemy import Date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Admin(db.Model):
    __tablename__ = 'admin'
    admin_id = db.Column(db.Integer, primary_key=True)
    admin_username = db.Column(db.String(80), unique=True, nullable=False)
    admin_email = db.Column(db.String(120), unique=True, nullable=False)
    admin_password_hash = db.Column(db.String(128), nullable=False)
    admin_role = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Password handling methods
    def set_password(self, password):
        self.admin_password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.admin_password_hash, password)
    
class Student(db.Model):
    __tablename__ = 'student'
    student_id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(80), nullable=False)
    student_email = db.Column(db.String(120), unique=True, nullable=False)
    student_password_hash = db.Column(db.String(128), nullable=False)
    student_dob = db.Column(db.Date, nullable=True)
    student_phone = db.Column(db.String(20), nullable=True)
    student_department = db.Column(db.String(50), nullable=False)
    student_cgpa = db.Column(db.Float, nullable=False)
    student_joining_year = db.Column(db.Integer, nullable=False)
    student_graduation_year = db.Column(db.Integer, nullable=False)
    student_resume_filename = db.Column(db.String(200), nullable=True)
    student_is_active = db.Column(db.Boolean, default=True)
    student_is_blacklisted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    #Relations
    applications = db.relationship('Application', backref='student', lazy=True)
    
    # Password handling methods
    def set_password(self, password):
        self.student_password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.student_password_hash, password)
    
class Company(db.Model):
    __tablename__ = 'company'
    company_id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(80), unique=True, nullable=False)
    company_email = db.Column(db.String(120), unique=True, nullable=False)
    company_password_hash = db.Column(db.String(128), nullable=False)
    company_hr_contact_name = db.Column(db.String(80), nullable=False)
    company_hr_contact_email = db.Column(db.String(120), nullable=False)
    company_website = db.Column(db.String(200), nullable=True)
    company_description = db.Column(db.Text, nullable=True)
    company_industry = db.Column(db.String(50), nullable=False)
    approval_status = db.Column(db.String(20), default='pending')
    company_is_approved = db.Column(db.Boolean, default=False)
    company_is_rejected = db.Column(db.Boolean, default=False)
    company_is_blacklisted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    #Relations
    placement_drive = db.relationship('PlacementDrive', backref='company', lazy=True)

    # Password handling methods
    def set_password(self, password):
        self.company_password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.company_password_hash, password)
    
class PlacementDrive(db.Model):
    __tablename__ = 'placement_drive'
    drive_id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.company_id'), nullable=False)
    job_title = db.Column(db.String(100), nullable=False)
    job_description = db.Column(db.Text, nullable=False)
    job_location = db.Column(db.String(100), nullable=False)
    job_type = db.Column(db.String(50), nullable=False)
    job_salary_range = db.Column(db.String(50), nullable=True)
    job_eligibility_criteria = db.Column(db.Text, nullable=True)
    job_no_of_positions = db.Column(db.Integer, nullable=False)
    application_deadline = db.Column(db.Date, nullable=False)
    drive_date_posted = db.Column(db.DateTime, default=datetime.utcnow)
    drive_status = db.Column(db.String(20), default='open')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    #relations
    applications = db.relationship('Application', backref='placement_drive', lazy=True)

class Application(db.Model):
    __tablename__ = 'application'
    application_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.student_id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('placement_drive.drive_id'), nullable=False)
    application_date = db.Column(db.DateTime, default=datetime.utcnow)
    application_status = db.Column(db.String(20), default='pending')
    remarks = db.Column(db.Text, nullable=True)

class PlacementStatistics(db.Model):
    __tablename__ = 'placement_statistics'
    stats_id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    total_students = db.Column(db.Integer, nullable=False)
    placed_students = db.Column(db.Integer, nullable=False)
    company_participation = db.Column(db.Integer, nullable=False)
    average_salary = db.Column(db.Float, nullable=True)
    highest_salary = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)