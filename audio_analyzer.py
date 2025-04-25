import os
import librosa
import librosa.display
import numpy as np
import matplotlib.pyplot as plt
import json
from sklearn.preprocessing import MinMaxScaler

def analyze_audio(file_path):
    """
    Analyze audio file and extract musical features
    Returns a dictionary of features
    """
    try:
        # Load the audio file
        y, sr = librosa.load(file_path)
        
        # Extract features
        # Tempo
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)
        if len(beat_times) > 1:
            ibis = np.diff(beat_times)
            rhythmic_precision = max(0.0, 1 - np.std(ibis) / (np.mean(ibis) + 1e-6))
        else:
            rhythmic_precision = 0.0
        
        # Spectral features
        spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
        spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
        
        # Rhythm features
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        
        # MFCCs
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        
        # Energy
        energy = np.mean(librosa.feature.rms(y=y)[0])
        
        # Chromagram
        chroma = librosa.feature.chroma_stft(y=y, sr=sr)
        # Compute harmonic cohesion between consecutive chroma frames
        n_frames = chroma.shape[1]
        if n_frames > 1:
            corr_vals = []
            for i in range(n_frames-1):
                v1 = chroma[:, i]
                v2 = chroma[:, i+1]
                denom = np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6
                corr_vals.append(np.dot(v1, v2) / denom)
            harmonic_cohesion = float(np.clip(np.mean(corr_vals), 0.0, 1.0))
        else:
            harmonic_cohesion = 0.0
        
        # Individual performance and conductor responsiveness are not measurable from mixed stereo
        individual_performance_quality = None
        responsiveness_to_conducting = None
        
        # Compute musical diversity based on MFCC variability
        diversity = np.mean(np.std(mfccs, axis=1))
        musical_diversity = float(min(1.0, diversity / 20.0))
        
        # Determine mood based on features (simple implementation)
        # This is a very simplified mood detection and would need refinement
        mood = determine_mood(
            tempo=tempo,
            energy=energy,
            mfccs_mean=np.mean(mfccs[1:]),
            spectral_centroid_mean=np.mean(spectral_centroid)
        )
        
        # Determine type of march (if applicable)
        march_type = determine_march_type(tempo)
        
        # Calculate additional military music specific features
        rhythmic_regularity = calculate_rhythmic_regularity(onset_env)
        
        # Store all features
        features = {
            'tempo': float(tempo),
            'rhythmic_precision': float(rhythmic_precision),
            'harmonic_cohesion': float(harmonic_cohesion),
            'individual_performance_quality': None,
            'responsiveness_to_conducting': None,
            'musical_diversity': float(musical_diversity),
            'energy': float(energy),
            'mood': mood,
            'march_type': march_type,
            'rhythmic_regularity': float(rhythmic_regularity),
            'duration': float(len(y) / sr),
            'spectral_centroid_mean': float(np.mean(spectral_centroid)),
            'spectral_bandwidth_mean': float(np.mean(spectral_bandwidth)),
            'spectral_rolloff_mean': float(np.mean(spectral_rolloff)),
            'mfcc_means': [float(np.mean(mfcc)) for mfcc in mfccs],
            'chroma_means': [float(np.mean(c)) for c in chroma],
        }
        
        return features
    
    except Exception as e:
        print(f"Error analyzing audio: {str(e)}")
        raise

def determine_mood(tempo, energy, mfccs_mean, spectral_centroid_mean):
    """
    Determine the mood of the music based on audio features
    This is a simplified approach and could be improved with ML
    """
    # Normalize values 
    tempo_norm = min(tempo / 180.0, 1.0)  # Normalize tempo with 180 BPM as upper threshold
    
    # Calculate mood scores
    energy_factor = energy * 10  # Scale energy to be more influential
    
    # Basic mood scoring - could be replaced with a trained classifier
    if tempo_norm > 0.7 and energy_factor > 0.6:
        return "حماسي"  # Energetic/Enthusiastic
    elif tempo_norm > 0.6 and energy_factor > 0.4:
        return "عسكري رسمي"  # Formal/Official
    elif tempo_norm < 0.5 and energy_factor > 0.4:
        return "وقور"  # Solemn/Dignified
    elif tempo_norm < 0.5 and energy_factor < 0.4:
        return "هادئ"  # Calm/Relaxed
    else:
        return "متوسط"  # Neutral

def determine_march_type(tempo):
    """
    Determine the type of military march based on tempo
    """
    if tempo < 70:
        return "مارش بطيء للجنازات"  # Funeral march
    elif 70 <= tempo < 90:
        return "مارش احتفالي بطيء"  # Slow ceremonial march
    elif 90 <= tempo < 110:
        return "مارش عسكري قياسي"  # Standard military march
    elif 110 <= tempo < 130:
        return "مارش سريع للاستعراضات"  # Quick march for parades
    else:
        return "مارش سريع جداً"  # Very quick march
    
def calculate_rhythmic_regularity(onset_env):
    """
    Calculate the regularity of the rhythm
    Higher value = more regular/structured rhythm (typical for military music)
    """
    # Calculate the autocorrelation of onset strength
    acf = librosa.autocorrelate(onset_env, max_size=len(onset_env))
    
    # Normalize
    acf = acf / acf[0]
    
    # Measure of regularity: sum of first few autocorrelation peaks
    regularity = np.sum(acf[1:20])
    
    # Normalize to 0-1 range
    regularity = min(1.0, max(0.0, regularity / 10.0))
    
    return regularity

def generate_plot(features, output_path):
    """Generate visualization of the audio features and save to output_path"""
    plt.figure(figsize=(10, 6))
    
    # Prepare data for radar chart
    categories = ['إيقاع', 'طاقة', 'انتظام', 'تكرار', 'وضوح صوتي']
    values = [
        min(features['tempo'] / 180.0, 1.0),  # Normalize tempo 
        min(features['energy'] * 10, 1.0),    # Normalize energy
        features['rhythmic_regularity'],
        min(np.mean(features['chroma_means']), 1.0),  # Harmonic repetition
        min(features['spectral_centroid_mean'] / 3000, 1.0)  # Clarity
    ]
    
    # Close any previous plots
    plt.close('all')
    
    # Create radar chart
    angles = np.linspace(0, 2*np.pi, len(categories), endpoint=False).tolist()
    values += values[:1]  # Close the polygon
    angles += angles[:1]  # Close the polygon
    
    # Plot
    ax = plt.subplot(111, polar=True)
    ax.plot(angles, values, 'o-', linewidth=2)
    ax.fill(angles, values, alpha=0.25)
    ax.set_thetagrids(np.degrees(angles[:-1]), categories)
    
    # Add title and labels
    plt.title('تحليل خصائص الموسيقى العسكرية', fontsize=15, y=1.1)
    
    # Add feature text
    plt.figtext(0.5, 0.01, f"إيقاع: {features['tempo']:.1f} BPM | نوع: {features['march_type']}", 
               ha='center', fontsize=12)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Save plot
    plt.savefig(output_path, bbox_inches='tight', dpi=100)
    plt.close()
    
    return output_path
