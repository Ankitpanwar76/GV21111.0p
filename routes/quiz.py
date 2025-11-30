from flask import Blueprint, render_template, request, jsonify, flash
from flask_login import login_required, current_user
import google.generativeai as genai
import json, os
from models import db

bp = Blueprint('quiz', __name__)

genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

@bp.route('/quiz')
@login_required
def quiz_page():
    return render_template('quiz.html')

@bp.route('/generate', methods=['POST'])
@login_required
def generate():
    data = request.json
    topic = data.get('topic')
    num = int(data.get('num', 5))
    if not topic:
        return jsonify({'error': 'Topic required'}), 400

    model = client.generative_model("gemini-2.5-flash")
    prompt = f"""Generate {num} multiple-choice quiz questions on "{topic}".
Each question must have exactly 4 options (A,B,C,D) and indicate the correct answer.
Return **only** a JSON array like:
[
  {{"question":"...", "options":["A: ...","B: ...","C: ...","D: ..."], "correct":"A"}},
  ...
]
"""
    resp = model.generate_content(prompt)
    try:
        quiz = json.loads(resp.text)
    except Exception:
        return jsonify({'error': 'Failed to parse quiz'}), 500

    # Store quiz in session for scoring later
    request.session['current_quiz'] = quiz
    return jsonify(quiz)

@bp.route('/submit', methods=['POST'])
@login_required
def submit():
    answers = request.json.get('answers', {})
    quiz = request.session.get('current_quiz', [])
    score = 0
    for q in quiz:
        if answers.get(q['question']) == q['correct']:
            score += 1

    # Update streak
    current_user.update_streak()
    db.session.commit()

    return jsonify({'score': score, 'total': len(quiz)})