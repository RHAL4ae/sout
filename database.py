from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, Enum, text, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
import enum
from werkzeug.security import generate_password_hash, check_password_hash

# Create the engine
engine = create_engine('sqlite:///military_music.db')
Base = declarative_base()
Session = sessionmaker(bind=engine)

class AccessLevel(enum.Enum):
    VISITOR = 0      # Read-only access to public files
    ARCHIVIST = 10   # Can upload and edit metadata
    ANALYST = 20     # Can analyze and generate reports
    COMMANDER = 30   # Full access including user management
    ADMIN = 100      # System administrator

from flask_login import UserMixin

class User(Base, UserMixin):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    rank = Column(String(50))
    unit = Column(String(100))
    access_level = Column(Enum(AccessLevel), default=AccessLevel.VISITOR)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    
    # One-to-many relationship: one user can upload many files
    uploaded_files = relationship("MusicFile", back_populates="uploader")
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', access_level={self.access_level})>"
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def has_permission(self, required_level):
        return self.access_level.value >= required_level.value if isinstance(required_level, AccessLevel) else False

    # Flask-Login integration
    def get_id(self):
        """Return the user ID as a string for session serialization."""
        return str(self.id)
    
class MusicFile(Base):
    __tablename__ = 'music_files'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    artist = Column(String(100))
    filename = Column(String(255), nullable=False, unique=True)
    original_filename = Column(String(255))
    file_path = Column(String(255), nullable=False)
    file_type = Column(String(10))
    category = Column(String(50))
    tags = Column(String(255))
    description = Column(Text) # Manual description
    ai_description = Column(Text) # AI-generated description
    ai_image_path = Column(String(255))  # Path to AI-generated image
    features = Column(Text)  # JSON string of audio features
    tempo = Column(Float)
    energy = Column(Float)
    mood = Column(String(50))
    plot_path = Column(String(255))
    classification_level = Column(String(50), default="Unclassified")  # Security classification
    access_restriction = Column(String(255))  # Units/ranks with access
    rhythmic_precision = Column(Float)
    harmonic_cohesion = Column(Float)
    individual_performance_quality = Column(Float)
    responsiveness_to_conducting = Column(Float)
    musical_diversity = Column(Float)
    upload_date = Column(DateTime, default=datetime.utcnow)
    
    # Foreign key to track who uploaded the file
    uploader_id = Column(Integer, ForeignKey('users.id'))
    uploader = relationship("User", back_populates="uploaded_files")
    
    def __repr__(self):
        return f"<MusicFile(id={self.id}, title='{self.title}')>"

class MovementTrack(Base):
    __tablename__ = 'movement_tracks'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    uploader_id = Column(Integer, ForeignKey('users.id'))
    upload_ts = Column(DateTime, default=datetime.utcnow)
    raw_path = Column(String(255), nullable=False)

    uploader = relationship("User")

    def __repr__(self):
        return f"<MovementTrack(id={self.id}, name='{self.name}')>"

# Model for alerts on non-measurable metrics
class Alert(Base):
    __tablename__ = 'alerts'

    id = Column(Integer, primary_key=True)
    metric = Column(String(100), nullable=False)
    message = Column(String(255), nullable=False)
    file_id = Column(Integer, ForeignKey('music_files.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship to MusicFile
    music_file = relationship('MusicFile')

def init_db():
    """Initialize the database, creating tables if they don't exist."""
    # Create plots directory
    os.makedirs('static/plots', exist_ok=True)
    
    # Create database tables (will create tables if they don't exist)
    Base.metadata.create_all(engine)

    # ------------------------------------------------------------------
    # Lightweight, in-place schema migration for SQLite
    # ------------------------------------------------------------------
    # Some new columns may have been added to the SQLAlchemy models after
    # the initial database file was created. SQLite does not support many
    # ALTER operations, but adding a new column is possible.  We therefore
    # inspect the existing schema and add any missing columns for the
    # music_files table so that the application can run without manual
    # intervention or a full migration framework.

    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    # Only attempt to patch the schema if the table already exists
    if 'music_files' in existing_tables:
        existing_columns = {col['name'] for col in inspector.get_columns('music_files')}

        with engine.begin() as conn:
            # Add security classification column if missing
            if 'classification_level' not in existing_columns:
                conn.execute(
                    text(
                        """
                        ALTER TABLE music_files
                        ADD COLUMN classification_level VARCHAR(50) DEFAULT 'Unclassified'
                        """
                    )
                )

            # Add access restriction column if missing
            if 'access_restriction' not in existing_columns:
                conn.execute(
                    text(
                        """
                        ALTER TABLE music_files
                        ADD COLUMN access_restriction VARCHAR(255)
                        """
                    )
                )

            # Add plot_path column if missing (older DBs may lack it)
            if 'plot_path' not in existing_columns:
                conn.execute(
                    text(
                        """
                        ALTER TABLE music_files
                        ADD COLUMN plot_path VARCHAR(255)
                        """
                    )
                )

            # Add uploader_id column if missing (legacy DBs)
            if 'uploader_id' not in existing_columns:
                conn.execute(
                    text(
                        """
                        ALTER TABLE music_files
                        ADD COLUMN uploader_id INTEGER
                        """
                    )
                )

            # Add ai_description column if missing
            if 'ai_description' not in existing_columns:
                conn.execute(
                    text(
                        """
                        ALTER TABLE music_files
                        ADD COLUMN ai_description TEXT
                        """
                    )
                )

            # Add ai_image_path column if missing
            if 'ai_image_path' not in existing_columns:
                conn.execute(
                    text(
                        """
                        ALTER TABLE music_files
                        ADD COLUMN ai_image_path VARCHAR(255)
                        """
                    )
                )

            # Add new KPI columns if missing
            if 'rhythmic_precision' not in existing_columns:
                conn.execute(text("ALTER TABLE music_files ADD COLUMN rhythmic_precision FLOAT"))
            if 'harmonic_cohesion' not in existing_columns:
                conn.execute(text("ALTER TABLE music_files ADD COLUMN harmonic_cohesion FLOAT"))
            if 'individual_performance_quality' not in existing_columns:
                conn.execute(text("ALTER TABLE music_files ADD COLUMN individual_performance_quality FLOAT"))
            if 'responsiveness_to_conducting' not in existing_columns:
                conn.execute(text("ALTER TABLE music_files ADD COLUMN responsiveness_to_conducting FLOAT"))
            if 'musical_diversity' not in existing_columns:
                conn.execute(text("ALTER TABLE music_files ADD COLUMN musical_diversity FLOAT"))

    # ------------------------------------------------------------------

    # Create initial admin user if none exists
    create_default_admin()

def create_default_admin():
    """Create a default admin user if no users exist."""
    session = Session()
    
    try:
        # Check if any users exist
        user_count = session.query(User).count()
        
        if user_count == 0:
            # Create default admin
            admin = User(
                username="admin",
                email="admin@military-music.gov.ae",
                full_name="System Administrator",
                rank="System",
                access_level=AccessLevel.ADMIN,
                is_active=True
            )
            admin.set_password("ChangeMe123!")  # Default password that must be changed
            
            session.add(admin)
            session.commit()
            print("Created default admin user. Please change the password immediately.")
    
    except Exception as e:
        session.rollback()
        print(f"Error creating default admin: {e}")
    
    finally:
        session.close()

def add_user(username, email, password, full_name, rank=None, unit=None, access_level=AccessLevel.VISITOR):
    """Add a new user to the database."""
    session = Session()
    
    try:
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            rank=rank,
            unit=unit,
            access_level=access_level
        )
        user.set_password(password)
        
        session.add(user)
        session.commit()
        return user
    
    except Exception as e:
        session.rollback()
        raise e
    
    finally:
        session.close()

def get_user_by_id(user_id):
    """Get a user by ID."""
    session = Session()
    try:
        user = session.query(User).filter(User.id == user_id).first()
        return user
    finally:
        session.close()

def get_user_by_username(username):
    """Get a user by username."""
    session = Session()
    try:
        user = session.query(User).filter(User.username == username).first()
        return user
    finally:
        session.close()

def get_user_by_email(email):
    """Get a user by email."""
    session = Session()
    
    try:
        return session.query(User).filter(User.email == email).first()
    
    finally:
        session.close()

def update_last_login(user_id):
    """Update user's last login time."""
    session = Session()
    
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if user:
            user.last_login = datetime.utcnow()
            session.commit()
    
    finally:
        session.close()

def add_music_file(**kwargs):
    """Add a new music file to the database."""
    session = Session()
    try:
        # Extract audio features for specific columns if available
        features = kwargs.get('features', '{}')
        import json
        features_dict = json.loads(features)
        if 'tempo' in features_dict:
            kwargs.setdefault('tempo', features_dict['tempo'])
        if 'energy' in features_dict:
            kwargs.setdefault('energy', features_dict['energy'])
        if 'mood' in features_dict:
            kwargs.setdefault('mood', features_dict['mood'])
        # Map new KPI fields if present
        if 'rhythmic_precision' in features_dict:
            kwargs.setdefault('rhythmic_precision', features_dict['rhythmic_precision'])
        if 'harmonic_cohesion' in features_dict:
            kwargs.setdefault('harmonic_cohesion', features_dict['harmonic_cohesion'])
        if 'individual_performance_quality' in features_dict:
            kwargs.setdefault('individual_performance_quality', features_dict['individual_performance_quality'])
        if 'responsiveness_to_conducting' in features_dict:
            kwargs.setdefault('responsiveness_to_conducting', features_dict['responsiveness_to_conducting'])
        if 'musical_diversity' in features_dict:
            kwargs.setdefault('musical_diversity', features_dict['musical_diversity'])
            
        # Ensure ai_description is handled (even if None)
        if 'ai_description' not in kwargs:
            kwargs['ai_description'] = None
            
        # Create and add new MusicFile
        music_file = MusicFile(**kwargs)
        session.add(music_file)
        session.commit()
        mf_id = music_file.id  # Safely access ID before potential closure
        # Re-fetch to ensure the object is usable after session closure if needed elsewhere immediately
        # Or simply return the ID if that's sufficient for the caller
        # For now, let's return the fetched object for consistency
        return session.query(MusicFile).get(mf_id)
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def get_music_files():
    """Get all music files from the database."""
    session = Session()
    try:
        music_files = session.query(MusicFile).order_by(MusicFile.upload_date.desc()).all()
        return music_files
    finally:
        session.close()

def get_music_file_by_id(file_id):
    """Get a music file by its ID."""
    session = Session()
    try:
        music_file = session.query(MusicFile).filter(MusicFile.id == file_id).first()
        return music_file
    finally:
        session.close()

def search_music_files(query, category=None):
    """Search music files by query text and category."""
    session = Session()
    
    try:
        # Base query
        search_query = session.query(MusicFile)
        
        # Add filters
        if query:
            search_query = search_query.filter(
                (MusicFile.title.like(f'%{query}%')) |
                (MusicFile.artist.like(f'%{query}%')) |
                (MusicFile.tags.like(f'%{query}%')) |
                (MusicFile.description.like(f'%{query}%')) |
                (MusicFile.ai_description.like(f'%{query}%'))
            )
        
        if category:
            search_query = search_query.filter(MusicFile.category == category)
        
        # Execute and return results
        results = search_query.order_by(MusicFile.upload_date.desc()).all()
        return results
    
    finally:
        session.close()

def get_similar_files(file_id, feature_name, limit=5):
    """Get similar files based on a specific audio feature."""
    session = Session()
    
    try:
        # Get the reference file
        reference_file = session.query(MusicFile).filter(MusicFile.id == file_id).first()
        
        if not reference_file:
            return []
        
        # Get the reference feature value
        import json
        features = json.loads(reference_file.features)
        
        if feature_name not in features:
            return []
        
        reference_value = features[feature_name]
        
        # Query for similar files
        similar_files = []
        
        for file in session.query(MusicFile).filter(MusicFile.id != file_id).all():
            file_features = json.loads(file.features)
            
            if feature_name in file_features:
                file_value = file_features[feature_name]
                
                # Calculate similarity (simplified)
                if isinstance(reference_value, (int, float)) and isinstance(file_value, (int, float)):
                    similarity = abs(reference_value - file_value)
                    similar_files.append((file, similarity))
        
        # Sort by similarity and return top results
        similar_files.sort(key=lambda x: x[1])
        return [file for file, _ in similar_files[:limit]]
    
    finally:
        session.close()

def add_movement_track(name, uploader_id, raw_path):
    session = Session()
    try:
        track = MovementTrack(name=name, uploader_id=uploader_id, raw_path=raw_path)
        session.add(track)
        session.commit()
        # Return the track ID to avoid detached instance issues
        return track.id
    finally:
        session.close()

def get_movement_track_by_id(track_id):
    session = Session()
    try:
        return session.query(MovementTrack).filter(MovementTrack.id == track_id).first()
    finally:
        session.close()

def get_movement_tracks():
    session = Session()
    try:
        return session.query(MovementTrack).order_by(MovementTrack.upload_ts.desc()).all()
    finally:
        session.close()
