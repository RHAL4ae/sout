from typing import Dict, Any
import librosa
import numpy as np
from scipy.signal import correlate
from sqlalchemy.orm import Session as DBSession

class AudioAnalyzer:
    """
    Analyze audio files and compute KPIs:
    - Rhythmic Precision
    - Harmonic Cohesion
    - Individual Performance Quality
    - Responsiveness to Conducting
    - Musical Diversity
    """
    def __init__(self, db_session: DBSession):
        self.db = db_session

    def analyze(self, file_path: str) -> Dict[str, Any]:
        y, sr = librosa.load(file_path, sr=None)
        # KPI computations
        metrics = {
            'rhythmic_precision': self._compute_rhythmic_precision(y, sr),
            'harmonic_cohesion': self._compute_harmonic_cohesion(y, sr),
            'performance_quality': self._compute_performance_quality(y, sr),
            'conducting_responsiveness': self._compute_responsiveness(y, sr),
            'musical_diversity': self._compute_diversity(y, sr)
        }
        return metrics

    def _compute_rhythmic_precision(self, y, sr):
        # Compare detected beats to ideal grid
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
        ideal_times = np.arange(beats[0], beats[-1], 60.0/tempo)
        diffs = np.abs(beats - ideal_times[:len(beats)])
        return float(1 - np.mean(diffs) / (60.0/tempo))

    def _compute_harmonic_cohesion(self, y, sr):
        # Chroma feature variance: low variance = more cohesion
        chroma = librosa.feature.chroma_stft(y=y, sr=sr)
        return float(1 - np.var(chroma))

    def _compute_performance_quality(self, y, sr):
        # Estimate noise floor vs signal
        power = np.mean(y**2)
        noise = np.mean((y - librosa.effects.hpss(y)[1])**2)
        return float(power / (power + noise))

    def _compute_responsiveness(self, y, sr):
        # Cross-correlation between ideal beat impulse and audio onset
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        ideal_impulse = np.zeros_like(onset_env)
        for i in librosa.beat.beat_track(y=y, sr=sr)[1]:
            ideal_impulse[int(i)] = 1
        corr = correlate(onset_env, ideal_impulse, mode='full')
        lag = corr.argmax() - len(onset_env) + 1
        return float(1 - abs(lag) / len(onset_env))

    def _compute_diversity(self, y, sr):
        # Spectral rolloff variance as proxy for diversity
        rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
        return float(np.var(rolloff))
