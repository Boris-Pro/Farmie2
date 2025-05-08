

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import mysql.connector
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
app.config['JWT_TOKEN_LOCATION'] = ['cookies']
app.config['JWT_ACCESS_COOKIE_PATH'] = '/'
app.config['JWT_COOKIE_CSRF_PROTECT'] = False

jwt = JWTManager(app)
CORS(app, supports_credentials=True)

db = mysql.connector.connect(
    host=os.getenv('MYSQL_HOST'),
    user=os.getenv('MYSQL_USER'),
    password=os.getenv('MYSQL_PASSWORD'),
    database=os.getenv('MYSQL_DB')
)

@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    cursor = db.cursor()
    cursor.execute("INSERT INTO User (user_name, email, password) VALUES (%s, %s, %s)", 
                   (data['user_name'], data['email'], data['password']))
    db.commit()
    return jsonify(message='User registered'), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    cursor = db.cursor()
    cursor.execute("SELECT user_id, password FROM User WHERE email=%s", (data['email'],))
    user = cursor.fetchone()
    if user and data['password'] == user[1]:
        token = create_access_token(identity=user[0], expires_delta=datetime.timedelta(days=1))
        resp = jsonify(login=True)
        resp.set_cookie('access_token_cookie', token)
        return resp
    return jsonify(error="Invalid credentials"), 401

@app.route('/farm', methods=['POST'])
@jwt_required()
def create_farm():
    user_id = get_jwt_identity()
    data = request.json
    cursor = db.cursor()
    cursor.execute("INSERT INTO Farm (user_id, location) VALUES (%s, %s)", (user_id, data['location']))
    db.commit()
    return jsonify(message="Farm created"), 201

@app.route('/farms', methods=['GET'])
@jwt_required()
def get_farms():
    user_id = get_jwt_identity()
    cursor = db.cursor()
    cursor.execute("SELECT farm_id, location FROM Farm WHERE user_id=%s", (user_id,))
    farms = cursor.fetchall()
    return jsonify([{'farm_id': f[0], 'location': f[1]} for f in farms])

@app.route('/crop', methods=['POST'])
@jwt_required()
def create_crop():
    data = request.json
    cursor = db.cursor()
    cursor.execute("INSERT INTO Crop (crop_name, crop_family) VALUES (%s, %s)", 
                   (data['crop_name'], data['crop_family']))
    db.commit()
    return jsonify(message="Crop added"), 201

@app.route('/crops', methods=['GET'])
def get_crops():
    cursor = db.cursor()
    cursor.execute("SELECT crop_id, crop_name, crop_family FROM Crop")
    crops = cursor.fetchall()
    return jsonify([{'crop_id': c[0], 'crop_name': c[1], 'crop_family': c[2]} for c in crops])

@app.route('/cultivate', methods=['POST'])
@jwt_required()
def cultivate_crop():
    user_id = get_jwt_identity()
    data = request.json
    cursor = db.cursor()
    cursor.execute("SELECT 1 FROM Farm WHERE farm_id=%s AND user_id=%s", (data['farm_id'], user_id))
    if not cursor.fetchone():
        return jsonify(error="Unauthorized or invalid farm"), 403
    cursor.execute("""
        INSERT INTO Cultivate (crop_id, farm_id, quantity)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE quantity=VALUES(quantity)
    """, (data['crop_id'], data['farm_id'], data['quantity']))
    db.commit()
    return jsonify(message="Crop assigned"), 200

if __name__ == '__main__':
    app.run(debug=True)
