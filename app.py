# app.py
from dotenv import load_dotenv
import os
load_dotenv()  # Load environment variables first

from flask import Flask, redirect, url_for, render_template  # ← Added render_template
from flask_login import LoginManager, current_user
from flask_sqlalchemy import SQLAlchemy
from config import Config
from models import db, User

# ----------------------------------------------------------------------
# Import ALL blueprints (including the new SkillShare)
# ----------------------------------------------------------------------
from routes import (
    auth,
    dashboard,
    youtube,
    gemini,
    code,
    skillshare,          # NEW
)

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # --------------------------------------------------------------
    # Upload folder (videos from SkillShare)
    # --------------------------------------------------------------
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # --------------------------------------------------------------
    # Initialise extensions
    # --------------------------------------------------------------
    db.init_app(app)

    login_manager = LoginManager(app)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(uid):
        # SQLAlchemy 2.0+ style
        return db.session.get(User, int(uid))

    # --------------------------------------------------------------
    # Register blueprints
    # --------------------------------------------------------------
    app.register_blueprint(auth,        url_prefix='/auth')
    app.register_blueprint(dashboard)                     # no prefix
    app.register_blueprint(youtube,     url_prefix='/youtube')
    app.register_blueprint(gemini,      url_prefix='/gemini')
    app.register_blueprint(code,        url_prefix='/code')
    app.register_blueprint(skillshare,  url_prefix='/skillshare')   # NEW

    # --------------------------------------------------------------
    # CLI command to create tables
    # --------------------------------------------------------------
    @app.cli.command("init-db")
    def init_db():
        """Create all tables (including SkillPost & Like)."""
        db.create_all()
        print("Database tables created!")

    # --------------------------------------------------------------
    # Root route – Serve GoalVerse 2.0 landing page (goalverse-github-ui.html)
    # --------------------------------------------------------------
    @app.route('/')
    def index():
        return render_template('goalverse-github-ui.html')

    # --------------------------------------------------------------
    # Optional: Keep old login/dashboard redirect at /home (if needed)
    # --------------------------------------------------------------
    @app.route('/home')
    def home():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard.index'))
        return redirect(url_for('auth.login'))

    # --------------------------------------------------------------
    # Ensure tables are created on first request (safe for dev)
    # --------------------------------------------------------------
    @app.before_request
    def create_tables():
        db.create_all()

    # --------------------------------------------------------------
    # Debug – show first 10 chars of API keys (helps spot missing .env)
    # --------------------------------------------------------------
    yt_key = os.getenv('YOUTUBE_API_KEY')
    gm_key = os.getenv('GEMINI_API_KEY')
    print("YouTube Key:", yt_key[:10] + "..." if yt_key else "MISSING")
    print("Gemini Key:",  gm_key[:10] + "..." if gm_key else "MISSING")

    return app


# ----------------------------------------------------------------------
# Run the app (only when executed directly)
# ----------------------------------------------------------------------
if __name__ == '__main__':
    create_app().run(debug=True)