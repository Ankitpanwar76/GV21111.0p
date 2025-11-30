# routes/skillshare.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from  models import db, SkillPost, Like
import os
import uuid
from werkzeug.utils import secure_filename

# Create the blueprint
skillshare = Blueprint(
    'skillshare', __name__,
    template_folder='../templates/skillshare',
    url_prefix='/skillshare'
)

# Allowed video extensions
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ———————————————————————— Routes ————————————————————————

@skillshare.route('/')
def index():
    posts = SkillPost.query.order_by(SkillPost.created_at.desc()).all()
    return render_template('index.html', posts=posts)

@skillshare.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        file = request.files.get('video')

        if not title or not file:
            flash('Title and video are required.', 'error')
            return redirect(request.url)

        if not allowed_file(file.filename):
            flash('Only MP4, MOV, AVI files are allowed.', 'error')
            return redirect(request.url)

        # Generate unique filename
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Save to DB
        post = SkillPost(
            title=title,
            description=description,
            video_filename=filename,
            user_id=current_user.id
        )
        db.session.add(post)
        db.session.commit()

        flash('Video uploaded successfully!', 'success')
        return redirect(url_for('skillshare.index'))

    return render_template('upload.html')

@skillshare.route('/like/<int:post_id>', methods=['POST'])
@login_required
def like(post_id):
    post = SkillPost.query.get_or_404(post_id)
    existing_like = Like.query.filter_by(user_id=current_user.id, post_id=post_id).first()

    if existing_like:
        db.session.delete(existing_like)
        db.session.commit()
        flash('Unliked.', 'info')
    else:
        like = Like(user_id=current_user.id, post_id=post_id)
        db.session.add(like)
        db.session.commit()
        flash('Liked!', 'success')

    return redirect(url_for('skillshare.index'))