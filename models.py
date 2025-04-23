from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_bootstrap import Bootstrap5
from werkzeug.security import generate_password_hash, check_password_hash
from db import db

class ChatUser(UserMixin, db.Model):
    __tablename__ = 'chat_users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)


class DictionaryEntry(db.Model):
    __tablename__ = 'dictionary_entries'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('chat_users.id'), nullable=False)
    chinese = db.Column(db.String(10), nullable=False)
    pinyin = db.Column(db.String(50), nullable=True)
    translation = db.Column(db.String(255), nullable=True)
    examples = db.Column(db.JSON, nullable=True)  # List of example sentences
    user = db.relationship('ChatUser', backref=db.backref('dictionary', lazy=True))


class ChatHistory(db.Model):
    __tablename__ = 'chat_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('chat_users.id'), nullable=False)
    level = db.Column(db.String(10), nullable=False)  # e.g., A1, B2, etc.
    message = db.Column(db.Text, nullable=False)
    reply = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('ChatUser', backref=db.backref('chat_histories', lazy=True))


class ChatSummary(db.Model):
    __tablename__ = 'chat_summaries'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('chat_users.id'), nullable=False)
    level = db.Column(db.String(10), nullable=False)
    summary = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('ChatUser', backref=db.backref('chat_summaries', lazy=True))

