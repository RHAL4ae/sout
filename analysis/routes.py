from flask import Blueprint, request, jsonify
from sqlalchemy.orm import sessionmaker
from database import engine
from analysis.audio_analysis import AudioAnalyzer
from analysis.alert_system import AlertSystem
from database import Session, MusicFile, Alert
import pandas as pd
from io import BytesIO
import json

analysis_bp = Blueprint('analysis_bp', __name__, url_prefix='/api')

# Initialize DB session factory
SessionLocal = sessionmaker(bind=engine)

@analysis_bp.route('/analyze', methods=['POST'])
def analyze_audio():
    file_path = request.json.get('file_path')
    session = SessionLocal()
    analyzer = AudioAnalyzer(session)
    metrics = analyzer.analyze(file_path)
    # Save metrics to DB
    record = MusicFile(file_path=file_path, features=json.dumps(metrics))
    session.add(record)
    session.commit()
    return jsonify({'metrics': metrics}), 201

@analysis_bp.route('/metrics', methods=['GET'])
def get_metrics():
    session = SessionLocal()
    records = session.query(MusicFile).order_by(MusicFile.upload_date.desc()).all()
    metrics = [{
        'id': r.id,
        **json.loads(r.features)
    } for r in records]
    return jsonify({'metrics': metrics})

@analysis_bp.route('/alerts', methods=['POST'])
def get_alerts():
    observations = request.json.get('observations', {})
    alerts = AlertSystem().analyze_qualitative(observations)
    return jsonify(alerts)

@analysis_bp.route('/export', methods=['GET'])
def export_reports():
    fmt = request.args.get('format', 'pdf')
    session = SessionLocal()
    df = pd.read_sql(session.query(MusicFile).statement, session.bind)
    output = BytesIO()
    if fmt == 'excel':
        df.to_excel(output, index=False)
        content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    else:
        # PDF via pandas + reportlab
        from reportlab.platypus import SimpleDocTemplate, Table
        from reportlab.lib.pagesizes import letter
        pdf = SimpleDocTemplate(output, pagesize=letter)
        data = [list(df.columns)] + df.values.tolist()
        tbl = Table(data)
        pdf.build([tbl])
        content_type = 'application/pdf'
    output.seek(0)
    return (output.read(), 200, {'Content-Type': content_type, 'Content-Disposition': f'attachment; filename="report.{fmt}"'})

