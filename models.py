# models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(300), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class UserScores(db.Model):
    __tablename__ = "user_scores"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    dsa = db.Column(db.Integer, default=0)
    dbms = db.Column(db.Integer, default=0)
    os = db.Column(db.Integer, default=0)
    cn = db.Column(db.Integer, default=0)
    math = db.Column(db.Integer, default=0)
    aptitude = db.Column(db.Integer, default=0)
    comm = db.Column(db.Integer, default=0)
    problem_solving = db.Column(db.Integer, default=0)
    creative = db.Column(db.Integer, default=0)
    hackathons = db.Column(db.Integer, default=0)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())

    user = db.relationship("User", backref="scores")
