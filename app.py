from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///your_database.db'  # 使用SQLite，你也可以選擇其他資料庫
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

