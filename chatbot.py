import os, json
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, redirect, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from openai import OpenAI

# ------------------ Load Environment Variables ------------------
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ------------------ Database ------------------
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)

# ----------------- OpenAI -----------------
client = OpenAI()

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

with app.app_context():
    db.create_all()

# ----------------- Routes -----------------
@app.route('/')
def home():
    logged_in = 'user_id' in session
    return render_template('index.html', logged_in=logged_in)

# ----------------- Auth -----------------
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

# ----------------- Create New Chat -----------------
@app.route('/create_chat', methods=['POST'])
def create_chat():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Login required"})
    
    new_chat = Chat(user_id=session['user_id'], title="New Conversation", messages=json.dumps([]))
    db.session.add(new_chat)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "chat": {
            "db_id": new_chat.id,
            "title": new_chat.title,
            "messages": []
        }
    })

# ----------------- Get User Chats -----------------
@app.route('/get_chats')
def get_chats():
    if 'user_id' not in session:
        return jsonify([])
    chats = Chat.query.filter_by(user_id=session['user_id']).all()
    result = []
    for c in chats:
        result.append({
            "db_id": c.id,
            "title": c.title,
            "messages": json.loads(c.messages) if c.messages else []
        })
    return jsonify(result)

# ----------------- Add Message -----------------
@app.route('/chat/<int:chat_id>/add_message', methods=['POST'])
def add_message(chat_id):
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Login required"})
    
    chat = Chat.query.filter_by(id=chat_id, user_id=session['user_id']).first()
    if not chat:
        return jsonify({"success": False, "message": "Chat not found"})

    new_msg = request.json
    msgs = json.loads(chat.messages) if chat.messages else []
    msgs.append(new_msg)
    chat.messages = json.dumps(msgs)

    if not chat.title and new_msg['sender'] == 'user':
        chat.title = new_msg['text'][:30] + ("..." if len(new_msg['text']) > 30 else "")

    db.session.commit()
    return jsonify({"success": True})

# ----------------- Edit Message -----------------
@app.route('/chat/<int:chat_id>/edit_message', methods=['POST'])
def edit_message(chat_id):
    data = request.json
    chat = Chat.query.filter_by(id=chat_id, user_id=session['user_id']).first()
    if not chat: return jsonify({"success": False})
    msgs = json.loads(chat.messages)
    msgs[data['index']]['text'] = data['text']
    chat.messages = json.dumps(msgs)
    db.session.commit()
    return jsonify({"success": True})

# ----------------- Delete Message -----------------
@app.route('/chat/<int:chat_id>/delete_message', methods=['POST'])
def delete_message(chat_id):
    data = request.json
    chat = Chat.query.filter_by(id=chat_id, user_id=session['user_id']).first()
    if not chat: return jsonify({"success": False})
    msgs = json.loads(chat.messages)
    msgs.pop(data['index'])
    chat.messages = json.dumps(msgs)
    db.session.commit()
    return jsonify({"success": True})

# ----------------- Ask AI -----------------
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
