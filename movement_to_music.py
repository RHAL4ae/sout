import os
import pandas as pd
from mido import MidiFile, MidiTrack, Message, MetaMessage, second2tick
from database import get_movement_track_by_id

def compose_midi(track_id):
    """Generate a MIDI file from a movement track and return its file path."""
    # Retrieve track
    track = get_movement_track_by_id(track_id)
    if not track:
        raise ValueError("Track not found")
    # Read CSV and detect timestamp column
    df = pd.read_csv(track.raw_path)
    # Identify timestamp-like column
    ts_col = None
    for c in df.columns:
        if c.lower() == 'timestamp':
            ts_col = c
            break
    if not ts_col:
        for c in df.columns:
            if 'time' in c.lower():
                ts_col = c
                break
    if not ts_col:
        raise ValueError(f"Missing timestamp column in CSV. Found columns: {list(df.columns)}")
    # Parse dates in timestamp column
    df[ts_col] = pd.to_datetime(df[ts_col])
    # Standardize column name
    if ts_col != 'timestamp':
        df.rename(columns={ts_col: 'timestamp'}, inplace=True)
    df = df.sort_values('timestamp')
    # Create MIDI file and track
    midi = MidiFile()
    midi_track = MidiTrack()
    midi.tracks.append(midi_track)
    # Set default tempo (microseconds per beat)
    tempo = 500000
    midi_track.append(MetaMessage('set_tempo', tempo=tempo, time=0))
    ticks_per_beat = midi.ticks_per_beat
    # Use fixed note (C4) for events
    base_note = 60
    prev_ts = None
    for _, row in df.iterrows():
        ts = row['timestamp']
        if prev_ts is None:
            prev_ts = ts
            continue
        # Time delta in seconds
        dt = (ts - prev_ts).total_seconds()
        prev_ts = ts
        # Convert seconds to MIDI ticks
        ticks = int(second2tick(dt, ticks_per_beat, tempo))
        # Note on/off events
        midi_track.append(Message('note_on', note=base_note, velocity=64, time=0))
        midi_track.append(Message('note_off', note=base_note, velocity=64, time=ticks))
    # Prepare output directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(project_root, 'static', 'music')
    os.makedirs(out_dir, exist_ok=True)
    # Save MIDI file
    filename = f"tactical_track_{track_id}.mid"
    output_path = os.path.join(out_dir, filename)
    midi.save(output_path)
    return output_path
