from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
import requests, base64, time
from models import db

bp = Blueprint('code', __name__)

JUDGE0_URL = "https://ce.judge0.com/submissions"

@bp.route('/code')
@login_required
def code_page():
    return render_template('code.html')

@bp.route('/run', methods=['POST'])
@login_required
def run():
    data = request.json
    code = data['code']
    lang = data.get('lang', 'python')

    lang_map = {'python': 71, 'javascript': 63, 'java': 62, 'c': 50, 'cpp': 54}
    lang_id = lang_map.get(lang, 71)

    payload = {
        "source_code": base64.b64encode(code.encode()).decode(),
        "language_id": lang_id,
        "stdin": ""
    }

    r = requests.post(f"{JUDGE0_URL}?base64_encoded=true&fields=*", json=payload, timeout=10)
    token = r.json()['token']

    for _ in range(15):
        time.sleep(1)
        res = requests.get(f"{JUDGE0_URL}/{token}?base64_encoded=true&fields=*")
        data = res.json()
        if data['status']['id'] in (3, 4):
            output = base64.b64decode(data['stdout'] or '').decode() if data['stdout'] else ''
            error = base64.b64decode(data['stderr'] or '').decode() if data['stderr'] else ''
            current_user.update_streak()
            db.session.commit()
            return jsonify({'output': output, 'error': error})
    return jsonify({'error': 'Timeout'})