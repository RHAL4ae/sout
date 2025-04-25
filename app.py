import os
import json
import uuid
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory, flash, Response
import io
import csv
from werkzeug.utils import secure_filename
import sqlite3
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use Agg backend
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import openai # Import OpenAI library
import requests
import shutil
from audio_analyzer import generate_plot

API_URL = "https://api.piapi.ai"  # قاعدة PiAPI
API_KEY = "4bc53918155aaa9a113fae0fc3c343cc3c11d528fc58ab62290ce7896d1f8fad"

def generate_march(prompt: str, length_secs: int = 60):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "music-u",
        "task_type": "generate_music",
        "input": {
            "gpt_description_prompt": prompt,
            "lyrics_type": "instrumental",
            "length": length_secs,
            "format": "wav"
        }
    }
    resp = requests.post(f"{API_URL}/api/v1/task", json=payload, headers=headers)
    resp.raise_for_status()
    return resp.json()

# Import custom modules
import audio_analyzer
from database import init_db, MusicFile, User, add_music_file, get_music_files, get_music_file_by_id, search_music_files
from database import get_user_by_id, get_user_by_username, get_user_by_email, add_user, update_last_login, AccessLevel, Session
from database import add_movement_track, get_movement_track_by_id
from movement_to_music import compose_midi
from audio_dashboard import dashboard_blueprint
from analysis.routes import analysis_bp
from forms import LoginForm, RegistrationForm, UserProfileForm, AdminUserForm
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024  # 64MB max upload size
app.config['ALLOWED_EXTENSIONS'] = {'mp3', 'wav', 'ogg', 'flac'}
app.config['SECRET_KEY'] = 'military-music-archive-secret-key-2025'

# Load OpenAI API Key (Ensure this environment variable is set!)
try:
    openai.api_key = os.environ['OPENAI_API_KEY']
except KeyError:
    print("\n *** WARNING: OPENAI_API_KEY environment variable not set. AI description generation will be skipped. ***\n")
    openai.api_key = None # Indicate that the key is missing

# Make standard Python 'min' and 'max' available in templates
app.jinja_env.globals.update(min=min, max=max)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'الرجاء تسجيل الدخول للوصول إلى هذه الصفحة.'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    return get_user_by_id(int(user_id))

# Initialize database
init_db()

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Register audio dashboard blueprint
app.register_blueprint(dashboard_blueprint, url_prefix='/dashboard')
app.register_blueprint(analysis_bp)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Context processor to make current date available to all templates
@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

@app.route('/')
def index():
    music_files = get_music_files()
    return render_template('index.html', music_files=music_files)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = get_user_by_username(form.username.data)
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('هذا الحساب معطل. الرجاء التواصل مع المسؤول.', 'danger')
                return render_template('login.html', form=form)
            
            login_user(user, remember=form.remember_me.data)
            update_last_login(user.id)
            
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('index')
            
            flash(f'مرحباً بك {user.full_name}!', 'success')
            return redirect(next_page)
        else:
            flash('خطأ في اسم المستخدم أو كلمة المرور', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    logout_user()
    flash('تم تسجيل الخروج بنجاح', 'success')
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            user = add_user(
                username=form.username.data,
                email=form.email.data,
                password=form.password.data,
                full_name=form.full_name.data,
                rank=form.rank.data,
                unit=form.unit.data,
                access_level=AccessLevel.VISITOR  # Default access level
            )
            flash('تم تسجيل حسابك بنجاح! يمكنك الآن تسجيل الدخول.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'حدث خطأ: {str(e)}', 'danger')
    
    return render_template('register.html', form=form)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = UserProfileForm()
    
    if request.method == 'GET':
        form.email.data = current_user.email
        form.full_name.data = current_user.full_name
        form.rank.data = current_user.rank
        form.unit.data = current_user.unit
    
    if form.validate_on_submit():
        session = Session()
        try:
            user = session.query(User).filter(User.id == current_user.id).first()
            
            # Check password if trying to change it
            if form.new_password.data:
                if not form.current_password.data:
                    flash('يجب إدخال كلمة المرور الحالية لتغيير كلمة المرور', 'danger')
                    return render_template('profile.html', form=form)
                
                if not user.check_password(form.current_password.data):
                    flash('كلمة المرور الحالية غير صحيحة', 'danger')
                    return render_template('profile.html', form=form)
                
                user.set_password(form.new_password.data)
            
            # Check email uniqueness
            if user.email != form.email.data:
                existing_user = session.query(User).filter(User.email == form.email.data, User.id != current_user.id).first()
                if existing_user:
                    flash('البريد الإلكتروني مستخدم بالفعل', 'danger')
                    return render_template('profile.html', form=form)
            
            # Update user data
            user.email = form.email.data
            user.full_name = form.full_name.data
            user.rank = form.rank.data
            user.unit = form.unit.data
            
            session.commit()
            flash('تم تحديث الملف الشخصي بنجاح', 'success')
            return redirect(url_for('profile'))
            
        except Exception as e:
            session.rollback()
            flash(f'حدث خطأ: {str(e)}', 'danger')
        finally:
            session.close()
    
    # Get user uploads count
    session = Session()
    uploads_count = session.query(MusicFile).filter(MusicFile.uploader_id == current_user.id).count()
    
    # Calculate days since last activity
    last_activity_days = 0
    if current_user.last_login:
        delta = datetime.utcnow() - current_user.last_login
        last_activity_days = delta.days
    
    # Get user files
    user_files = session.query(MusicFile).filter(MusicFile.uploader_id == current_user.id).order_by(MusicFile.upload_date.desc()).limit(5).all()
    session.close()
    
    # For analysis statistics - placeholder for now
    analyses_count = 0
    
    return render_template('profile.html', form=form, uploads_count=uploads_count, 
                          analyses_count=analyses_count, last_activity_days=last_activity_days,
                          user_files=user_files)

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_file():
    # Check if user has permission to upload
    if current_user.access_level.value < AccessLevel.ARCHIVIST.value:
        flash('ليس لديك صلاحية رفع الملفات', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        if file and allowed_file(file.filename):
            # Preserve the original filename
            original_filename = file.filename
            
            # Extract extension from the ORIGINAL filename
            if '.' in original_filename:
                file_extension = original_filename.rsplit('.', 1)[1].lower()
            else:
                # This case should technically not be reached if allowed_file passed
                return jsonify({'error': 'File extension missing or invalid.'}), 400

            # Generate a unique filename using UUID and the extracted extension
            unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
            
            # Use secure_filename ONLY for the path joining, if needed, but unique_filename is safer
            # safe_filename = secure_filename(original_filename) # No longer needed for extension extraction
            
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            
            # Extract tags and metadata from the form
            title = request.form.get('title', original_filename)
            artist = request.form.get('artist', 'Unknown')
            category = request.form.get('category', 'Unknown')
            tags = request.form.get('tags', '')
            description = request.form.get('description', '')
            classification_level = request.form.get('classification_level', 'Unclassified')
            access_restriction = request.form.get('access_restriction', '')
            
            # Analyze audio
            try:
                analysis_features = audio_analyzer.analyze_audio(file_path)
                
                # Generate plots
                plot_filename = f"{uuid.uuid4().hex}.png"
                plot_path = os.path.join('static', 'plots', plot_filename)
                audio_analyzer.generate_plot(analysis_features, os.path.join(app.root_path, plot_path))
                
                # --- OpenAI Description Generation ---
                ai_description = None
                if openai.api_key: # Only attempt if API key is set
                    try:
                        # Modified prompt to request Arabic output
                        prompt = (
                            f"أنشئ وصفًا موجزًا وموضوعيًا (2-3 جمل) باللغة العربية لمقطوعة موسيقية عسكرية بعنوان '{title}' "
                            f"للفنان '{artist}'. إيقاعها {analysis_features.get('tempo', 'غير متاح'):.1f} نبضة في الدقيقة، "
                            f"ومستوى طاقتها المتصور هو '{analysis_features.get('energy_level', 'غير متاح')}'، "
                            f"ومزاجها مصنف على أنه '{analysis_features.get('mood', 'غير متاح')}'. "
                            f"ركز على الآلات الموسيقية المحتملة، أو حالة الاستخدام النموذجية (مثل العرض العسكري، الاحتفال، القتال)، أو الإحساس العام."
                        )
                        
                        client = openai.OpenAI() # Use the new client interface
                        response = client.chat.completions.create(
                            model="gpt-3.5-turbo", # Or a newer model like gpt-4
                            messages=[{"role": "system", "content": "أنت مساعد مفيد يصف الموسيقى العسكرية باللغة العربية."}, # Adjusted system message too
                                      {"role": "user", "content": prompt}],
                            max_tokens=150, # Slightly increased tokens for potentially longer Arabic phrases
                            temperature=0.6 # Slightly adjusted temperature for potentially more creative Arabic phrasing
                        )
                        if response.choices:
                            ai_description = response.choices[0].message.content.strip()
                        else:
                             print("OpenAI API call succeeded but returned no description.")
                    except Exception as ai_error:
                        print(f"Error calling OpenAI API: {ai_error}") 
                        # Continue without AI description if API fails
                else:
                    print("Skipping AI description generation: OpenAI API key not configured.")
                # -------------------------------------

                # Add to database with uploader info and AI description
                music_file = add_music_file(
                    title=title,
                    artist=artist,
                    filename=unique_filename,
                    original_filename=original_filename,
                    file_path=file_path,
                    file_type=file_extension,
                    category=category,
                    tags=tags,
                    description=description, # Manual description
                    ai_description=ai_description, # AI-generated description
                    features=json.dumps(analysis_features),
                    plot_path=plot_path,
                    uploader_id=current_user.id,
                    classification_level=classification_level,
                    access_restriction=access_restriction
                )
                
                return jsonify({
                    'success': True,
                    'message': 'File uploaded, analyzed' + (', and AI description generated' if ai_description else ''),
                    'file_id': music_file.id
                })
            
            except Exception as e:
                # Remove the file if analysis fails
                if os.path.exists(file_path):
                    os.remove(file_path)
                return jsonify({'error': str(e)}), 500
        
        return jsonify({'error': 'File type not allowed'}), 400
    
    return render_template('upload.html')

@app.route('/file/<int:file_id>')
def file_details(file_id):
    music_file = get_music_file_by_id(file_id)
    if not music_file:
        return render_template('404.html'), 404
    
    # Check if file has access restrictions and user has appropriate access
    if music_file.classification_level != 'Unclassified' and (
        not current_user.is_authenticated or 
        current_user.access_level.value < AccessLevel.ANALYST.value):
        flash('ليس لديك صلاحية للوصول إلى هذا الملف المصنف', 'danger')
        return redirect(url_for('index'))
    
    # Parse features JSON
    features = json.loads(music_file.features)
    
    # Get uploader information
    uploader = None
    if music_file.uploader_id:
        uploader = get_user_by_id(music_file.uploader_id)
    
    return render_template('file_details.html', music_file=music_file, features=features, uploader=uploader)

@app.route('/download/<int:file_id>')
def download_file(file_id):
    music_file = get_music_file_by_id(file_id)
    if not music_file:
        return render_template('404.html'), 404
    
    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        music_file.filename,
        as_attachment=True,
        download_name=music_file.original_filename
    )

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        query = request.form.get('query', '')
        category = request.form.get('category', '')
        
        results = search_music_files(query, category)
        return render_template('search_results.html', query=query, category=category, results=results)
    
    return render_template('search.html')

@app.route('/analyze/<int:file_id>')
@login_required
def analyze_file(file_id):
    # Check if user has permission to access analysis
    if current_user.access_level.value < AccessLevel.ANALYST.value:
        flash('ليس لديك صلاحية للوصول إلى تحليلات الملفات', 'danger')
        return redirect(url_for('index'))
    
    music_file = get_music_file_by_id(file_id)
    if not music_file:
        return render_template('404.html'), 404
    
    features = json.loads(music_file.features)
    
    # Generate static plot for AI inspiration
    plot_path = os.path.join(app.root_path, 'static', 'plots', f"{music_file.id}_radar.png")
    try:
        generate_plot(features, plot_path)
    except Exception as e:
        flash(f"خطأ في إنشاء مخطط التحليل: {e}", 'danger')
    plot_url = url_for('static', filename=f"plots/{music_file.id}_radar.png")
    
    return render_template('analysis.html', music_file=music_file, features=features, plot_url=plot_url)

@app.route('/export/csv/<int:file_id>')
@login_required
def export_csv(file_id):
    music_file = get_music_file_by_id(file_id)
    if not music_file:
        return render_template('404.html'), 404
    if current_user.access_level.value < AccessLevel.ANALYST.value:
        flash('ليس لديك صلاحية لتصدير التحليل', 'danger')
        return redirect(url_for('analyze_file', file_id=file_id))
    features = json.loads(music_file.features)
    si = io.StringIO()
    writer = csv.writer(si)
    writer.writerow(['Metric', 'Value'])
    for key, value in features.items():
        writer.writerow([key, value if value is not None else 'غير قابل للقياس'])
    output = si.getvalue()
    return Response(output, mimetype='text/csv', headers={'Content-Disposition': f'attachment;filename=analysis_{file_id}.csv'})

@app.route('/tactical-music/upload', methods=['GET','POST'])
@login_required
def upload_track():
    if request.method == 'POST':
        file = request.files.get('file')
        name = request.form.get('name')
        if not file or file.filename == '':
            flash('يرجى اختيار ملف CSV.', 'danger')
            return redirect(request.url)
        if not file.filename.lower().endswith('.csv'):
            flash('الملف يجب أن يكون CSV.', 'danger')
            return redirect(request.url)
        filename = secure_filename(file.filename)
        raw_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'movement_tracks')
        os.makedirs(raw_dir, exist_ok=True)
        raw_path = os.path.join(raw_dir, f"{uuid.uuid4().hex}_{filename}")
        file.save(raw_path)
        track_id = add_movement_track(name=name, uploader_id=current_user.id, raw_path=raw_path)
        flash('تم رفع المسار بنجاح.', 'success')
        return redirect(url_for('compose_tactical', track_id=track_id))
    return render_template('tactical_upload.html')

@app.route('/tactical-music/compose/<int:track_id>')
@login_required
def compose_tactical(track_id):
    track = get_movement_track_by_id(track_id)
    if not track:
        flash('المسار غير موجود.', 'danger')
        return redirect(url_for('index'))
    midi_path = compose_midi(track_id)
    midi_filename = os.path.basename(midi_path)
    return render_template('tactical_compose.html', track=track, midi_filename=midi_filename)

@app.route('/generate-march', methods=['GET','POST'])
@login_required
def generate_march_page():
    """UI for user to input prompt and generate a march via PiAPI"""
    audio_url = None
    if request.method == 'POST':
        prompt = request.form.get('prompt', '')
        length = int(request.form.get('length', 60))
        try:
            audio_url = generate_march(prompt, length)
        except Exception as e:
            flash(f'خطأ في توليد المارش: {e}', 'danger')
    return render_template('generate_march.html', audio_url=audio_url)

@app.route('/generate-ai-image/<int:file_id>', methods=['POST'])
@login_required
def generate_ai_image(file_id):
    # Only analysts or above allowed
    if current_user.access_level.value < AccessLevel.ANALYST.value:
        flash('ليس لديك صلاحية لتوليد صور AI', 'danger')
        return redirect(url_for('file_details', file_id=file_id))
    
    session = Session()
    # Fetch the specific music file
    mf = session.query(MusicFile).filter(MusicFile.id == file_id).first()
    if not mf:
        session.close()
        flash('الملف غير موجود', 'danger')
        return redirect(url_for('index'))
    # If already has AI image, skip
    if mf.ai_image_path:
        session.close()
        flash('تم إنشاء صورة AI مسبقًا لهذا الملف', 'info')
        return redirect(url_for('file_details', file_id=file_id))
    # Build prompt
    prompt = f"Create a 512x512 abstract album cover for a military march titled '{mf.title}'. The design should reflect the mood '{mf.mood}', tempo {mf.tempo:.0f} BPM, and energy {mf.energy:.2f}. Use a military aesthetic with colors #5c4e2c, #191918, #a38d54, and #e3d195."
    try:
        # Generate image via OpenAI
        resp = openai.images.generate(prompt=prompt, n=1, size="512x512")
        image_url = resp.data[0].url
        # Download and save locally
        img_resp = requests.get(image_url)
        save_dir = os.path.join(app.root_path, 'static', 'images', 'ai')
        os.makedirs(save_dir, exist_ok=True)
        filename = f"{file_id}.png"
        file_path = os.path.join(save_dir, filename)
        with open(file_path, 'wb') as f:
            f.write(img_resp.content)
        # Update database record
        mf.ai_image_path = f"images/ai/{filename}"
        session.commit()
        flash('تم توليد وحفظ صورة AI بنجاح', 'success')
    except Exception as e:
        session.rollback()
        flash(f"خطأ في توليد أو حفظ صورة AI: {e}", 'danger')
    finally:
        session.close()
    return redirect(url_for('file_details', file_id=file_id))

@app.route('/admin/regenerate-images')
@login_required
def regenerate_images():
    # Only admins allowed
    if current_user.access_level.value < AccessLevel.ADMIN.value:
        flash('ليس لديك صلاحية لإعادة إنشاء الصور', 'danger')
        return redirect(url_for('admin_users'))
    session = Session()
    files = session.query(MusicFile).all()
    count = 0
    for mf in files:
        try:
            features = json.loads(mf.features)
            plot_file = os.path.join(app.root_path, 'static', 'plots', f"{mf.id}_radar.png")
            generate_plot(features, plot_file)
            count += 1
        except Exception:
            continue
    session.close()
    flash(f'تم إعادة إنشاء الصور لعدد {count} ملفًا.', 'success')
    return redirect(url_for('admin_users'))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

# Admin routes for user management
@app.route('/admin/users')
@login_required
def admin_users():
    if current_user.access_level.value < AccessLevel.COMMANDER.value:
        flash('ليس لديك صلاحية للوصول إلى إدارة المستخدمين', 'danger')
        return redirect(url_for('index'))
    
    session = Session()
    users = session.query(User).order_by(User.username).all()
    session.close()
    
    return render_template('admin_users.html', users=users)

@app.route('/admin/users/add', methods=['GET', 'POST'])
@login_required
def add_user_admin():
    if current_user.access_level.value < AccessLevel.COMMANDER.value:
        flash('ليس لديك صلاحية للوصول إلى إدارة المستخدمين', 'danger')
        return redirect(url_for('index'))
    
    form = AdminUserForm()
    
    if form.validate_on_submit():
        try:
            # Convert access level from form (which is int) to enum
            access_level = AccessLevel(form.access_level.data) if isinstance(form.access_level.data, int) else AccessLevel.VISITOR
            
            # Validate password is provided for new user
            if not form.password.data:
                flash('كلمة المرور مطلوبة للمستخدم الجديد', 'danger')
                return render_template('admin_user_form.html', form=form)
            
            # Create the user
            user = add_user(
                username=form.username.data,
                email=form.email.data,
                password=form.password.data,
                full_name=form.full_name.data,
                rank=form.rank.data,
                unit=form.unit.data,
                access_level=access_level
            )
            
            # Update active status if needed
            if not form.is_active.data:
                session = Session()
                db_user = session.query(User).filter(User.id == user.id).first()
                db_user.is_active = False
                session.commit()
                session.close()
            
            flash('تم إضافة المستخدم بنجاح', 'success')
            return redirect(url_for('admin_users'))
            
        except Exception as e:
            flash(f'حدث خطأ: {str(e)}', 'danger')
    
    return render_template('admin_user_form.html', form=form)

@app.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user_admin(user_id):
    if current_user.access_level.value < AccessLevel.COMMANDER.value:
        flash('ليس لديك صلاحية للوصول إلى إدارة المستخدمين', 'danger')
        return redirect(url_for('index'))
    
    session = Session()
    user = session.query(User).filter(User.id == user_id).first()
    
    if not user:
        session.close()
        flash('المستخدم غير موجود', 'danger')
        return redirect(url_for('admin_users'))
    
    # Prevent editing users with higher access level
    if user.access_level.value > current_user.access_level.value and current_user.access_level != AccessLevel.ADMIN:
        session.close()
        flash('لا يمكنك تعديل حساب مستخدم ذو صلاحيات أعلى', 'danger')
        return redirect(url_for('admin_users'))
    
    form = AdminUserForm(obj=user)
    form.user_id = user_id  # Pass the user ID to form validators
    
    if request.method == 'GET':
        form.access_level.data = user.access_level.value
        form.is_active.data = user.is_active
    
    if form.validate_on_submit():
        try:
            # Convert access level from form (which is int) to enum
            access_level = AccessLevel(form.access_level.data) if isinstance(form.access_level.data, int) else user.access_level
            
            # Update user data
            user.username = form.username.data
            user.email = form.email.data
            user.full_name = form.full_name.data
            user.rank = form.rank.data
            user.unit = form.unit.data
            user.access_level = access_level
            user.is_active = form.is_active.data
            
            # Update password if provided
            if form.password.data:
                user.set_password(form.password.data)
            
            session.commit()
            flash('تم تحديث بيانات المستخدم بنجاح', 'success')
            return redirect(url_for('admin_users'))
            
        except Exception as e:
            session.rollback()
            flash(f'حدث خطأ: {str(e)}', 'danger')
        finally:
            session.close()
    else:
        session.close()
    
    return render_template('admin_user_form.html', form=form, user=user)

@app.route('/admin/users/delete/<int:user_id>')
@login_required
def delete_user_admin(user_id):
    if current_user.access_level.value < AccessLevel.COMMANDER.value:
        flash('ليس لديك صلاحية للوصول إلى إدارة المستخدمين', 'danger')
        return redirect(url_for('index'))
    
    # Prevent deleting self
    if current_user.id == user_id:
        flash('لا يمكنك حذف حسابك الخاص', 'danger')
        return redirect(url_for('admin_users'))
    
    session = Session()
    user = session.query(User).filter(User.id == user_id).first()
    
    if not user:
        session.close()
        flash('المستخدم غير موجود', 'danger')
        return redirect(url_for('admin_users'))
    
    # Prevent deleting users with higher access level
    if user.access_level.value > current_user.access_level.value:
        session.close()
        flash('لا يمكنك حذف حساب مستخدم ذو صلاحيات أعلى', 'danger')
        return redirect(url_for('admin_users'))
    
    try:
        session.delete(user)
        session.commit()
        flash('تم حذف المستخدم بنجاح', 'success')
    except Exception as e:
        session.rollback()
        flash(f'حدث خطأ أثناء حذف المستخدم: {str(e)}', 'danger')
    finally:
        session.close()
    
    return redirect(url_for('admin_users'))

@app.route('/admin/users/toggle/<int:user_id>')
@login_required
def toggle_user_status(user_id):
    if current_user.access_level.value < AccessLevel.COMMANDER.value:
        flash('ليس لديك صلاحية للوصول إلى إدارة المستخدمين', 'danger')
        return redirect(url_for('index'))
    
    # Prevent toggling self
    if current_user.id == user_id:
        flash('لا يمكنك تغيير حالة حسابك الخاص', 'danger')
        return redirect(url_for('admin_users'))
    
    session = Session()
    user = session.query(User).filter(User.id == user_id).first()
    
    if not user:
        session.close()
        flash('المستخدم غير موجود', 'danger')
        return redirect(url_for('admin_users'))
    
    # Prevent modifying users with higher access level
    if user.access_level.value > current_user.access_level.value:
        session.close()
        flash('لا يمكنك تعديل حساب مستخدم ذو صلاحيات أعلى', 'danger')
        return redirect(url_for('admin_users'))
    
    try:
        # Toggle status
        user.is_active = not user.is_active
        session.commit()
        status = 'تنشيط' if user.is_active else 'تعطيل'
        flash(f'تم {status} حساب المستخدم بنجاح', 'success')
    except Exception as e:
        session.rollback()
        flash(f'حدث خطأ: {str(e)}', 'danger')
    finally:
        session.close()
    
    return redirect(url_for('admin_users'))

if __name__ == "__main__":
    # Create plots directory if it doesn't exist
    os.makedirs(os.path.join(app.root_path, 'static', 'plots'), exist_ok=True)
    # Ensure static/images exists and copy Logo.jpg for branding
    logo_src = os.path.join(app.root_path, 'Logo.jpg')
    logo_dest_dir = os.path.join(app.root_path, 'static', 'images')
    os.makedirs(logo_dest_dir, exist_ok=True)
    if os.path.isfile(logo_src):
        shutil.copy2(logo_src, os.path.join(logo_dest_dir, 'Logo.jpg'))
    app.run(debug=True)
