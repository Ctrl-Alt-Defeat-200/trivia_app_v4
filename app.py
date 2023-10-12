# app.py
from flask import Flask, render_template, request, url_for, redirect, session, flash
from flask_sqlalchemy import SQLAlchemy 
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from sqlalchemy import or_
from flask_migrate import Migrate
from flask_caching import Cache
import uuid

# Configure app
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///db.sqlite"
app.config["SECRET_KEY"] = "abc"
db = SQLAlchemy()

# Configure migration
migrate = Migrate(app, db, render_as_batch=True)

#Configure caching
app.config['CACHE_TYPE'] = 'simple'
app.config['CACHE_DEFAULT_TIMEOUT'] = 300   #seconds
cache = Cache(app)

#Configure login
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
    is_active = db.Column(db.Boolean, default=True, nullable=False)

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
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    trivia_set_id = db.Column(db.String(50), unique=True, nullable=False)

    questions = db.relationship('Question', backref='trivia_set', lazy='dynamic')

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
    trivia_set_id = db.Column(db.Integer, db.ForeignKey('trivia_set.id'), nullable=False)

    options = db.relationship('Option', backref='question', lazy='dynamic')

    def __init__(self, question_text, question_type, trivia_set_id):
        self.question_text = question_text
        self.question_type = question_type
        self.trivia_set_id = trivia_set_id


class Option(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(255), nullable=False)
    is_correct = db.Column(db.Boolean, default=False, nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)

    def __init__(self, text, question_id, is_correct=False):
        self.text = text
        self.is_correct = is_correct
        self.question_id = question_id


class UserScore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    trivia_set_id = db.Column(db.Integer, db.ForeignKey('trivia_set.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)

    def __init__(self, user_id, trivia_set_id, score):
        self.user_id = user_id
        self.trivia_set_id = trivia_set_id
        self.score = score




def generate_unique_id():
    return str(uuid.uuid4())



def calculate_score(trivia_set, user_answers):
    score = 0
    for question in trivia_set.questions:
        correct_option_id = None

        for option in question.options:
            if option.is_correct:
                correct_option_id = option.id
                break

        user_answer = user_answers.get(question.id)
        if user_answer and user_answer == str(correct_option_id):
            score += 1

    return score


@cache.memoize()
def get_top_scores(userId):
    player = User.query.get(userId)
    if player is None:
        return None
    
    scores = (
        db.session.query(UserScore.score, UserScore.trivia_set_id, TriviaSet.set_title)
        .join(TriviaSet, UserScore.trivia_set_id == TriviaSet.id)
        .filter(UserScore.user_id == userId)
        .order_by(UserScore.score.desc())
        .limit(3)
        .all()
    )
    
    top_scores = [(str(score.score), str(score.trivia_set_id), score.set_title) for score in scores]
    
    return top_scores


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



@app.route('/print_database')
@login_required
def print_database():

        trivia_sets = TriviaSet.query.all()


        for set in trivia_sets:
            print(f"Set Title: {set.set_title}")
            print(f"Category: {set.category}")
            print(f"Difficulty: {set.difficulty}")

            for question in set.questions:
                print(f"Question: {question.question_text}")
                print(f"Question Type: {question.question_type}")

                for option in question.options:
                    print(f"Option: {option.text}")
                    print(f"Is Correct: {option.is_correct}")

                correct_option = next((opt for opt in question.options if opt.is_correct), None)
                if correct_option:
                    print(f"Correct Answer: {correct_option.text}")


            print("\n")


        return "Database contents printed in the terminal."



@app.route('/dashboard')
@login_required  # only logged-in users can access this route
def dashboard():
    if isinstance(current_user, UserMixin) and current_user.is_authenticated:
        # Query the user's trivia sets from the database
        user_trivia_sets = TriviaSet.query.filter_by(user_id=current_user.id).all() # type: ignore
        user_top_scores = get_top_scores(current_user.id)
        #print(user_top_scores)
        return render_template("dashboard.html", current_user=current_user, user_trivia_sets=user_trivia_sets, user_top_scores=user_top_scores)
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
        user_id = current_user.id  # type:ignore

        trivia_set_id = generate_unique_id()

        trivia_set = TriviaSet(set_title=set_title, category=category, difficulty=difficulty, user_id=user_id, trivia_set_id=trivia_set_id)
        db.session.add(trivia_set)
        db.session.commit()

        # Process and save questions and options
        for question_num in range(1, 11):
            question_text = request.form.get(f'question_{question_num}')
            options = request.form.getlist(f'question_{question_num}_options[]')
            correct_option = int(request.form.get(f'correct_option_{question_num}')) # type:ignore

            # Create a new question associated with the trivia set
            question = Question(question_text=question_text, question_type='multiple_choice', trivia_set_id=trivia_set.id)
            db.session.add(question)
            db.session.commit()

            # Create options for the question
            for option_num, option_text in enumerate(options, start=1):
                is_correct = (option_num == correct_option)
                option = Option(text=option_text, is_correct=is_correct, question_id=question.id)
                db.session.add(option)
                db.session.commit()

        flash('Trivia set created successfully', 'success')
        return redirect(url_for('dashboard'))

    return render_template('create_trivia_set.html')




@app.route('/edit_trivia_set/<trivia_set_id>', methods=['GET', 'POST'])
@login_required
def edit_trivia_set(trivia_set_id):
    # Fetch the trivia set from the database
    trivia_set = TriviaSet.query.filter_by(trivia_set_id=trivia_set_id).first()

    # Check if the logged-in user is the owner of the trivia set
    if trivia_set is None:
        flash("Trivia set not found.", "error")
        return redirect(url_for('dashboard'))

    if trivia_set.user_id != current_user.id: #type:ignore
        flash("You do not have permission to edit this trivia set.", "error")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        # Get the updated data from the form submission
        set_title = request.form.get('set_title')
        category = request.form.get('category')
        difficulty = request.form.get('difficulty')

        # Update the trivia set data
        trivia_set.set_title = set_title
        trivia_set.category = category
        trivia_set.difficulty = difficulty

        # Update questions and options
        for question_num in range(1, 11):
            question_text = request.form.get(f'questions_{question_num}_text')
            question = trivia_set.questions[question_num - 1]

            if question_text:
                question.question_text = question_text

            for option_num in range(1, 5):
                option_text = request.form.get(f'options_{question_num}_{option_num}_text')
                option = question.options[option_num - 1]

                if option_text is not None:
                    option.text = option_text

                # Check if this option is the correct one based on the selected radio button
                is_correct = (request.form.get(f'correct_option_{question_num}') == str(option_num))
                option.is_correct = is_correct


        # Commit changes to the database
        db.session.commit()

        flash('Trivia set updated successfully', 'success')
        return redirect(url_for('dashboard'))

    return render_template('edit_trivia_set.html', trivia_set=trivia_set)



@app.route('/update_trivia_set/<trivia_set_id>', methods=['POST'])
@login_required
def update_trivia_set(trivia_set_id):
    # Fetch the trivia set from the database
    trivia_set = TriviaSet.query.filter_by(trivia_set_id=trivia_set_id).first()

    # Check if the trivia set exists
    if not trivia_set:
        flash("Trivia set not found.", "error")
        return redirect(url_for('dashboard'))

    # Check if the logged-in user is the owner of the trivia set
    if trivia_set.user_id != current_user.id: # type:ignore

        flash("You do not have permission to update this trivia set.", "error")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        # Get the updated data from the form submission
        set_title = request.form.get('set_title')
        category = request.form.get('category')
        difficulty = request.form.get('difficulty')

        # Update the trivia set data
        trivia_set.set_title = set_title
        trivia_set.category = category
        trivia_set.difficulty = difficulty

        # Update questions and options
        for question_num in range(1, 11):
            question_text = request.form.get(f'question_{question_num}')
            options = request.form.getlist(f'question_{question_num}_options[]')
            correct_option = int(request.form.get(f'correct_option_{question_num}')) # type:ignore

            # Check if the question exists before updating
            if len(trivia_set.questions) >= question_num:
                question = trivia_set.questions[question_num - 1]
                question.question_text = question_text

                # Update options for the question
                for option_num, option_text in enumerate(options, start=1):
                    is_correct = (option_num == correct_option)

                    # Check if the option exists before updating
                    if len(question.options) >= option_num:
                        option = question.options[option_num - 1]
                        option.text = option_text
                        option.is_correct = is_correct

        # Commit changes to the database
        db.session.commit()

        flash('Trivia set updated successfully', 'success')
        return redirect(url_for('dashboard'))

    return redirect(url_for('dashboard'))  # Redirect to dashboard if it's not a POST request



@app.route('/submit_trivia_set/<trivia_set_id>', methods=['POST'])
@login_required
def submit_trivia_set(trivia_set_id):
    # Fetch the trivia set from the database
    trivia_set = TriviaSet.query.filter_by(trivia_set_id=trivia_set_id).first()

    # Check if the trivia set exists
    if not trivia_set:
        flash("Trivia set not found.", "error")
        return redirect(url_for('dashboard'))

    # Get user's answers from the form submission
    user_answers = {}
    for question in trivia_set.questions:
        answer_key = f"answer_{question.id}"
        user_answers[question.id] = request.form.get(answer_key)

    # Calculate the user's score
    score = calculate_score(trivia_set, user_answers)

    # Update the user's score in the database
    user_score = UserScore.query.filter_by(
        user_id=current_user.id, trivia_set_id=trivia_set.id).first() # type:ignore

    if not user_score:
        # If no previous score exists, create a new entry
        user_score = UserScore(
        user_id=current_user.id, trivia_set_id=trivia_set.id, score=score) # type:ignore
        db.session.add(user_score)
    else:
        # Update the existing score
        user_score.score = score

    db.session.commit()

    # Render the results HTML template
    return render_template('trivia_results.html', trivia_set=trivia_set, user_score=score)



@app.route('/delete_trivia_set/<trivia_set_id>', methods=['POST'])
@login_required
def delete_trivia_set(trivia_set_id):

    trivia_set = TriviaSet.query.filter_by(trivia_set_id=trivia_set_id).first()

    if trivia_set:

        if current_user.id == trivia_set.user_id:  # type:ignore
            # delete associated questions first!!! important
            for question in trivia_set.questions:
                db.session.delete(question)
            # Delete the trivia set and commit to db
            db.session.delete(trivia_set)
            db.session.commit()

            return redirect(url_for('dashboard'))
        else:
            flash("You do not have permission to delete this trivia set.", "error")
            return redirect(url_for('dashboard'))
    else:
        return "Trivia set not found", 404


# Route to display results after the user submits their answers
@app.route('/results/<int:set_id>')
def results(set_id):
    trivia_set = TriviaSet.query.get(set_id)
    # Fetch the user's score for the specified trivia set from the database
    # You can query the UserScore table based on the set_id and the current user's ID
    # Assuming you have the necessary imports and database setup
    user_score = UserScore.query.filter_by(trivia_set_id=set_id, user_id=current_user.id).first()

    return render_template('results.html', trivia_set=trivia_set, user_score=user_score)

@app.route('/play_set/<int:set_id>', methods=['GET', 'POST'])
@login_required
def play_set(set_id):
    trivia_set = TriviaSet.query.get(set_id)
    if not trivia_set:
        flash('Trivia set not found', 'danger')
        return redirect(url_for('dashboard'))  # Redirect to a dashboard page or another route

    if request.method == 'POST':
        score = 0
        for question_id, selected_option_id in request.form.items():
            question = Question.query.get(question_id)
            selected_option = Option.query.get(selected_option_id)

            if question and selected_option:
                if selected_option.is_correct:
                    score += 1

        user_score = UserScore(user_id=current_user.id, trivia_set_id=set_id, score=score)
        db.session.add(user_score)
        db.session.commit()
        flash(f'Your score: {score}', 'success')
        return redirect(url_for('results', set_id=set_id))  # Redirect to a dashboard page or another route

    questions = trivia_set.questions.all()
    return render_template('play_set.html', trivia_set=trivia_set, questions=questions)


@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        # Get the search term from the form
        search_term = request.form.get('search_term', '')

        # Query trivia sets matching the search term in 'set_title' or 'category'
        trivia_sets = TriviaSet.query.filter(
            or_(TriviaSet.set_title.ilike(f"%{search_term}%"), TriviaSet.category.ilike(f"%{search_term}%"))
        ).all()

        return render_template('search.html', trivia_sets=trivia_sets, search_term=search_term)

    return render_template('search.html')



@app.route("/logout")
@login_required # only logged-in users can access this route
def logout():
	logout_user()
	return redirect(url_for("home"))



if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0')
