# =============== IMPORTING REQUIRED LIBRARIES ===================

from flask import Flask , render_template , redirect , session , request , url_for
import time 
from flask_sqlalchemy import SQLAlchemy
import json
from datetime import datetime
import os
from werkzeug.utils import secure_filename

# =================== DONE =======================================

app = Flask(__name__)

# -------------------- SECRET KEY -----------------------------
app.secret_key = 'secret_key_for_session'

# -------------------- DATABASE CONFIGURATION (FIXED!) -------------------
# Get database URL from environment variable (Render sets this automatically)
database_url = os.environ.get('DATABASE_URL')

# Fix for SQLAlchemy (Render uses 'postgres://' but SQLAlchemy needs 'postgresql://')
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

# Use PostgreSQL in production, SQLite for local development
app.config["SQLALCHEMY_DATABASE_URI"] = database_url or "sqlite:///quiz.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# -------------------- UPLOAD CONFIG --------------------------
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



#----------------------------- MODELS -----------------------------
class User(db.Model):
    id = db.Column(db.Integer , primary_key = True)
    username = db.Column(db.String(50) , nullable = False , unique=True)
    password = db.Column(db.Integer , unique = True , nullable = False)
    fullname = db.Column(db.String(50) , nullable = False)
    dob = db.Column(db.Date , nullable = False)

class Admin(db.Model):
    id = db.Column(db.Integer , primary_key = True)
    username = db.Column(db.String(100) , nullable = False)
    password = db.Column(db.Integer , nullable = False , unique = True)

class Quiz(db.Model):
    id = db.Column(db.Integer , primary_key= True)
    title = db.Column(db.String(100) , nullable = False)
    chapters = db.relationship('Chapter' , backref = 'quiz' , lazy = True)

class Chapter(db.Model):
    id = db.Column(db.Integer , primary_key = True)
    title = db.Column(db.String(50) , nullable = False)
    quiz_id = db.Column(db.Integer , db.ForeignKey('quiz.id') , nullable = False)




class Question(db.Model):
    id = db.Column(db.Integer , primary_key = True)
    quiz_id = db.Column(db.Integer , db.ForeignKey('quiz.id') , nullable = False)
    chapter_id = db.Column(db.Integer , db.ForeignKey('chapter.id') , nullable = False)

    question_statement = db.Column(db.Text , nullable = True)
    question_image = db.Column(db.String(100), nullable=True)

    option_1 = db.Column(db.String(50) , nullable = False)
    option_2 = db.Column(db.String(50) , nullable = False)
    option_3 = db.Column(db.String(50) , nullable = False)
    option_4 = db.Column(db.String(50) , nullable = False)

    correct_option = db.Column(db.Integer , nullable = False)
    explanation = db.Column(db.Text, nullable=True)

    quiz = db.relationship('Quiz' , backref='questions')
    chapter = db.relationship('Chapter' , backref='questions')


class QuizAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id'), nullable=True)
    score = db.Column(db.Integer, nullable=True)
    answers = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='quiz_attempts')
    quiz = db.relationship('Quiz', backref='attempts')
    chapter = db.relationship('Chapter', backref='attempts')

# ===================== ROUTES ================================

@app.route('/')
def home():
    return render_template('index.html')

# ---------------- USER REGISTER ----------------
@app.route('/user/register' , methods = ['GET' , 'POST'])
def user_register():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        fullname = request.form['fullname']
        dob = request.form['dob']
        
        if User.query.filter_by(username = username).first():
            return render_template('user_register.html' , error = 'Username Already Exists!')

        dob = datetime.strptime(dob, "%Y-%m-%d").date()
        
        user = User(username=username , password=password , fullname=fullname , dob=dob)
        db.session.add(user)
        db.session.commit()  
        return redirect('/user/login')
    
    return render_template('user_register.html')

# ---------------- USER LOGIN ----------------
@app.route('/user/login' , methods = ['GET' , 'POST'])
def user_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username , password=password).first()

        if user:
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect('/user/dashboard')

        return render_template('user_login.html' , error = 'Invalid Details!')
    return render_template('user_login.html')

# ---------------- FORGOT PASSWORD ----------------
@app.route('/user/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == "POST":
        username = request.form['username']
        dob = request.form['dob']

        user = User.query.filter_by(username=username).first()
        if user and str(user.dob) == dob:
            session['reset_user_id'] = user.id
            return redirect(url_for('reset_password'))
        else:
            return render_template('forgot_password.html', error="Invalid details!")
    return render_template('forgot_password.html')

# ---------------- RESET PASSWORD ----------------
@app.route('/user/reset_password', methods=['GET', 'POST'])
def reset_password():
    if 'reset_user_id' not in session:
        return redirect(url_for('forgot_password'))

    if request.method == "POST":
        new_password = request.form['password']

        user = User.query.get(session['reset_user_id'])
        user.password = new_password
        db.session.commit()

        session.pop('reset_user_id', None)
        return redirect(url_for('user_login'))

    return render_template('reset_password.html')

# ---------------- ADMIN LOGIN ----------------
@app.route('/admin/login' , methods=['GET' , 'POST'])
def admin_login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        admin = Admin.query.filter_by(username = username, password = password).first()

        if admin:
            session['admin_id'] = admin.id
            session['admin_username'] = admin.username
            return redirect('/admin/dashboard')
        else:
            return render_template('admin_login.html', error = "Invalid Details!")
    return render_template('admin_login.html')

# ---------------- ADMIN DASHBOARD ----------------
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        redirect('/admin/login')

    search_query = request.args.get('search' ,'').strip().lower()

    if search_query:
        quizzes = Quiz.query.filter(Quiz.title.ilike(f'%{ search_query }%')).all()
    else:
        quizzes = Quiz.query.all()
        
    chapters = Chapter.query.filter(Chapter.quiz_id.in_([q.id for q in quizzes])).all()
    questions = Question.query.filter(Question.quiz_id.in_([q.id for q in quizzes])).all()

    return render_template('admin_dashboard.html' , quizzes=quizzes , chapters=chapters , questions=questions, search_query=search_query)

# ---------------- ABOUT / CONTACT ----------------
@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

# ---------------- USER DASHBOARD ----------------
@app.route('/user/dashboard', methods=['GET', 'POST'])
def user_dashboard():
    if 'user_id' not in session:
        return redirect('/user/login')
    
    search_query = request.args.get('search', '').strip().lower()

    chapters = Chapter.query.all()

    if search_query:
        quizzes = Quiz.query.filter(
            Quiz.title.ilike(f'%{ search_query }%') 
        ).all()
    else:
        quizzes = Quiz.query.all()


    attempts = QuizAttempt.query.filter_by(user_id=session['user_id']).order_by(QuizAttempt.timestamp.desc()).all()
    # 🔥 attach total questions to each attempt
    for attempt in attempts:
        if attempt.chapter:
            attempt.total_questions = len(attempt.chapter.questions)
        else:
            attempt.total_questions = 0

    
    # 🔥 Get all attempts for the logged-in user

    return render_template(
        'user_dashboard.html', 
        username=session.get('username'),
        quizzes=quizzes, 
        chapters=chapters, 
        search_query=search_query,
        attempts=attempts
    )

# ---------------- CHAPTER WISE QUIZ ----------------
@app.route('/chapter/wise/quiz/<int:quiz_id>/', methods=['GET'])
def chapter_wise_quiz(quiz_id):
    if 'user_id' not in session:
        return redirect('/user/login')
    
    quiz = Quiz.query.get(quiz_id)

    # Get search text from search box
    search_query = request.args.get("q")

    if search_query:
        # filter only chapters of this quiz whose title matches search
        chapters = Chapter.query.filter(
            Chapter.quiz_id == quiz_id,
            Chapter.title.ilike(f"%{search_query}%")
        ).all()
    else:
        # show all chapters if no search text
        chapters = Chapter.query.filter_by(quiz_id=quiz_id).all()

    return render_template('chapter_wise_quiz.html', quiz=quiz, chapters=chapters, search_query=search_query)




# ---------------- LEADERBOARD ----------------

@app.route('/leaderboard/<int:quiz_id>/<int:chapter_id>')
def leaderboard(quiz_id, chapter_id):
    if 'user_id' not in session:
        return redirect('/user/login')

    quiz = Quiz.query.get_or_404(quiz_id)
    chapter = Chapter.query.get_or_404(chapter_id)

    # ✅ ONLY same quiz + same chapter
    top_attempts = QuizAttempt.query.filter_by(
        quiz_id=quiz_id,
        chapter_id=chapter_id
    ).order_by(
        QuizAttempt.score.desc(),
        QuizAttempt.timestamp.asc()
    ).limit(10).all()

    current_user_id = session.get('user_id')

    return render_template(
        'leaderboard.html',
        quiz=quiz,
        chapter=chapter,
        top_attempts=top_attempts,
        current_user_id=current_user_id
    )



# ---------------- ANSWER KEY ----------------
@app.route('/user/answer_key/<int:attempt_id>')
def answer_key(attempt_id):
    if 'user_id' not in session:
        return redirect('/user/login')

    attempt = QuizAttempt.query.get_or_404(attempt_id)

    if attempt.user_id != session.get('user_id'):
        return "Not authorized", 403

    # Load questions
    if attempt.chapter_id:
        questions_query = Question.query.filter_by(chapter_id=attempt.chapter_id).all()
    else:
        questions_query = Question.query.filter_by(quiz_id=attempt.quiz_id).all()

    # Parse stored answers
    user_answers = {}
    if attempt.answers:
        raw = json.loads(attempt.answers)
        user_answers = {int(k): v for k, v in raw.items()}

    total = len(questions_query)
    correct = 0
    wrong = 0
    unattempted = 0

    detailed_questions = []

    for q in questions_query:
        selected = user_answers.get(q.id)

        if selected is None:
            unattempted += 1
        elif selected == q.correct_option:
            correct += 1
        else:
            wrong += 1


        detailed_questions.append({
            "id": q.id,
            "question_statement": q.question_statement,
            "question_image": q.question_image,
            "options": [q.option_1, q.option_2, q.option_3, q.option_4],
            "correct_option": q.correct_option,
            "selected": selected,
            "explanation": q.explanation
        })


    # ACCURACY CALCULATION
    accuracy = round((correct / total) * 100, 2) if total else 0

    # PERFORMANCE MESSAGE LOGIC
    if accuracy < 30:
        performance_msg = "Very Poor 😟 – You need serious improvement in this chapter."
        performance_class = "danger"
    elif accuracy < 50:
        performance_msg = "Poor 😐 – Focus more on this chapter."
        performance_class = "warning"
    elif accuracy < 70:
        performance_msg = "Average 🙂 – You can do better with practice."
        performance_class = "secondary"
    elif accuracy < 80:
        performance_msg = "Good 👍 – Keep improving!"
        performance_class = "info"
    elif accuracy < 90:
        performance_msg = "Excellent 🌟 – Strong understanding!"
        performance_class = "success"
    else:
        performance_msg = "Outstanding 🔥 – You have mastered this topic!"
        performance_class = "success"

    return render_template(
        'quiz_analysis.html',
        quiz=attempt.quiz,
        chapter=attempt.chapter,
        total=total,
        correct=correct,
        wrong=wrong,
        unattempted=unattempted,
        accuracy=accuracy,
        questions=detailed_questions,
        user_answers=user_answers,
        attempt=attempt,
        performance_msg=performance_msg,
        performance_class=performance_class
    )

# ---------------- USER PROFILE ----------------
@app.route('/user/profile/')
def user_profile():
    if 'user_id' not in session:
        return redirect('/user/login')
    
    user_id = session['user_id']
    user = User.query.get_or_404(user_id)
        
    return render_template('user_profile.html' , user=user)

# ---------------- ADMIN USERS LIST ----------------
@app.route('/admin/users')
def admin_users():
    if 'admin_id' not in session:
        return redirect('/admin/login')

    all_attempts_data = []
    users = User.query.all()
    for user in users:
        attempts = QuizAttempt.query.filter_by(user_id=user.id).order_by(QuizAttempt.timestamp.asc()).all()
        if attempts:
            for attempt in attempts:
                chapter_title = attempt.chapter.title if attempt.chapter else "N/A"
                total_questions = len(attempt.chapter.questions) if attempt.chapter else len(attempt.quiz.questions)
                score_text = f"{attempt.score}/{total_questions}"

                all_attempts_data.append({
                    "username": user.username,
                    "fullname": user.fullname,
                    "dob": user.dob.strftime("%Y-%m-%d"),
                    "password" : user.password,
                    "quiz_title": attempt.quiz.title,
                    "chapter_title": chapter_title,
                    "score": score_text,
                    "date": attempt.timestamp.strftime("%Y-%m-%d %H:%M")
                })
        else:
            all_attempts_data.append({
                "username": user.username,
                "fullname": user.fullname,
                "dob": user.dob.strftime("%Y-%m-%d"),
                "password" : user.password,
                "quiz_title": "N/A",
                "chapter_title": "N/A",
                "score": "N/A",
                "date": "N/A"
            })
    return render_template('admin_users.html', attempts_data=all_attempts_data)

# ---------------- ADD QUIZ / CHAPTER / QUESTION ----------------
@app.route('/add/quiz' , methods = ['GET' , 'POST'])
def add_quiz():
    if 'admin_id' not in session:
        return redirect('/admin/login')
    
    if request.method == "POST":
        title = request.form['title']
        new_quiz = Quiz(title=title)
        db.session.add(new_quiz)
        db.session.commit()
        return redirect('/admin/dashboard')
    return render_template('add_quiz.html')

@app.route('/add/chapter/<int:quiz_id>' , methods = ['GET' , 'POST'])
def add_chapter(quiz_id):
    if 'admin_id' not in session :
        return redirect('/admin/login')
    
    quiz = Quiz.query.get_or_404(quiz_id)
    
    if request.method == "POST":
        title = request.form['title']
        new_chapter = Chapter(title = title , quiz_id=quiz.id)
        db.session.add(new_chapter)
        db.session.commit()
        return redirect('/admin/dashboard')
    return render_template('add_chapter.html' , quiz=quiz)


@app.route('/add/question/<int:quiz_id>/<int:chapter_id>', methods=['GET', 'POST'])
def add_question(quiz_id, chapter_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    quiz = Quiz.query.get_or_404(quiz_id)
    chapter = Chapter.query.get_or_404(chapter_id)

    if request.method == 'POST':
        question_text = request.form.get('name')
        option_1 = request.form.get('option_1')
        option_2 = request.form.get('option_2')
        option_3 = request.form.get('option_3')
        option_4 = request.form.get('option_4')
        correct_option = request.form.get('correct_option')

        file = request.files.get('question_image')
        filename = None
        if file and file.filename != "" and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        if question_text or filename:
            new_question = Question(
                quiz_id=quiz.id,
                chapter_id=chapter.id,
                question_statement=question_text,
                question_image=filename,
                option_1=option_1,
                option_2=option_2,
                option_3=option_3,
                option_4=option_4,
                correct_option=int(correct_option),
                explanation=request.form.get("explanation")
            )
            db.session.add(new_question)
            db.session.commit()
            return redirect('/admin/dashboard')

    return render_template('add_question.html', quiz=quiz, chapter=chapter)

# ---------------- TAKE QUIZ ----------------
@app.route('/take/quiz/<int:quiz_id>/<int:chapter_id>', methods=['GET', 'POST'])
def take_quiz(quiz_id, chapter_id):
    if 'user_id' not in session:
        return redirect('/user/login')

    quiz = Quiz.query.get_or_404(quiz_id)
    chapter = Chapter.query.get_or_404(chapter_id)
    questions_query = Question.query.filter_by(chapter_id=chapter.id).all()

    questions = []
    for q in questions_query:
        questions.append({
            "id": q.id,
            "question_statement": q.question_statement,
            "question_image": q.question_image,
            "option_1": q.option_1,
            "option_2": q.option_2,
            "option_3": q.option_3,
            "option_4": q.option_4,
            "correct_option": q.correct_option
        })

    session_key = f"quiz_end_{quiz.id}_{chapter.id}"
    total_seconds = len(questions) * 60

    if request.method == "POST":
        score = 0
        user_answers = {}

        for q in questions:
            ans = request.form.get(f'q{q["id"]}')
            user_answers[str(q["id"])] = int(ans) if ans else None
            if ans and int(ans) == q["correct_option"]:
                score += 1

        new_attempt = QuizAttempt(
            user_id=session['user_id'],
            quiz_id=quiz.id,
            chapter_id=chapter.id,
            score=score,
            answers=json.dumps(user_answers)
        )
        db.session.add(new_attempt)
        db.session.commit()
        session.pop(session_key, None)

        return render_template(
            'quiz_result.html',
            score=score,
            total=len(questions),
            quiz_id=quiz.id,
            attempt_id=new_attempt.id
        )

    if session_key not in session:
        session[session_key] = int(time.time()) + total_seconds

    return render_template(
        'take_quiz.html',
        quiz=quiz,
        chapter=chapter,
        questions=questions,
        quiz_end_time=session[session_key]
    )

# ---------------- USER LOGOUT ----------------
@app.route('/user/logout')
def user_logout():
    session.clear()
    return redirect('/')

# ---------------- ADMIN LOGOUT ----------------
@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect('/')




# ============  DELETE CHAPTER , QUESTION =========================


@app.route('/delete/quiz/<int:quiz_id>' , methods = ['GET' , 'POST'])
def delete_quiz(quiz_id):
    if 'admin_id' not in session:
        return redirect('/admin/login')
    
    quiz = Quiz.query.get_or_404(quiz_id)

    QuizAttempt.query.filter_by(quiz_id=quiz.id).delete()

    Chapter.query.filter_by(quiz_id=quiz.id).delete()
    Question.query.filter_by(quiz_id=quiz.id).delete()

    db.session.delete(quiz)
    db.session.commit()

    return redirect('/admin/dashboard')




@app.route('/delete/chapter/<int:chapter_id>' , methods=['GET' , 'POST'])
def delete_chapter(chapter_id):
    if 'admin_id' not in session:
        return redirect('/admin/login')
    
    chapter = Chapter.query.get_or_404(chapter_id)
    Question.query.filter_by(chapter_id=chapter.id).delete()

    db.session.delete(chapter)
    db.session.commit()

    return redirect('/admin/dashboard')





@app.route('/delete/question/<int:question_id>' , methods = ['GET' , 'POST'])
def delete_question(question_id):
    if 'admin_id' not in session:
        return redirect('/admin/login')
    
    question = Question.query.get_or_404(question_id)

    db.session.delete(question)
    db.session.commit()

    return redirect('/admin/dashboard')




# ========================== Edit Question Route ==========================

@app.route("/edit/question/<int:question_id>", methods=["GET", "POST"])
def edit_question(question_id):
    question = Question.query.get_or_404(question_id)

    if request.method == "POST":
        # Update text question
        question.explanation = request.form.get("explanation")
        question_text = request.form.get("quiz_name")
        if question_text:
            question.question_statement = question_text

        # Update options
        question.option_1 = request.form.get("option_1")
        question.option_2 = request.form.get("option_2")
        question.option_3 = request.form.get("option_3")
        question.option_4 = request.form.get("option_4")

        # Correct option
        correct_option = request.form.get("correct_option")
        if correct_option:
           question.correct_option = int(correct_option)

        file = request.files.get("question_image")
        if file and file.filename != "" and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            question.question_image = filename

          

        db.session.commit()
        return redirect("/admin/dashboard")

    # Render the form with existing values
    return render_template("edit_question.html", question=question)




# ===================== DEBUG ROUTE =====================
@app.route('/debug/db')
def debug_db():
    # Only allow access if admin is logged in
    if 'admin_id' not in session:
        return "Access denied! Login as admin to see debug info.", 403

    users = User.query.all()
    quizzes = Quiz.query.all()

    data = {
        "users": [{"id": u.id, "username": u.username, "fullname": u.fullname} for u in users],
        "quizzes": [{"id": q.id, "title": q.title} for q in quizzes]
    }

    return json.dumps(data, indent=4)

#---------------- MAIN ----------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not Admin.query.first():
            default_admin = Admin(username='admin', password='admin123')
            db.session.add(default_admin)
            db.session.commit()
    app.run(debug=True)


