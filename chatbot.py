import os, json
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from openai import OpenAI
from authlib.integrations.flask_client import OAuth

# ------------------ Load Environment Variables ------------------
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ------------------ Database ------------------
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)

# ------------------ OpenAI ------------------
client = OpenAI()

# ------------------ OAuth (Google Login) ------------------
oauth = OAuth(app)
app.config['GOOGLE_CLIENT_ID'] = os.getenv("GOOGLE_CLIENT_ID")
app.config['GOOGLE_CLIENT_SECRET'] = os.getenv("GOOGLE_CLIENT_SECRET")
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", os.urandom(24))

google = oauth.register(
    name='google',
    client_id=app.config['GOOGLE_CLIENT_ID'],
    client_secret=app.config['GOOGLE_CLIENT_SECRET'],
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params={'scope': 'email profile'},
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    client_kwargs={'scope': 'openid email profile'}
)

# ----------------- Models -----------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    username = db.Column(db.String(50), unique=True, nullable=True)
    password = db.Column(db.String(200), nullable=True)
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
    email = data.get('email')
    username = data.get('username')
    password = data.get('password')

    if User.query.filter((User.username==username) | (User.email==email)).first():
        return jsonify({"success": False, "message": "User already exists"})

    hashed = generate_password_hash(password)
    user = User(username=username, email=email, password=hashed)
    db.session.add(user)
    db.session.commit()
    session['user_id'] = user.id
    return jsonify({"success": True})

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password, password):
        return jsonify({"success": False, "message": "Invalid credentials"})
    
    session['user_id'] = user.id
    return jsonify({"success": True})

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect('/')

# ----------------- Google Login -----------------
@app.route('/login/google')
def google_login():
    redirect_uri = url_for('google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/login/google/callback')
def google_callback():
    token = google.authorize_access_token()
    resp = google.get('userinfo')
    user_info = resp.json()

    user = User.query.filter_by(email=user_info['email']).first()
    if not user:
        user = User(email=user_info['email'], username=user_info.get('name'))
        db.session.add(user)
        db.session.commit()
    
    session['user_id'] = user.id
    return redirect('/')

# ----------------- Profile Settings -----------------
@app.route('/profile/change_password', methods=['POST'])
def change_password():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Login required"})

    data = request.get_json()
    old_password = data.get("old_password")
    new_password = data.get("new_password")

    user = User.query.get(session['user_id'])
    if not check_password_hash(user.password, old_password):
        return jsonify({"success": False, "message": "Wrong old password"})

    user.password = generate_password_hash(new_password)
    db.session.commit()
    return jsonify({"success": True})

@app.route('/profile/delete_account', methods=['POST'])
def delete_account():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Login required"})

    user = User.query.get(session['user_id'])
    db.session.delete(user)
    db.session.commit()
    session.pop('user_id', None)
    return jsonify({"success": True, "message": "Account deleted"})

# ----------------- Chat Endpoints -----------------
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

@app.route('/get_chats')
def get_chats():
    if 'user_id' not in session:
        return jsonify([])
    chats = Chat.query.filter_by(user_id=session['user_id']).all()
    return jsonify([{
        "db_id": c.id,
        "title": c.title,
        "messages": json.loads(c.messages) if c.messages else []
    } for c in chats])

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
