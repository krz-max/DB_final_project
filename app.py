from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from sqlalchemy.orm import aliased
from sqlalchemy.sql import func
import pandas as pd
from sqlalchemy import inspect

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///your_database.db'
app.jinja_env.add_extension('jinja2.ext.loopcontrols')
db = SQLAlchemy(app)

class Food(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False, unique=True)

class Nutrient(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
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
    food_id = db.Column(db.Integer, db.ForeignKey('food.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow, nullable=False)
    calories_ingest = db.Column(db.Integer, nullable=False)

class UserExerciseRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow, nullable=False)
    activity_id = db.Column(db.Integer, db.ForeignKey('activity.id'), nullable=False)
    time = db.Column(db.Integer, nullable=False)
    calories_consumption = db.Column(db.Integer, nullable=False)

class WeightRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow, nullable=False)
    weight = db.Column(db.Float, nullable=False)

with app.app_context():
    inspector = inspect(db.engine)
    if not inspector.has_table('food') or not inspector.has_table('activity'):
        # 如果表格不存在，則建立資料庫表格
        db.create_all()

        # 讀取 food_nutrients_clean.csv 並插入 Food 和 Nutrient 資料表
        food_nutrients_data = pd.read_csv('dataset/food/food_nutrients_clean.csv')
        food_nutrients_data = food_nutrients_data.dropna()
        food_nutrients_data = food_nutrients_data.drop_duplicates(subset=['樣品名稱'])
        for index, row in food_nutrients_data.iterrows():
            food = Food(name=row['樣品名稱'])
            db.session.add(food)
            db.session.commit()

            nutrient = Nutrient(
                food_id=food.id,
                calories=row['熱量(kcal)'],
                carbohydrates=row['總碳水化合物(g)'],
                protein=row['粗蛋白(g)'],
                fat=row['粗脂肪(g)'],
            )
            db.session.add(nutrient)
            db.session.commit()
            print(f'Added {food.name} to database')

        # 讀取 exercise_clean.csv 並插入 Activity 資料表
        exercise_data = pd.read_csv('dataset/exercise/exercise_clean.csv')
        exercise_data = exercise_data.dropna()
        exercise_data = exercise_data.drop_duplicates(subset=['Activity'])
        for index, row in exercise_data.iterrows():
            activity = Activity(
                name=row['Activity'],
                calories_per_kg=row['Calories per kg'],
            )
            db.session.add(activity)
            db.session.commit()
            print(f'Added {activity.name} to database')

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
    today_calories_consumption = (
        db.session.query(
            func.sum(UserExerciseRecord.calories_consumption)
        )
        .filter(UserExerciseRecord.user_id == user_id)
        .filter(UserExerciseRecord.date == datetime.utcnow().date())
        .scalar()
    )
    today_calories_ingest = (
        db.session.query(
            func.sum(UserCaloriesRecord.calories_ingest)
        )
        .filter(UserCaloriesRecord.user_id == user_id)
        .filter(UserCaloriesRecord.date == datetime.utcnow().date())
        .scalar()
    )
    return render_template('user_home.html',
                            user=user,
                            today_calories_consumption=today_calories_consumption,
                            today_calories_ingest=today_calories_ingest)

@app.route('/record_weight', methods=['GET', 'POST'])
def record_weight():
    if request.method == 'POST':
        user_id = request.form['user_id']
        weight = request.form['weight']
        
        # 新增體重紀錄
        new_weight_record = WeightRecord(user_id=user_id, weight=weight)
        db.session.add(new_weight_record)
        db.session.commit()

        # 更新使用者的體重
        user = User.query.get(user_id)
        user.weight = weight
        db.session.commit()
        
        # 重新導向到使用者首頁
        return redirect(url_for('user_home', user_id=user_id))

    user_id = request.args.get('user_id')
    return render_template('record_weight.html', user_id=user_id)


@app.route('/get_records', methods=['GET'])
def get_records():
    user_id = request.args.get('user_id')
    selected_date = request.args.get('selectedDate')  # 新增取得選擇的日期

    if selected_date:
        # 如果選擇了日期，使用選擇的日期，否則使用當前日期
        selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
    else:
        selected_date = datetime.utcnow().date() - timedelta(days=7)
    
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
        .filter(UserExerciseRecord.user_id == user_id)
        .filter(UserExerciseRecord.date >= selected_date)
        .group_by(UserExerciseRecord.date)
        .order_by(UserExerciseRecord.date.asc())
        .all()
    )
    
    detailed_weight_records = (
        db.session.query(
            WeightRecord.date,
            WeightRecord.weight
        )
        .filter(WeightRecord.user_id == user_id)
        .filter(WeightRecord.date >= selected_date)
        .order_by(WeightRecord.date.asc())
        .all()
    )
    # TODO
    detailed_food_records = (
        # db.session.query(
        #     UserCaloriesRecord.date,
        #     Food.name,
        #     UserCaloriesRecord.calories_ingest
        # )
        # .join(Food, UserCaloriesRecord.food_id == Food.id)
        # .filter(UserCaloriesRecord.user_id == user_id)
        # .filter(UserCaloriesRecord.date >= selected_date)
        # .order_by(UserCaloriesRecord.date.asc())
    )
    
    detailed_exercise_records = (
        db.session.query(
            UserExerciseRecord.date,
            activity_alias.name,
            UserExerciseRecord.time,
            UserExerciseRecord.calories_consumption
        )
        .join(activity_alias, UserExerciseRecord.activity_id == activity_alias.id)
        .filter(UserExerciseRecord.user_id == user_id)
        .filter(UserExerciseRecord.date >= selected_date)
        .order_by(UserExerciseRecord.date.asc())
        .all()
    )
    # 返回 JSON 格式的記錄，用於在前端進行更新
    return jsonify({
        'join_records': [{'date': record.date.strftime('%Y-%m-%d'),
                          'total_time': record.total_time,
                          'total_calories_consumption': record.total_calories_consumption,
                          'total_calories_ingest': record.total_calories_ingest}
                         for record in join_records],
        'detailed_weight_records': [{'date': record.date.strftime('%Y-%m-%d'),
                                     'weight': record.weight}
                                    for record in detailed_weight_records],
        'detailed_food_records': [{'date': record.date.strftime('%Y-%m-%d'),
                                   'name': record.name,
                                   'calories_ingest': record.calories_ingest}
                                  for record in detailed_food_records],
        'detailed_exercise_records': [{'date': record.date.strftime('%Y-%m-%d'),
                                       'name': record.name,
                                       'time': record.time,
                                       'calories_consumption': record.calories_consumption}
                                      for record in detailed_exercise_records],
    })
    
@app.route('/view_past_week_records', methods=['GET'])
def view_past_week_records():
    user_id = request.args.get('user_id')
    selected_date = request.args.get('selectedDate')  # 新增取得選擇的日期

    if selected_date:
        # 如果選擇了日期，使用選擇的日期，否則使用當前日期
        selected_date = datetime.utcnow().date() - datetime.strptime(selected_date, '%Y-%m-%d').date()
    else:
        selected_date = datetime.utcnow().date() - timedelta(days=7)
    
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
        .filter(UserExerciseRecord.user_id == user_id)
        .filter(UserExerciseRecord.date >= selected_date)
        .group_by(UserExerciseRecord.date)
        .order_by(UserExerciseRecord.date.asc())
        .all()
    )
    
    detailed_weight_records = (
        db.session.query(
            WeightRecord.date,
            WeightRecord.weight
        )
        .filter(WeightRecord.user_id == user_id)
        .filter(WeightRecord.date >= selected_date)
        .order_by(WeightRecord.date.asc())
        .all()
    )
    # TODO
    detailed_food_records = (
        # db.session.query(
        #     UserCaloriesRecord.date,
        #     Food.name,
        #     UserCaloriesRecord.calories_ingest
        # )
        # .join(Food, UserCaloriesRecord.food_id == Food.id)
        # .filter(UserCaloriesRecord.user_id == user_id)
        # .filter(UserCaloriesRecord.date >= selected_date)
        # .order_by(UserCaloriesRecord.date.asc())
    )
    
    detailed_exercise_records = (
        db.session.query(
            UserExerciseRecord.date,
            activity_alias.name,
            UserExerciseRecord.time,
            UserExerciseRecord.calories_consumption
        )
        .join(activity_alias, UserExerciseRecord.activity_id == activity_alias.id)
        .filter(UserExerciseRecord.user_id == user_id)
        .filter(UserExerciseRecord.date >= selected_date)
        .order_by(UserExerciseRecord.date.asc())
        .all()
    )
    # 返回 JSON 格式的記錄，用於在前端進行更新
    return render_template('view_past_week_records.html',
                           user_id=user_id,
                           join_records=join_records,
                           detailed_exercise_records=detailed_exercise_records,
                           detailed_food_records=detailed_food_records,
                           detailed_weight_records=detailed_weight_records,
                           )

@app.route('/get_similar_records', methods=['GET'])
def get_similar_records():
    user_id = request.args.get('user_id')
    selected_date = request.args.get('selectedDate')  # 新增取得選擇的日期

    if selected_date:
        # 如果選擇了日期，使用選擇的日期，否則使用當前日期
        selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
    else:
        selected_date = datetime.utcnow().date() - timedelta(days=7)
        
    # 取得目前使用者的身高和體重
    current_user = User.query.get(user_id)
    # 使用者的運動和攝取記錄
    user_records = (
        db.session.query(
            UserExerciseRecord.date,
            func.sum(UserExerciseRecord.calories_consumption).label('total_calories_consumption'),
            func.sum(UserCaloriesRecord.calories_ingest).label('total_calories_ingest')
        )
        .outerjoin(UserCaloriesRecord, UserExerciseRecord.date == UserCaloriesRecord.date)
        .filter(UserExerciseRecord.user_id == user_id)
        .filter(UserExerciseRecord.date >= selected_date)
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
            .filter(UserExerciseRecord.user_id == similar_user.id)
            .filter(UserExerciseRecord.date >= selected_date)
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
    # 返回 JSON 格式的記錄，用於在前端進行更新
    return jsonify({
        'avg_records': [{'date': record['date'].strftime('%Y-%m-%d'),
                         'avg_calories_consumption': record['avg_calories_consumption'],
                         'avg_calories_ingest': record['avg_calories_ingest']}
                         for record in avg_records],
        'user_records': [{'date': record.date.strftime('%Y-%m-%d'),
                          'total_calories_consumption': record.total_calories_consumption,
                          'total_calories_ingest': record.total_calories_ingest}
                          for record in user_records],
        'similar_users': [{'id': user.id, 'weight': user.weight, 'height': user.height} for user in similar_users],
    })

# TODO: user_id完成後要檢查
@app.route('/compare_user_records', methods=['GET'])
def compare_users_records():
    user_id = request.args.get('user_id')
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    
    # 取得目前使用者的身高和體重
    current_user = User.query.get(user_id)
    # 使用者的運動和攝取記錄
    user_records = (
        db.session.query(
            UserExerciseRecord.date,
            func.sum(UserExerciseRecord.calories_consumption).label('total_calories_consumption'),
            func.sum(UserCaloriesRecord.calories_ingest).label('total_calories_ingest')
        )
        .outerjoin(UserCaloriesRecord, UserExerciseRecord.date == UserCaloriesRecord.date)
        .filter(UserExerciseRecord.user_id == user_id)
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
            .filter(UserExerciseRecord.user_id == similar_user.id)
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
        user_id=user_id
    )
    

# TODO
@app.route('/add_food', methods=['GET', 'POST'])
def add_food():
    if request.method=='POST':
        food_name=request.form['foodName']
        new_food=Food(
            name=food_name
        )

        db.session.add(new_food)
        db.session.commit()
        food_calories=request.form['foodCalories']
        food_carbohydrates=request.form['foodCarbohydrates']
        food_protein=request.form['foodProtein']
        food_fat=request.form['foodFat']
        new_nutrient=Nutrient(
            food_id=new_food.id,
            calories=food_calories,
            carbohydrates=food_carbohydrates,
            protein=food_protein,
            fat=food_fat
        )
        db.session.add(new_nutrient)
        db.session.commit()
    return render_template('add_food.html')
# TODO
@app.route('/api/foods')
def get_foods():
    foods=db.session.query(Food, Nutrient).join(Nutrient, Food.id == Nutrient.food_id).all()
    food_list=[{
        'id': food.id,
        'name': food.name,
        'calories': nutrient.calories,
        'carbohydrates': nutrient.carbohydrates,
        'protein': nutrient.protein,
        'fat': nutrient.fat
    } for food,nutrient in foods]
    return jsonify({'foods':food_list})
# TODO
@app.route('/record_food', methods=['GET', 'POST'])
def record_food():
    user_id = request.args.get('user_id', type=int)
    return render_template('food_record.html', user_id=user_id)

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
@app.route('/submit_foods',methods=['POST'])
def submit_foods():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        foods = data.get('foods')

        for food_data in foods:
            # 假设food_data包含food_id和calories_ingest
            food_id=food_data['food_id']
            calories_ingest = food_data['calories']

            # 创建并保存食物摄入记录
            new_calories_record = UserCaloriesRecord(
                user_id=user_id,
                food_id=food_id,
                
                calories_ingest=calories_ingest
            )
            db.session.add(new_calories_record)

        db.session.commit()
        return jsonify({'message': 'Foods submitted successfully'})

    except Exception as e:
        print("Error processing foods:", str(e))
        db.session.rollback()
        return jsonify({'error': 'Failed to process foods'}), 500

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
