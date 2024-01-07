from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from sqlalchemy.orm import aliased
from sqlalchemy.sql import func

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

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        user_id = request.form['user_id']
        user = User.query.filter_by(id=user_id).first()

        if user is None:
            return redirect(url_for('register', user_id=user_id))

        # 使用者存在，進入使用者首頁
        return redirect(url_for('user_home', user_id=user_id))

    return render_template('login.html', User=User.query.all())

@app.route('/register/<user_id>', methods=['GET', 'POST'])
def register(user_id):
    if request.method == 'POST':
        weight = request.form['weight']
        height = request.form['height']

        # 創建新使用者
        new_user = User(id=user_id, weight=weight, height=height)
        db.session.add(new_user)
        db.session.commit()

        # 進入使用者首頁
        return redirect(url_for('user_home', user_id=user_id))

    return render_template('register.html', user_id=user_id)

@app.route('/user_home/<int:user_id>')
def user_home(user_id):
    user = User.query.get(user_id)
    return render_template('user_home.html', user=user)

@app.route('/view_past_week_records', methods=['GET'])
def view_past_week_records():
    user_id = request.args.get('user_id')
    # 取得七天前的日期
    seven_days_ago = datetime.utcnow() - timedelta(days=7)

    # 取得過去一周的運動紀錄，並結合 Activity 表格以獲取 Activity.name
    activity_alias = aliased(Activity)
    join_records = (
        db.session.query(
            UserExerciseRecord.date,
            func.sum(UserExerciseRecord.time).label('total_time'),
            func.sum(UserExerciseRecord.calories_consumption).label('total_calories_consumption'),
            func.sum(UserCaloriesRecord.calories_ingest).label('total_calories_ingest')
        )
        .outerjoin(UserCaloriesRecord, UserExerciseRecord.date == UserCaloriesRecord.date)  # Use outer join to include dates with no calories records
        # .filter(UserExerciseRecord.user_id == user_id)
        .filter(UserExerciseRecord.date >= seven_days_ago)
        .group_by(UserExerciseRecord.date)
        .order_by(UserExerciseRecord.date.asc())
        .all()
    )
    
    # TODO
    """
    detailed_food_records = (
        db.session.query(
            UserCaloriesRecord.date,
            Food.name,
            UserCaloriesRecord.calories_ingest
        )
        .join(Food, UserCaloriesRecord.food_id == Food.id)
        .filter(UserCaloriesRecord.user_id == user_id)
        .filter(UserCaloriesRecord.date >= seven_days_ago)
        .order_by(UserCaloriesRecord.date.asc())
        .all()
    )
    """
    detailed_food_records = ()
    
    detailed_exercise_records = (
        db.session.query(
            UserExerciseRecord.date,
            activity_alias.name,
            UserExerciseRecord.time,
            UserExerciseRecord.calories_consumption
        )
        .join(activity_alias, UserExerciseRecord.activity_id == activity_alias.id)
        # .filter(UserExerciseRecord.user_id == user_id)
        .filter(UserExerciseRecord.date >= seven_days_ago)
        .order_by(UserExerciseRecord.date.asc())
        .all()
    )
    return render_template('view_past_week_records.html',
                           join_records=join_records,
                           detailed_exercise_records=detailed_exercise_records,
                           detailed_food_records=detailed_food_records
                           )

@app.route('/compare_user_records', methods=['GET'])
def compare_users_records():
    user_id = request.args.get('user_id')
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    
    # 取得目前使用者的身高和體重
    current_user = User.query.get(user_id)

    # 找到相似使用者的條件
    similar_users = User.query.filter(
        User.id != user_id,
        User.height.between(current_user.height - 3, current_user.height + 3),
        User.weight.between(current_user.weight - 5, current_user.weight + 5)
    ).all()

    # 使用者的運動和攝取記錄
    user_records = (
        db.session.query(
            UserExerciseRecord.date,
            func.sum(UserExerciseRecord.time).label('total_time'),
            func.sum(UserExerciseRecord.calories_consumption).label('total_calories_consumption'),
            func.sum(UserCaloriesRecord.calories_ingest).label('total_calories_ingest')
        )
        .outerjoin(UserCaloriesRecord, UserExerciseRecord.date == UserCaloriesRecord.date)
        # .filter(UserExerciseRecord.user_id == user_id)
        .filter(UserExerciseRecord.date >= seven_days_ago)
        .group_by(UserExerciseRecord.date)
        .order_by(UserExerciseRecord.date.asc())
        .all()
    )

    # 找到相似使用者的條件
    similar_users = User.query.filter(
        User.id != user_id,
        User.height.between(current_user.height - 3, current_user.height + 3),
        User.weight.between(current_user.weight - 5, current_user.weight + 5)
    ).all()

    # 初始化一個字典來存放每位相似使用者的過去七天每天的消耗和攝取
    similar_user_records = {user.id: [] for user in similar_users}

    # 找到每位相似使用者過去七天每天的消耗和攝取
    for similar_user in similar_users:
        temp = (
            db.session.query(
                UserExerciseRecord.date,
                func.sum(UserExerciseRecord.calories_consumption).label('total_calories_consumption'),
                func.coalesce(func.sum(UserCaloriesRecord.calories_ingest), 0).label('total_calories_ingest')
            )
            .outerjoin(UserCaloriesRecord, UserExerciseRecord.date == UserCaloriesRecord.date)
            # .filter(UserExerciseRecord.user_id == similar_user.id)
            .filter(UserExerciseRecord.date >= seven_days_ago)
            .group_by(UserExerciseRecord.date)
            .order_by(UserExerciseRecord.date.asc())
            .all()
        )
        similar_user_records[similar_user.id] = temp

    # 計算每天所有相似使用者的平均值
    avg_records = []
    for date in set(record.date for records in similar_user_records.values() for record in records):
        avg_calories_consumption = sum(record.total_calories_consumption for records in similar_user_records.values() for record in records if record.date == date) / len(similar_users)
        avg_calories_ingest = sum(record.total_calories_ingest for records in similar_user_records.values() for record in records if record.date == date) / len(similar_users)
        avg_records.append({'date': date, 'avg_calories_consumption': avg_calories_consumption, 'avg_calories_ingest': avg_calories_ingest})

    return render_template(
        'compare_user_records.html',
        avg_records=avg_records,
        user_records=user_records,
        similar_users=similar_users,
    )

@app.route('/add_food', methods=['GET', 'POST'])
def add_food():
    return render_template('login.html', User=User.query.all())
# TODO
@app.route('/api/foods')
def get_foods():
    return render_template('login.html', User=User.query.all())
# TODO
@app.route('/record_food', methods=['GET', 'POST'])
def record_food():
    return render_template('login.html', User=User.query.all())


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
    user_id = request.args.get('user_id',type=int)
    weight = request.args.get('weight',type=float)
    height = request.args.get('height',type=float)
    return render_template('exercise_record.html', user_id=user_id, weight=weight, height=height)

@app.route('/submit_exercises', methods=['POST'])
def submit_exercises():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
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

@app.route('/exercise_history')
def exercise_history():
    user_id = request.args.get('user_id', type=int)

    if user_id is not None:
        results = db.session.query(UserExerciseRecord.id,
                                   UserExerciseRecord.user_id,
                                   UserExerciseRecord.date,
                                   Activity.name,
                                   UserExerciseRecord.time,
                                   UserExerciseRecord.calories_consumption).\
            join(Activity, UserExerciseRecord.activity_id == Activity.id).\
            filter(UserExerciseRecord.user_id == user_id).all()
    else:
        results = []

    return render_template('exercise_history.html', results=results)

@app.route('/delete_record/<int:record_id>', methods=['POST'])
def delete_record(record_id):
    try:
        record = UserExerciseRecord.query.get(record_id)
        if record:
            db.session.delete(record)
            db.session.commit()
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Record not found'}), 404
    except Exception as e:
        print("Error deleting record:", str(e))
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Failed to delete record'}), 500
