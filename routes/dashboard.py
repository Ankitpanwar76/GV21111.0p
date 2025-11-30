from flask import Blueprint, render_template
from flask_login import login_required, current_user
from models import PlaylistItem, Documentation

bp = Blueprint('dashboard', __name__)

@bp.route('/dashboard')
@login_required
def index():
    recent_playlists = PlaylistItem.query.filter_by(user_id=current_user.id)\
        .order_by(PlaylistItem.searched_at.desc()).limit(6).all()
    recent_docs = Documentation.query.filter_by(user_id=current_user.id)\
        .order_by(Documentation.generated_at.desc()).limit(5).all()

    return render_template('dashboard.html',
                           user=current_user,
                           recent_playlists=recent_playlists,
                           recent_docs=recent_docs)