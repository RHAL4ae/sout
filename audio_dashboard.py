import os
import librosa
import librosa.display
import numpy as np
import matplotlib.pyplot as plt
from flask import Blueprint, render_template, jsonify, current_app, send_from_directory, url_for
from flask_login import login_required

# Blueprint for audio dashboard
dashboard_blueprint = Blueprint('dashboard_blueprint', __name__)

@dashboard_blueprint.route('/')
@login_required
def index_dashboard():
    """Render dashboard with list of audio sessions."""
    uploads = current_app.config['UPLOAD_FOLDER']
    sessions_dir = os.path.join(uploads, 'audio_sessions')
    sessions = []
    if os.path.isdir(sessions_dir):
        sessions = sorted(os.listdir(sessions_dir))
    return render_template('dashboard.html', sessions=sessions)

@dashboard_blueprint.route('/api/session/<session_id>')
@login_required
def session_data(session_id):
    """Return JSON with channels' audio URLs and spectrograms."""
    uploads = current_app.config['UPLOAD_FOLDER']
    session_dir = os.path.join(uploads, 'audio_sessions', session_id)
    channels = []
    if not os.path.isdir(session_dir):
        return jsonify({'channels': []})
    for fname in os.listdir(session_dir):
        if not fname.lower().endswith(('.wav', '.mp3', '.flac', '.ogg')):
            continue
        # generate spectrogram if missing
        spec_name = f"{session_id}_{fname}.png"
        spec_path = os.path.join(current_app.root_path, 'static', 'plots', spec_name)
        if not os.path.exists(spec_path):
            y, sr = librosa.load(os.path.join(session_dir, fname), sr=None)
            S = librosa.stft(y)
            S_db = librosa.amplitude_to_db(np.abs(S), ref=np.max)
            plt.figure(figsize=(8, 4))
            librosa.display.specshow(S_db, sr=sr, x_axis='time', y_axis='log')
            plt.colorbar(format='%+2.0f dB')
            plt.title(f"Spectrogram {session_id} - {fname}")
            plt.tight_layout()
            os.makedirs(os.path.dirname(spec_path), exist_ok=True)
            plt.savefig(spec_path)
            plt.close()
        audio_url = url_for('dashboard_blueprint.serve_audio', session_id=session_id, filename=fname)
        spec_url = url_for('static', filename=os.path.join('plots', spec_name))
        channels.append({'channel': fname, 'audio_url': audio_url, 'spectrogram_url': spec_url})
    return jsonify({'channels': channels})

@dashboard_blueprint.route('/audio/<session_id>/<filename>')
@login_required
def serve_audio(session_id, filename):
    """Serve raw audio file from uploads."""
    uploads = current_app.config['UPLOAD_FOLDER']
    path = os.path.join(uploads, 'audio_sessions', session_id)
    return send_from_directory(path, filename)
