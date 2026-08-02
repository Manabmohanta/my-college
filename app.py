import os
import random
import threading
from datetime import datetime                                               
from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy                                     
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message

app = Flask(__name__)
app.config['SECRET_KEY'] = 'manab_secret_key_9938'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# --- Email Config ---                                                      
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'Bbdegreecollegerangamatia@gmail.com'
app.config['MAIL_PASSWORD'] = 'jofd caiz unhe yqch'

mail = Mail(app)

def send_async_email(app, msg):
    with app.app_context():
        try:
            mail.send(msg)
        except Exception as e:
            print("Email error:", e)

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)                            
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    ans1 = db.Column(db.String(200), nullable=True)  # Name
    ans2 = db.Column(db.String(200), nullable=True)  # Mobile
    ans3 = db.Column(db.String(200), nullable=True)  # Roll No
    ans4 = db.Column(db.String(200), nullable=True)  # Stream
    is_questions_submitted = db.Column(db.Boolean, default=False)

    has_given_exam = db.Column(db.Boolean, default=False)
    exam_score = db.Column(db.String(50), nullable=True)

    data_items = db.relationship('UserData', backref='owner', lazy=True, cascade='all, delete-orphan')

class UserData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text_content = db.Column(db.Text, nullable=True)
    file_path = db.Column(db.String(200), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Notice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.String(50), nullable=False)

class QuizQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_text = db.Column(db.Text, nullable=False)
    option1 = db.Column(db.String(200), nullable=False)
    option2 = db.Column(db.String(200), nullable=False)
    option3 = db.Column(db.String(200), nullable=False)
    option4 = db.Column(db.String(200), nullable=False)
    correct_option = db.Column(db.String(200), nullable=False)
    is_published = db.Column(db.Boolean, default=False)

class ImportantQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_title = db.Column(db.Text, nullable=False)
    answer_text = db.Column(db.Text, nullable=False)
    is_published = db.Column(db.Boolean, default=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin_dashboard'))
        if not current_user.is_questions_submitted:
            return redirect(url_for('questions'))
        return redirect(url_for('profile'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        action = request.form.get('action')
        email = request.form.get('email')
        password = request.form.get('password')

        if action == 'register':
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash('Email is already registered!', 'danger')
            else:
                hashed_pw = generate_password_hash(password, method='scrypt')
                new_user = User(email=email, password=hashed_pw, is_admin=False)
                db.session.add(new_user)
                db.session.commit()
                login_user(new_user)
                return redirect(url_for('questions'))

        elif action == 'login':
            user = User.query.filter_by(email=email).first()
            if user and check_password_hash(user.password, password):
                login_user(user)
                if user.is_admin:
                    return redirect(url_for('admin_dashboard'))
                if not user.is_questions_submitted:
                    return redirect(url_for('questions'))
                return redirect(url_for('profile'))
            else:
                flash('Invalid email or password!', 'danger')

    return render_template('login.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email, is_admin=True).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid Admin Credentials!', 'danger')

    return render_template('admin_login.html')

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))

    users_list = User.query.filter_by(is_admin=False, is_questions_submitted=True).all()
    notices_list = Notice.query.order_by(Notice.id.desc()).all()
    quiz_questions = QuizQuestion.query.all()
    important_questions = ImportantQuestion.query.all()                     
    total_submissions = len(users_list)

    return render_template('admin_dashboard.html', users=users_list, total=total_submissions, notices=notices_list, quiz_questions=quiz_questions, important_questions=important_questions)

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))

    user_to_delete = User.query.get_or_404(user_id)
    if user_to_delete.is_admin:
        flash('Cannot delete admin account!', 'danger')                     
        return redirect(url_for('admin_dashboard'))

    db.session.delete(user_to_delete)
    db.session.commit()
    flash('Student and all associated data deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_notice', methods=['POST'])
@login_required
def add_notice():
    if not current_user.is_admin:
        return redirect(url_for('login'))

    title = request.form.get('title')
    content = request.form.get('content')
    current_date = datetime.now().strftime("%d %b %Y, %I:%M %p")

    if title and content:
        new_notice = Notice(title=title, content=content, date_posted=current_date)
        db.session.add(new_notice)
        db.session.commit()
        flash('Notice published successfully!', 'success')

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_notice/<int:notice_id>', methods=['POST'])
@login_required
def delete_notice(notice_id):
    if not current_user.is_admin:
        return redirect(url_for('login'))

    notice = Notice.query.get_or_404(notice_id)
    db.session.delete(notice)
    db.session.commit()
    flash('Notice deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_important_q', methods=['POST'])
@login_required
def add_important_q():
    if not current_user.is_admin:
        return redirect(url_for('login'))

    question_title = request.form.get('question_title')
    answer_text = request.form.get('answer_text')

    if question_title and answer_text:
        new_iq = ImportantQuestion(question_title=question_title, answer_text=answer_text, is_published=False)
        db.session.add(new_iq)
        db.session.commit()
        flash('Important question added successfully!', 'success')

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/publish_important_q/<int:q_id>', methods=['POST'])
@login_required
def publish_important_q(q_id):
    if not current_user.is_admin:
        return redirect(url_for('login'))

    iq = ImportantQuestion.query.get_or_404(q_id)
    iq.is_published = True
    db.session.commit()
    flash('Important question published successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/unpublish_important_q/<int:q_id>', methods=['POST'])
@login_required
def unpublish_important_q(q_id):
    if not current_user.is_admin:
        return redirect(url_for('login'))

    iq = ImportantQuestion.query.get_or_404(q_id)
    iq.is_published = False
    db.session.commit()
    flash('Important question unpublished successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_important_q/<int:q_id>', methods=['POST'])
@login_required
def delete_important_q(q_id):
    if not current_user.is_admin:                                           
        return redirect(url_for('login'))

    iq = ImportantQuestion.query.get_or_404(q_id)
    db.session.delete(iq)
    db.session.commit()
    flash('Important question deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_quiz', methods=['POST'])
@login_required
def add_quiz():
    if not current_user.is_admin:
        return redirect(url_for('login'))

    question_text = request.form.get('question_text')
    option1 = request.form.get('option1')
    option2 = request.form.get('option2')
    option3 = request.form.get('option3')
    option4 = request.form.get('option4')
    correct_option = request.form.get('correct_option')

    if question_text and option1 and option2 and option3 and option4 and correct_option:
        new_q = QuizQuestion(
            question_text=question_text,
            option1=option1,
            option2=option2,
            option3=option3,
            option4=option4,                                                
            correct_option=correct_option,
            is_published=False
        )
        db.session.add(new_q)
        db.session.commit()
        flash('Exam question added as draft successfully!', 'success')

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/publish_quiz', methods=['POST'])
@login_required
def publish_quiz():
    if not current_user.is_admin:
        return redirect(url_for('login'))
    QuizQuestion.query.update({QuizQuestion.is_published: True})
    db.session.commit()
    flash('All exam questions have been successfully published for students!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/unpublish_quiz', methods=['POST'])
@login_required
def unpublish_quiz():
    if not current_user.is_admin:
        return redirect(url_for('login'))

    QuizQuestion.query.update({QuizQuestion.is_published: False})
    db.session.commit()
    flash('Exam unpublished successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_quiz/<int:quiz_id>', methods=['POST'])
@login_required
def delete_quiz(quiz_id):                                                   
    if not current_user.is_admin:
        return redirect(url_for('login'))

    q = QuizQuestion.query.get_or_404(quiz_id)
    db.session.delete(q)
    db.session.commit()
    flash('Exam question deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_all_quiz', methods=['POST'])
@login_required
def delete_all_quiz():
    if not current_user.is_admin:                                           
        return redirect(url_for('login'))

    QuizQuestion.query.delete()
    User.query.update({User.has_given_exam: False, User.exam_score: None})
    db.session.commit()
    flash('All exam questions deleted and student exam status reset successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/questions', methods=['GET', 'POST'])
@login_required
def questions():
    if request.method == 'POST':
        current_user.ans1 = request.form.get('ans1')
        current_user.ans2 = request.form.get('ans2')
        current_user.ans3 = request.form.get('ans3')
        current_user.ans4 = request.form.get('ans4')
        current_user.is_questions_submitted = True
        db.session.commit()
        return redirect(url_for('profile'))

    return render_template('questions.html')

@app.route('/edit-profile')
@login_required
def edit_profile():
    return redirect(url_for('questions'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if not current_user.is_questions_submitted:
        return redirect(url_for('questions'))

    if request.method == 'POST':
        text_note = request.form.get('text_note')
        file = request.files.get('file')
        saved_file_path = None

        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            saved_file_path = f"uploads/{filename}"

        if text_note or saved_file_path:
            new_entry = UserData(text_content=text_note, file_path=saved_file_path, user_id=current_user.id)
            db.session.add(new_entry)
            db.session.commit()

    user_data = UserData.query.filter_by(user_id=current_user.id).all()
    notices_list = Notice.query.order_by(Notice.id.desc()).all()
    return render_template('dashboard.html', user_data=user_data, notices=notices_list)

@app.route('/important-questions')
@login_required
def important_questions():
    if not current_user.is_questions_submitted:
        return redirect(url_for('questions'))
    questions_list = ImportantQuestion.query.filter_by(is_published=True).all()
    return render_template('important_questions.html', important_questions=questions_list)

@app.route('/nss-exam', methods=['GET', 'POST'])
@login_required
def nss_exam():
    if not current_user.is_questions_submitted:
        return redirect(url_for('questions'))

    questions_list = QuizQuestion.query.filter_by(is_published=True).all()
    total_q = len(questions_list)

    if current_user.has_given_exam:
        return render_template('nss_exam.html', questions=[], score=current_user.exam_score, submitted=True, already_submitted=True)

    if request.method == 'POST':
        correct_count = 0
        for q in questions_list:
            user_ans = request.form.get(f'question_{q.id}')
            if user_ans == q.correct_option:
                correct_count += 1

        score_str = f"{correct_count} / {total_q}"
        current_user.has_given_exam = True
        current_user.exam_score = score_str
        db.session.commit()
                                                                            
        return render_template('nss_exam.html', questions=[], score=score_str, submitted=True, already_submitted=True)

    return render_template('nss_exam.html', questions=questions_list, submitted=False)

@app.route('/student/profile')
@login_required
def student_profile():
    if not current_user.is_questions_submitted:
        return redirect(url_for('questions'))
    return render_template('profile.html')

@app.route('/forgot', methods=['GET', 'POST'])
def forgot():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            otp = random.randint(100000, 999999)
            session['reset_otp'] = str(otp)
            session['reset_email'] = email
            msg = Message('OTP for Password Reset', sender=app.config['MAIL_USERNAME'], recipients=[email])
            msg.body = f'Your OTP is: {otp}'                                
            
            # Background Thread जोड़ दिया गया है ताकि सर्वर क्रैश न हो
            threading.Thread(target=send_async_email, args=(app, msg)).start()
            
            flash('OTP has been sent to your email!', 'success')
            return redirect(url_for('reset_password'))
        else:
            flash('यह ईमेल हमारे डेटाबेस में रजिस्टर नहीं है!', 'danger')
    return render_template('forgot.html')

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        if request.form.get('otp') == session.get('reset_otp'):
            email = session.get('reset_email')
            user = User.query.filter_by(email=email).first()
            if user:
                user.password = generate_password_hash(request.form.get('new_password'), method='scrypt')
                db.session.commit()
                flash('Password reset successfully! Please login.', 'success')
                return redirect(url_for('login'))
        else:
            flash('Invalid OTP!', 'danger')
    return render_template('reset_password.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

def create_default_admin():
    admin_email = "admin@gmail.com"
    admin = User.query.filter_by(email=admin_email).first()
    if not admin:
        hashed_pw = generate_password_hash("admin123", method='scrypt')
        default_admin = User(
            email=admin_email,
            password=hashed_pw,
            is_admin=True,
            is_questions_submitted=True
        )
        db.session.add(default_admin)
        db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_default_admin()
    app.run(host='0.0.0.0', port=5000, debug=True)
