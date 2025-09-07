import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, redirect, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from openai import OpenAI

# ------------------ Load Environment Variables ------------------
load_dotenv()

app = Flask(__name__)

# ------------------ Secure Secret Key ------------------
app.secret_key = os.urandom(24)  # automatically generate secure key

# ------------------ Database ------------------
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)

# ----------------- OpenAI -----------------
client = OpenAI()  # load from .env

# ----------------- Models -----------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    chats = db.relationship('Chat', backref='user', lazy=True)

class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100))
    messages = db.Column(db.Text)  # store JSON string of messages

# ----------------- Initialize Database -----------------
with app.app_context():
    db.create_all()

# ----------------- Routes -----------------
@app.route('/')
def home():
    logged_in = 'user_id' in session
    return render_template('index.html', logged_in=logged_in)

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if User.query.filter_by(username=username).first():
        return jsonify({"success": False, "message": "Username exists"})
    hashed = generate_password_hash(password)
    user = User(username=username, password=hashed)
    db.session.add(user)
    db.session.commit()
    session['user_id'] = user.id
    return jsonify({"success": True})

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password, password):
        return jsonify({"success": False, "message": "Invalid credentials"})
    session['user_id'] = user.id
    return jsonify({"success": True})

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect('/')

@app.route("/ask", methods=["POST"])
def ask():
    if 'user_id' not in session:
        return jsonify({"reply": "Please log in first."})
    user_input = request.json.get("message")
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": user_input}
            ]
        )
        return jsonify({"reply": response.choices[0].message.content})
    except Exception as e:
        return jsonify({"reply": f"Error: {str(e)}"})

