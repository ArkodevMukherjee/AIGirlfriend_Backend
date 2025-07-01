from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from langchain.schema import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
import datetime
import os

# --- CONFIG ---
app = Flask(__name__)
CORS(app)
app.config['JWT_SECRET_KEY'] = 'super-secret-key'  # Replace with env var in prod
jwt = JWTManager(app)

# --- MONGO DB ---
client = MongoClient("mongodb+srv://username:VvwnBeJMOue4jMs1@cluster0.n5ejfzl.mongodb.net/?retryWrites=true&w=majority&tls=true")
db = client['luna_db']
users_col = db['users']

# OoagIiiq9W7ty64l
# VvwnBeJMOue4jMs1

# --- GEMINI ---
os.environ['GOOGLE_API_KEY'] = "AIzaSyCxjoaEpXuLqK5TsRB7MG1k8dCA2XJuZe0"

llm = ChatGoogleGenerativeAI(
model="gemini-2.0-flash",
google_api_key=os.environ['GOOGLE_API_KEY'],
temperature=0.7
)

# --- ROUTES ---

# Register
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if users_col.find_one({"username": username}):
        return jsonify({"msg": "Username already exists"}), 400

    hashed = generate_password_hash(password)
    users_col.insert_one({"username": username, "password": hashed, "chat_history": []})
    access_token = create_access_token(identity=username, expires_delta=datetime.timedelta(hours=1))
    return jsonify({
        "msg": "User registered successfully",
        "access_token": access_token
    })

# Login
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    user = users_col.find_one({"username": username})
    if not user or not check_password_hash(user['password'], password):
        return jsonify({"msg": "Invalid credentials"}), 401

    token = create_access_token(identity=username, expires_delta=datetime.timedelta(hours=1))
    return jsonify(access_token=token)

# Chat
@app.route('/chat', methods=['POST'])
@jwt_required()
def chat():
    username = get_jwt_identity()
    message = request.json.get("message")
    if not message:
        return jsonify({"error": "Message required"}), 400

    user = users_col.find_one({"username": username})
    history = user.get("chat_history", [])

    chat_messages = [SystemMessage(content="You are Luna, a sweet and intelligent virtual girlfriend. Be empathetic and engaging.")]
    for m in history:
        role = m['role']
        content = m['message']
        if role == 'user':
            chat_messages.append(HumanMessage(content=content))
        else:
            chat_messages.append(SystemMessage(content=content))

    chat_messages.append(HumanMessage(content=message))
    response = llm(chat_messages)
    reply = response.content

    # Save to DB
    users_col.update_one(
        {"username": username},
        {"$push": {"chat_history": {"role": "user", "message": message}}}
    )
    users_col.update_one(
        {"username": username},
        {"$push": {"chat_history": {"role": "luna", "message": reply}}}
    )

    return jsonify({"response": reply})

# Optional: Clear history
@app.route('/clear', methods=['POST'])
@jwt_required()
def clear_history():
    username = get_jwt_identity()
    users_col.update_one({"username": username}, {"$set": {"chat_history": []}})
    return jsonify({"msg": "Chat history cleared"})

# Run
if __name__ == '__main__':
    app.run(debug=True,use_reloader=False)
