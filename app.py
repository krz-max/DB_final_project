from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///your_database.db'  # 使用SQLite，你也可以選擇其他資料庫
app.jinja_env.add_extension('jinja2.ext.loopcontrols')
db = SQLAlchemy(app)
# db.init_app(app)

class Food(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)

class Nutrient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    food_id = db.Column(db.Integer, db.ForeignKey('food.id'), nullable=False)
    calories = db.Column(db.Integer, nullable=False)
    carbohydrates = db.Column(db.Float, nullable=False)
    protein = db.Column(db.Float, nullable=False)
    fat = db.Column(db.Float, nullable=False)

class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    calories_per_kg = db.Column(db.Float, nullable=False)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    weight = db.Column(db.Float, nullable=False)
    height = db.Column(db.Float, nullable=False)

class UserCaloriesRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow, nullable=False)
    calories_ingest = db.Column(db.Integer, nullable=False)

class UserExerciseRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow, nullable=False)
    activity_id = db.Column(db.Integer, db.ForeignKey('activity.id'), nullable=False)
    time = db.Column(db.Integer, nullable=False)
    calories_consumption = db.Column(db.Integer, nullable=False)


with app.app_context():
    # 建立資料庫表格
    db.create_all()

@app.route('/')
def index():
    items = User.query.all()
    return render_template('index.html', User=items)

@app.route('/add', methods=['POST'])
def add_item():
    if request.method == 'POST':
        user_id = request.form['user_id']
        weight = request.form['weight']
        height = request.form['height']
        new_item = User(weight=weight, height=height)
        db.session.add(new_item)
        db.session.commit()
        return redirect(url_for('index'))

@app.route('/add_exercise', methods=['GET', 'POST'])
def add_exercise():
    if request.method == 'POST':
        exercise_name = request.form['exerciseName']
        exercise_calories_per_kg = request.form['calories_per_kg']
        new_exercise = Activity(
            name=exercise_name,
            calories_per_kg=exercise_calories_per_kg
        )
        db.session.add(new_exercise)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add_exercise.html')

@app.route('/api/exercises')
def get_exercises():
    exercises = Activity.query.all()
    exercise_list = [{'id': exercise.id, 'name': exercise.name, 'calories_per_kg': exercise.calories_per_kg} for exercise in exercises]
    return {'exercises': exercise_list}

@app.route('/record_exercise')
def record_exercise():
    user_id = request.args.get('user_id')
    weight = request.args.get('weight')
    height = request.args.get('height')
    return render_template('exercise_record.html', user_id=user_id, weight=weight, height=height)

@app.route('/submit_exercises', methods=['POST'])
def submit_exercises():
    try:
        data = request.get_json()
        user_id = 0
        exercises = data.get('exercises')

        for exercise in exercises:
            new_exercise_record = UserExerciseRecord(
                user_id=user_id,
                activity_id=exercise['activity_id'],
                time=exercise['time'],
                calories_consumption=exercise['calories_consumption']
            )
            db.session.add(new_exercise_record)

        db.session.commit()

        return jsonify({'message': 'Exercises submitted successfully'})

    except Exception as e:
        print("Error processing exercises:", str(e))
        db.session.rollback()
        return jsonify({'error': 'Failed to process exercises'}), 500
