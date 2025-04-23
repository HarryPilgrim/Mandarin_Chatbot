from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, abort, session
import google.generativeai as genai
import os
#from flask_ckeditor import CKEditor
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required
from sqlalchemy.orm import DeclarativeBase
from flask_migrate import Migrate
from flask_bootstrap import Bootstrap5
from flask_cors import CORS
from db import db  # Import db from the new db.py file
import os
from dotenv import load_dotenv
from forms import RegisterForm, LoginForm
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
from forms import RegisterForm, LoginForm  # Assuming you've created these using Flask-WTF
from models import ChatUser  # Your model
from db import db


app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6babcdefg'

# Initialize Bootstrap5
bootstrap = Bootstrap5(app)


load_dotenv()  # load .env if exists
db_uri = os.getenv("DATABASE_URL", "sqlite:///local-chinese-dict.db")
app.config["SQLALCHEMY_DATABASE_URI"] = db_uri

db.init_app(app)
migrate = Migrate(app, db)
CORS(app)

from models import ChatUser, DictionaryEntry, ChatHistory, ChatSummary

# Ensure app context for database operations
with app.app_context():
    db.create_all()  # Creates tables in the database

#### comment out this to make first user
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(ChatUser, user_id)  # Avoid unnecessary joins or relationships

# Set your Gemini API key
genai.configure(api_key="AIzaSyCkayENRPF9NMd3oQnxDFIOh8aIBPcoczg")
model = genai.GenerativeModel('gemini-1.5-flash')

# Define characters by CEFR level
characters = {
    "A1": {"name": "Anna", "image": "a1.jpg"},
    "A2": {"name": "Ben", "image": "a2.jpg"},
    "B1": {"name": "Carlos", "image": "b1.jpg"},
    "B2": {"name": "Dina", "image": "b2.jpg"},
    "C1": {"name": "Elena", "image": "c1.jpg"},
    "C2": {"name": "Farid", "image": "c2.jpg"},
}

user_dictionary = []

# Store chats in memory (simple)
chat_sessions = {}

@app.route("/")
def index():
    return render_template("chat.html", characters=characters, user_dictionary=user_dictionary)

@app.route("/chat", methods=["POST"])
def chat():
    # data = request.json
    # level = data["level"]
    # message = data["message"]
    # user_id = data["user_id"]  # make sure you're sending this from the frontend
    # Check if the user is authenticated
    user_id = None

    if current_user.is_authenticated:
        # Get user_id from the logged-in user
        user_id = current_user.id
    else:
        # Generate a temporary user_id for guest users (using UUID)
        user_id = session.get("guest_user_id")

        if not user_id:
            # Generate a new guest user_id and store it in the session
            user_id = str(uuid.uuid4())
            session["guest_user_id"] = user_id  # Store it for the duration of the session

    # Now proceed with the rest of your code
    level = request.json["level"]
    message = request.json["message"]

    if level not in chat_sessions:
        # Base instructions
        base_prompt = (
            f"You are a native Chinese speaker helping someone learn Mandarin Chinese."
            f" You only reply in Chinese, even if the user speaks English."
            f" Use HSK level {level} vocabulary and grammar — nothing more advanced."
            f" Speak naturally but simply. Be friendly, ask questions, and gently correct any mistakes the user makes."
            f" Do not translate or use any English in your response."
        )

        # Look up last summary for logged-in users
        if current_user.is_authenticated:
            latest_summary = ChatSummary.query.filter_by(user_id=user_id, level=level).order_by(
                ChatSummary.created_at.desc()).first()
            summary_text = latest_summary.summary if latest_summary else None
        else:
            summary_text = None  # No summary for guest users

        # Include the summary in the prompt if available
        if summary_text:
            system_prompt = f"{base_prompt}\n\nHere is a summary of your past conversation with the user:\n{summary_text}"
        else:
            system_prompt = base_prompt

        chat_sessions[level] = genai.GenerativeModel("gemini-1.5-flash").start_chat(history=[
            {"role": "user", "parts": [system_prompt]}
        ])

    chat = chat_sessions[level]
    try:
        response = chat.send_message(message)
        reply = response.text

        # Save to database
        # Save to database for logged-in users only
        if current_user.is_authenticated:
            history = ChatHistory(user_id=user_id, level=level, message=message, reply=reply)
            db.session.add(history)
            db.session.commit()

    except Exception as e:
        reply = f"Error: {str(e)}"

    return jsonify({"reply": reply})


@app.route("/summarize", methods=["POST"])
def summarize():
    data = request.json
    user_id = data["user_id"]
    level = data["level"]

    history = ChatHistory.query.filter_by(user_id=user_id, level=level).order_by(ChatHistory.timestamp.desc()).limit(10).all()
    if not history:
        return jsonify({"summary": "No history available."})

    conversation = "\n".join([f"User: {h.message}\nBot: {h.reply}" for h in reversed(history)])

    try:
        summary_response = model.generate_content(f"请总结以下中文对话内容，用中文写一段简洁总结：\n\n{conversation}")
        summary_text = summary_response.text
        # Only save if user is logged in
        if user_id:
            summary = ChatSummary(user_id=user_id, level=level, summary=summary_text)
            db.session.add(summary)
            db.session.commit()

        return jsonify({"summary": summary_text})
    except Exception as e:
        return jsonify({"summary": f"Error: {str(e)}"})



@app.route("/save_word", methods=["POST"])
def save_word():
    if not current_user.is_authenticated:
        return jsonify({"status": "error", "message": "Login required to save words."}), 401

    data = request.json
    word = data.get("word")
    pinyin = data.get("pinyin", "")
    translation = data.get("translation", "")

    # Avoid duplicates
    existing = DictionaryEntry.query.filter_by(
        user_id=current_user.id,
        chinese=word
    ).first()

    if existing:
        return jsonify({"status": "ok", "message": "Already saved."})

    entry = DictionaryEntry(
        user_id=current_user.id,
        chinese=word,
        pinyin=pinyin,
        translation=translation
    )
    db.session.add(entry)
    db.session.commit()

    return jsonify({"status": "ok", "message": "Saved."})

@app.route("/get_dictionary")
def get_dictionary():
    if not current_user.is_authenticated:
        return jsonify([])

    entries = DictionaryEntry.query.filter_by(user_id=current_user.id).all()
    return jsonify([
        {"chinese": e.chinese, "pinyin": e.pinyin, "translation": e.translation}
        for e in entries
    ])

@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        username = form.username.data

        existing_user = ChatUser.query.filter_by(email=email).first()
        if existing_user:
            flash("You've already signed up with that email. Log in instead!", "warning")
            return redirect(url_for('login'))

        new_user = ChatUser(email=email, username=username)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        flash("Account created successfully!", "success")
        return redirect(url_for('index'))

    return render_template("register.html", form=form, current_user=current_user)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        user = ChatUser.query.filter_by(email=email).first()
        if not user:
            flash("That email does not exist, please try again.", "danger")
            return redirect(url_for('login'))
        elif not user.check_password(password):
            flash("Password incorrect, please try again.", "danger")
            return redirect(url_for('login'))
        else:
            login_user(user, remember=True)
            flash("Logged in successfully!", "success")
            return redirect(url_for('index'))

    return render_template("login.html", form=form, current_user=current_user)


@app.route('/logout')
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('index'))


if __name__ == "__main__":
    app.run(debug=True, port=5005)

