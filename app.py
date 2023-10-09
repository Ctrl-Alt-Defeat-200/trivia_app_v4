# app.py
from flask import Flask, render_template, request, url_for, redirect, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
import uuid


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///db.sqlite"
app.config["SECRET_KEY"] = "abc"
db = SQLAlchemy()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  # type:ignore

# Models
#--------------------------------------------------------------------------------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(length=120), nullable=False)
    is_active = db.Column(db.Boolean, default=True)  # Add the 'is_active' attribute

    def get_id(self):
        return str(self.id)

    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.password = password
        
class TriviaSet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    set_title = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    difficulty = db.Column(db.String(50), nullable=False)
    questions = db.relationship('Question', backref='trivia_set')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Add the following line to establish a relationship with the User model
    creator = db.relationship('User', backref='created_trivia_sets')

    # Add a new field for a unique trivia_set_id
    trivia_set_id = db.Column(db.String(50), unique=True, nullable=False)

    def __init__(self, set_title, category, difficulty, user_id, trivia_set_id):
        self.set_title = set_title
        self.category = category
        self.difficulty = difficulty
        self.user_id = user_id
        self.trivia_set_id = trivia_set_id



class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_text = db.Column(db.String(255), nullable=False)
    question_type = db.Column(db.Enum('multiple_choice', 'open_ended'), nullable=False)
    
    # Define a one-to-many relationship for options if it's a multiple choice question
    options = db.relationship('Option', backref='question', lazy=True, uselist=True)
    trivia_set_id = db.Column(db.Integer, db.ForeignKey('trivia_set.id'), nullable=False)
    def __init__(self, question_text, question_type):
        self.question_text = question_text
        self.question_type = question_type

class Option(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(255), nullable=False)
    is_correct = db.Column(db.Boolean, default=False, nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)

    def __init__(self, text, is_correct=False):
        self.text = text
        self.is_correct = is_correct

class UserScore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    trivia_set_id = db.Column(db.Integer, db.ForeignKey('trivia_set.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)

    def __init__(self, id, trivia_set_id, score):
        self.id=id
        self.trivia_set_id=trivia_set_id
        self.score=score
#--------------------------------------------------------------------------------------

db.init_app(app)


@login_manager.user_loader
def loader_user(user_id):
	return db.session.query(User).get(user_id)


# Routes
#--------------------------------------------------------------------------------------
@app.route("/")
def home():
	return render_template("index.html")

@app.route('/dashboard')
@login_required  # only logged-in users can access this route
def dashboard():
    if isinstance(current_user, UserMixin) and current_user.is_authenticated:
        # Query the user's trivia sets from the database
        user_trivia_sets = TriviaSet.query.filter_by(user_id=current_user.id).all() # type: ignore
        
        return render_template("dashboard.html", current_user=current_user, user_trivia_sets=user_trivia_sets)
    else:
        print('User is not authenticated')
        return redirect(url_for('login'))

@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email")
        username = request.form.get("username")
        password = request.form.get("password")

        existing_user = User.query.filter_by(email=email).first() or User.query.filter_by(username=username).first()

        if existing_user:
            return "Email or username already in use"

        new_user = User(email=email, username=username, password=password)
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)

        return redirect(url_for("dashboard"))

    return render_template("register.html")


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter((User.email == email) | (User.username == username)).first()
        
        if user:
            print('Login successful')
            print(f'Email: {email}')
            print(f'Username: {username}')
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials", "error")

    return render_template("login.html")


@app.route('/create_trivia_set', methods=['GET', 'POST'])
@login_required
def create_trivia_set():
    if request.method == 'POST':
        set_title = request.form.get('set_title')
        category = request.form.get('category')
        difficulty = request.form.get('difficulty')

        # Add validation for required fields
        if not set_title or not category or not difficulty:
            flash("Please fill in all required fields.", "error")
            return redirect(url_for('create_trivia_set'))

        # Create a new trivia set associated with the current user
        if isinstance(current_user, User):
            
            new_trivia_set_id = str(uuid.uuid4())
            
            new_trivia_set = TriviaSet(
                set_title=set_title,
                category=category,
                difficulty=difficulty,
                user_id=current_user.id,
                trivia_set_id=new_trivia_set_id
            )

            db.session.add(new_trivia_set)
            db.session.commit()

            question_index = 0  # Counter for questions

            while True:
                question_text_key = f'questions_{question_index}_text'
                question_type_key = f'questions_{question_index}_type'
                question_text = request.form.get(question_text_key)
                question_type = request.form.get(question_type_key)

                if not question_text:
                    break  # No more questions

                new_question = Question(question_text=question_text, question_type=question_type)
                new_trivia_set.questions.append(new_question)
                db.session.add(new_question)
                db.session.commit()

                if question_type == 'multiple_choice':
                    option_index = 0  # Counter for options

                    while True:
                        option_text_key = f'options_{question_index}_{option_index}_text'
                        option_is_correct_key = f'options_{question_index}_{option_index}_is_correct'
                        
                        option_text = request.form.get(option_text_key)
                        option_is_correct = request.form.get(option_is_correct_key)

                        if not option_text:
                            break  # No more options for this question

                        new_option = Option(
                            text=option_text,
                            is_correct=(option_is_correct == 'on'),
                        )
                        new_question.options.append(new_option)
                        db.session.add(new_option)
                        db.session.commit()

                        option_index += 1

                elif question_type == 'open_ended':
                    open_ended_answer_key = f'open_ended_{question_index}_text'
                    open_ended_answer = request.form.get(open_ended_answer_key)

                    if open_ended_answer:
                        # Only create an option for open-ended questions if the answer exists
                        new_option = Option(
                            text=open_ended_answer,
                            is_correct=True,
                            question_id=new_question.id # type:ignore
                        )
                        new_question.options.append(new_option)
                        db.session.add(new_option)
                        db.session.commit()

                question_index += 1

            return redirect(url_for('dashboard'))

    return render_template('create_trivia_set.html')

@app.route('/edit_trivia_set/<trivia_set_id>', methods=['GET', 'POST'])
@login_required
def edit_trivia_set(trivia_set_id):
    # Retrieve the trivia set based on the trivia_set_id
    trivia_set = TriviaSet.query.filter_by(trivia_set_id=trivia_set_id).first()

    if trivia_set:
        # Check if the current user is the creator of the trivia set
        if current_user.id == trivia_set.user_id: # type:ignore
            
            if request.method == 'POST':
                # Handle the form submission for editing the trivia set
                # Update the trivia set's properties as needed
                trivia_set.set_title = request.form.get('set_title')
                trivia_set.category = request.form.get('category')
                trivia_set.difficulty = request.form.get('difficulty')
                
                # Update the trivia set's questions and options
                updated_questions = []

                for i, question in enumerate(trivia_set.questions):
                    question_text_key = f'questions_{i}_text'
                    question_text = request.form.get(question_text_key)
                    question.question_text = question_text

                    # Update question options
                    updated_options = []

                    for j, option in enumerate(question.options):
                        option_text_key = f'options_{i}_{j}_text'
                        option_is_correct_key = f'options_{i}_{j}_is_correct'

                        option_text = request.form.get(option_text_key)
                        is_correct = request.form.get(option_is_correct_key)

                        new_option = Option(
                            text=option_text,
                            is_correct=(is_correct == 'on'),
                        )
                        updated_options.append(new_option)

                    question.options = updated_options
                    updated_questions.append(question)

                trivia_set.questions = updated_questions
                db.session.commit()
                
                # Redirect to the dashboard or the edited trivia set's page
                return redirect(url_for('dashboard'))
            
            # Render the edit trivia set form
            return render_template('edit_trivia_set.html', trivia_set=trivia_set)
        else:
            # The current user is not the creator of the trivia set, so they can't edit it
            flash("You do not have permission to edit this trivia set.", "error")
            return redirect(url_for('dashboard'))
    else:
        # Trivia set with the given trivia_set_id does not exist
        return "Trivia set not found", 404


@app.route('/delete_trivia_set/<trivia_set_id>', methods=['POST'])
@login_required
def delete_trivia_set(trivia_set_id):
    # Retrieve the trivia set based on the trivia_set_id
    trivia_set = TriviaSet.query.filter_by(trivia_set_id=trivia_set_id).first()

    if trivia_set:
        # Check if the current user is the creator of the trivia set
        if current_user.id == trivia_set.user_id: # type:ignore
            # Delete associated questions first
            for question in trivia_set.questions:
                db.session.delete(question)
            # Delete the trivia set and commit to db
            db.session.delete(trivia_set)
            db.session.commit()
            
            # Redirect to the dashboard or another appropriate page
            return redirect(url_for('dashboard'))
        else:
            # The current user is not the creator of the trivia set, so they can't delete it
            flash("You do not have permission to delete this trivia set.", "error")
            return redirect(url_for('dashboard'))
    else:
        # Trivia set with the given trivia_set_id does not exist
        return "Trivia set not found", 404



@app.route("/logout")
@login_required # only logged-in users can access this route
def logout():
	logout_user()
	return redirect(url_for("home"))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
