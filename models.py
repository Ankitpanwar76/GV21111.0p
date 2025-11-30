from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import date, datetime, timedelta

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    name = db.Column(db.String(100))
    streak = db.Column(db.Integer, default=0)
    last_active = db.Column(db.Date)
    learned = db.Column(db.Text, default='')  # topic|mode|difficulty

    def update_streak(self):
        today = date.today()
        if self.last_active == today:
            return
        if self.last_active == today - timedelta(days=1):
            self.streak += 1
        else:
            self.streak = 1
        self.last_active = today
        db.session.commit()

    def log_learning(self, topic, mode, difficulty=None):
        entry = f"{topic}|{mode}|{difficulty or ''}"
        parts = [p.strip() for p in self.learned.split(',') if p.strip()]
        if entry not in parts:
            parts.append(entry)
            self.learned = ','.join(parts)
        self.update_streak()

class PlaylistItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    topic = db.Column(db.String(200), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    thumbnail = db.Column(db.String(500))
    channel = db.Column(db.String(200))
    searched_at = db.Column(db.DateTime, default=datetime.utcnow)

class Documentation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    topic = db.Column(db.String(200), nullable=False)
    markdown = db.Column(db.Text, nullable=False)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)

class SkillPost(db.Model):
    __tablename__ = 'skill_post'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    video_filename = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    author = db.relationship('User', backref='skill_posts')
    likes = db.relationship('Like', backref='post',
                            lazy=True, cascade='all, delete-orphan')


class Like(db.Model):
    __tablename__ = 'like'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('skill_post.id'), nullable=False)

    __table_args__ = (db.UniqueConstraint('user_id', 'post_id', name='uq_user_post'),)