from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.wave import WAVE
import mutagen
import os
import shutil
from config import UPLOAD_DIR, TEMP_DIR
from utils.db_utils import connect_db
from tkinter import messagebox
import mysql.connector

def get_audio_duration(file_path):
    """Get the duration of an audio file"""
    try:
        file_type = os.path.splitext(file_path)[1][1:].lower()
        
        if file_type == 'mp3':
            audio = MP3(file_path)
        elif file_type == 'flac':
            audio = FLAC(file_path)
        elif file_type in ['wav', 'wave']:
            audio = WAVE(file_path)
        else:
            # Fallback for other formats
            audio = mutagen.File(file_path)
            
        return int(audio.info.length)
    except Exception as e:
        print(f"Error getting audio duration: {e}")
        return 0

def upload_song_to_db(file_path, title, artist_id, genre_id=None, album_id=None):
    """Upload a song to the database"""
    try:
        if not os.path.exists(file_path):
            messagebox.showerror("Error", f"File not found: {file_path}")
            return None
        
        # Get file information
        file_size = os.path.getsize(file_path)
        file_type = os.path.splitext(file_path)[1][1:].lower()
        
        # Get song duration
        duration = get_audio_duration(file_path)
        
        # Read file binary data
        with open(file_path, 'rb') as file:
            file_data = file.read()
        
        # Insert into database
        connection = connect_db()
        if not connection:
            return None
            
        cursor = connection.cursor()
        
        query = """
        INSERT INTO Songs (title, artist_id, album_id, genre_id, duration, file_data, file_type, file_size)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        values = (title, artist_id, album_id, genre_id, duration, file_data, file_type, file_size)
        
        cursor.execute(query, values)
        connection.commit()
        
        # Return the new song ID
        new_song_id = cursor.lastrowid
        
        return new_song_id
        
    except mysql.connector.Error as e:
        print(f"Error uploading song: {e}")
        messagebox.showerror("Database Error", f"Failed to upload song: {e}")
        return None
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()

def get_song_data(song_id):
    """Get binary song data from database"""
    try:
        connection = connect_db()
        if not connection:
            return None
            
        cursor = connection.cursor()
        
        query = """
        SELECT s.file_data, s.file_type, s.title, a.name as artist_name 
        FROM Songs s
        JOIN Artists a ON s.artist_id = a.artist_id
        WHERE s.song_id = %s
        """
        cursor.execute(query, (song_id,))
        
        result = cursor.fetchone()
        if result:
            return {
                'data': result[0], 
                'type': result[1],
                'title': result[2],
                'artist': result[3]
            }
        return None
        
    except mysql.connector.Error as e:
        print(f"Error getting song data: {e}")
        return None
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()

def play_song_from_db(song_id, mixer, now_playing_label=None, play_btn=None):
    """Play a song from its binary data in the database"""
    try:
        # Get song data from database
        song_data = get_song_data(song_id)
        if not song_data:
            messagebox.showerror("Error", "Could not retrieve song data")
            return None
            
        # Create a temporary file to play the song
        os.makedirs(TEMP_DIR, exist_ok=True)
        
        temp_file = os.path.join(TEMP_DIR, f"song_{song_id}.{song_data['type']}")
        
        # Write binary data to temp file
        with open(temp_file, 'wb') as f:
            f.write(song_data['data'])
            
        # Load and play the song
        mixer.music.load(temp_file)
        mixer.music.play()
        
        # Update UI elements if provided
        if now_playing_label:
            now_playing_label.configure(text=f"Now Playing: {song_data['title']} - {song_data['artist']}")
        
        if play_btn:
            play_btn.configure(text="⏸️")
        
        # Return song info for caller to maintain state
        return {
            "id": song_id,
            "title": song_data['title'],
            "artist": song_data['artist'],
            "playing": True,
            "paused": False
        }
        
    except Exception as e:
        print(f"Error playing song: {e}")
        messagebox.showerror("Error", f"Could not play song: {e}")
        return None

def format_file_size(size_bytes):
    """Format file size from bytes to human-readable format"""
    if not size_bytes:
        return "0 B"
    
    # Define size units
    units = ['B', 'KB', 'MB', 'GB']
    size = float(size_bytes)
    unit_index = 0
    
    # Convert to appropriate unit
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1
    
    # Return formatted size
    return f"{size:.2f} {units[unit_index]}"

def record_listening_history(user_id, song_id):
    """Record that the user listened to a song"""
    try:
        connection = connect_db()
        if not connection:
            return False
            
        cursor = connection.cursor()
        
        query = "INSERT INTO Listening_History (user_id, song_id) VALUES (%s, %s)"
        cursor.execute(query, (user_id, song_id))
        connection.commit()
        return True
        
    except Exception as e:
        print(f"Error recording listening history: {e}")
        return False
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()