from flask import Blueprint, render_template, request, jsonify, session
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
import json, os
from flask_login import login_required, current_user
from models import db, Documentation

bp = Blueprint('gemini', __name__)
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

# Define the structured output schema for the quiz
QUIZ_SCHEMA = {
    "type": "array",
    "description": "An array of multiple-choice questions.",
    "items": {
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "The quiz question."},
            "options": {
                "type": "array",
                "items": {"type": "string", "description": "A single option, starting with its letter (e.g., 'A: ...')."}
            },
            "correct": {"type": "string", "description": "The letter corresponding to the correct option (e.g., 'A', 'B', 'C', or 'D')."}
        },
        "required": ["question", "options", "correct"]
    }
}

@bp.route('/docs')
@login_required
def docs_page():
    return render_template('docs.html')

@bp.route('/generate-docs', methods=['POST'])
@login_required
def generate_docs():
    topic = request.json.get('topic')
    if not topic:
        return jsonify({'error': 'Topic required'}), 400

    model = genai.GenerativeModel('gemini-2.5-flash')
    prompt = f"""Write a concise learning document for "{topic}" in Markdown.
Include: definition, key points, one code example, common pitfalls. Under 800 words."""
    resp = model.generate_content(prompt)
    markdown = resp.text.strip()

    doc = Documentation(user_id=current_user.id, topic=topic, markdown=markdown)
    db.session.add(doc)
    db.session.commit()
    current_user.log_learning(topic, 'docs')

    return jsonify({'markdown': markdown})

@bp.route('/quiz')
@login_required
def quiz_page():
    return render_template('quiz.html')

@bp.route('/generate-quiz', methods=['POST'])
@login_required
def generate_quiz():
    data = request.json
    topic = data.get('topic')
    num = int(data.get('num', 5))
    if not topic:
        return jsonify({'error': 'Topic required'}), 400

    model = genai.GenerativeModel('gemini-2.5-flash') 
    
    # 1. Define the configuration to force structured JSON output
    config = GenerationConfig(
        response_mime_type="application/json",
        response_schema=QUIZ_SCHEMA
    )
    
    # 2. Simplify the prompt since the model is now forced to follow the schema
    prompt = f"Generate {num} multiple-choice questions on the topic: '{topic}'."
    
    # 3. Pass the configuration to the content generation call
    try:
        # FIX: Changed 'config' to 'generation_config' to match the SDK's expected argument name
        resp = model.generate_content(prompt, generation_config=config)
    except Exception as e:
        # Handle API call failures (e.g., network, authentication, etc.)
        print(f"Gemini API Call Error: {e}")
        return jsonify({'error': f'Failed to call Gemini API: {e}'}), 500

    try:
        # Since the model is configured for JSON, the response text should be clean JSON
        quiz = json.loads(resp.text.strip())
    except Exception as e:
        # If parsing still fails (highly unlikely with structured output)
        print(f"CRITICAL JSON Parse Error: {e}")
        print(f"Raw response text: {resp.text}")
        # Returning 500 here means we've definitively failed to process the request.
        return jsonify({'error': 'Failed to parse structured response. Check server console for raw text.'}), 500

    session['current_quiz'] = quiz
    return jsonify(quiz)

@bp.route('/submit-quiz', methods=['POST'])
@login_required
def submit_quiz():
    answers = request.json.get('answers', {})
    quiz = session.get('current_quiz', [])
    score = sum(1 for q in quiz if answers.get(q['question']) == q['correct'])
    current_user.update_streak()
    db.session.commit()
    return jsonify({'score': score, 'total': len(quiz)})
