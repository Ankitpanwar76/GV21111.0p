# routes/youtube.py
from flask import Blueprint, render_template, request, jsonify
import requests
from config import Config
from flask_login import login_required, current_user
from models import db, PlaylistItem
import isodate
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import re

bp = Blueprint('youtube', __name__)

# ----------------- Filters -----------------
MIN_VIEWS = 20
MAX_RESULTS = 10
BLACKLIST_WORDS = ['strategy', 'motivational', 'tips', 'hack', 'vlog', 'challenge', 'story', 'reaction']

# ----------------- Routes -----------------
@bp.route('/playlists')
@login_required
def playlists_page():
    return render_template('playlists.html')

# ----------------- Helper Functions -----------------
def build_query(topic, level):
    base_keywords = ["tutorial", "course", "lesson", "study", "explained", "step-by-step", "project"]

    if level == 'basic':
        level_keywords = ["beginner", "intro", "basics", "starter", "easy"]
    elif level == 'medium':
        level_keywords = ["intermediate", "example", "practice", "implementation", "real-world"]
    elif level == 'hard':
        level_keywords = ["advanced", "expert", "in-depth", "masterclass", "complete guide"]
    else:
        level_keywords = []

    keywords = base_keywords + level_keywords
    query = f"{topic} {' '.join(keywords)}"
    return query

def get_positive_comments(video_id, max_comments=3):
    try:
        url = 'https://www.googleapis.com/youtube/v3/commentThreads'
        params = {
            'part': 'snippet',
            'videoId': video_id,
            'maxResults': max_comments,
            'order': 'relevance',
            'textFormat': 'plainText',
            'key': Config.YOUTUBE_API_KEY
        }
        res = requests.get(url, params=params).json()
        comments = []
        for item in res.get('items', []):
            snippet = item['snippet']['topLevelComment']['snippet']
            text = snippet['textDisplay']
            if snippet.get('likeCount', 0) > 0:
                comments.append(text)
        return comments
    except:
        return []

def transcript_match_score(video_id, topic):
    """Return relevance score (0 to 1) based on transcript matching"""
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = " ".join([t['text'] for t in transcript_list]).lower()
        topic_words = re.findall(r'\w+', topic.lower())
        match_count = sum(1 for word in topic_words if word in transcript_text)
        return match_count / len(topic_words) if topic_words else 0
    except (TranscriptsDisabled, NoTranscriptFound):
        return 0
    except:
        return 0

# ----------------- Main Search -----------------
@bp.route('/search')
@login_required
def search():
    topic = request.args.get('q', '').strip()
    level = request.args.get('level', 'medium')

    if not topic:
        return jsonify([])

    query = build_query(topic, level)
    search_url = 'https://www.googleapis.com/youtube/v3/search'
    search_params = {
        'part': 'snippet',
        'q': query,
        'type': 'video',
        'maxResults': 30,
        'key': Config.YOUTUBE_API_KEY
    }

    try:
        search_res = requests.get(search_url, params=search_params).json()
        videos = search_res.get('items', [])
    except Exception as e:
        print("Search API Error:", e)
        return jsonify([])

    results = []
    seen_video_ids = set()

    for video in videos:
        vid = video['id'].get('videoId')
        if not vid or vid in seen_video_ids:
            continue

        title_lower = video['snippet']['title'].lower()
        if any(word in title_lower for word in BLACKLIST_WORDS):
            continue

        stats_url = 'https://www.googleapis.com/youtube/v3/videos'
        stats_params = {'part': 'statistics,contentDetails', 'id': vid, 'key': Config.YOUTUBE_API_KEY}
        try:
            stats_res = requests.get(stats_url, params=stats_params).json()
            items_stats = stats_res.get('items', [])
            if not items_stats:
                continue
        except:
            continue

        video_info = items_stats[0]
        stats = video_info.get('statistics', {})
        details = video_info.get('contentDetails', {})

        views = int(stats.get('viewCount', 0))
        likes = int(stats.get('likeCount', 0))
        total_comments = int(stats.get('commentCount', 0))
        duration = isodate.parse_duration(details.get('duration', 'PT0S')).total_seconds() / 60

        if duration < 1 or views < MIN_VIEWS:
            continue

        like_ratio = (likes / views) * 100 if views else 0
        comments = get_positive_comments(vid)
        positive_comment_percentage = round((len(comments) / total_comments) * 100, 1) if total_comments else 0
        watch_hours = round((views * duration) / 60, 1)
        transcript_score = transcript_match_score(vid, topic)

        # ----------------- Smart Score -----------------
        score = (
            transcript_score * 0.5 +         # 50% transcript match
            min(like_ratio/100, 1) * 0.2 +  # 20% like ratio
            min(watch_hours/1000, 1) * 0.15 + # 15% watch hours (scaled)
            (positive_comment_percentage/100) * 0.15  # 15% positive comments
        ) * 100  # convert to 0-100 scale

        # Save to DB
        try:
            pl_item = PlaylistItem(
                user_id=current_user.id,
                topic=topic,
                difficulty=level,
                title=video['snippet']['title'],
                url=f"https://www.youtube.com/watch?v={vid}",
                thumbnail=video['snippet']['thumbnails']['medium']['url'],
                channel=video['snippet']['channelTitle']
            )
            db.session.add(pl_item)
            db.session.commit()
        except:
            pass

        results.append({
            'title': video['snippet']['title'],
            'id': vid,
            'thumb': video['snippet']['thumbnails']['medium']['url'],
            'channel': video['snippet']['channelTitle'],
            'views': views,
            'likes': likes,
            'duration': round(duration, 1),
            'watch_hours': watch_hours,
            'positive_comments': comments,
            'positive_comment_percentage': positive_comment_percentage,
            'like_ratio': round(like_ratio, 1),
            'transcript_score': round(transcript_score*100,1),
            'score': round(score, 1)
        })

        seen_video_ids.add(vid)

    # Sort by smart score
    results = sorted(results, key=lambda x: x['score'], reverse=True)

    try:
        current_user.log_learning(topic, 'video', level)
    except:
        pass

    return jsonify(results)
