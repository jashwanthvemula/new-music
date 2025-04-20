import customtkinter as ctk
from tkinter import messagebox
import subprocess
import os
from PIL import Image, ImageTk
from pygame import mixer
import threading
import time

# Import from our utils
from utils.db_utils import connect_db, get_current_user
from utils.audio_utils import play_song_from_db, record_listening_history

# Initialize mixer for music playback
mixer.init()

# Current song information
current_song = {
    "id": None,
    "title": "No song playing",
    "artist": "",
    "playing": False,
    "paused": False
}

# ------------------- Song Management Functions -------------------
def get_featured_songs(limit=3):
    """Get featured songs from the database"""
    try:
        connection = connect_db()
        if not connection:
            return []
            
        cursor = connection.cursor(dictionary=True)
        
        # Get songs with most plays in listening history
        query = """
        SELECT s.song_id, s.title, a.name as artist_name, COUNT(lh.history_id) as play_count 
        FROM Songs s
        JOIN Artists a ON s.artist_id = a.artist_id
        LEFT JOIN Listening_History lh ON s.song_id = lh.song_id
        GROUP BY s.song_id
        ORDER BY play_count DESC
        LIMIT %s
        """
        
        cursor.execute(query, (limit,))
        songs = cursor.fetchall()
        
        # If no songs with play history, get newest songs
        if not songs:
            query = """
            SELECT s.song_id, s.title, a.name as artist_name 
            FROM Songs s
            JOIN Artists a ON s.artist_id = a.artist_id
            ORDER BY s.upload_date DESC
            LIMIT %s
            """
            cursor.execute(query, (limit,))
            songs = cursor.fetchall()
            
        return songs
        
    except Exception as e:
        print(f"Error fetching featured songs: {e}")
        return []
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()

# ------------------- Music Player Functions -------------------
def play_song(song_id):
    """Play a song from its binary data in the database"""
    global current_song
    
    # Get current user for history tracking
    user = get_current_user()
    if not user:
        return False
    
    # Use our utility function to play the song
    song_info = play_song_from_db(song_id, mixer, 
                               now_playing_label if 'now_playing_label' in globals() else None,
                               play_btn if 'play_btn' in globals() else None)
    
    if song_info:
        # Update current song info
        current_song = song_info
        
        # Record in listening history
        record_listening_history(user['user_id'], song_id)
        
        return True
    
    return False

def toggle_play_pause():
    """Toggle between play and pause states"""
    global current_song
    
    if current_song["id"] is None:
        # No song is loaded, try to play first featured song
        featured_songs = get_featured_songs(1)
        if featured_songs:
            play_song(featured_songs[0]['song_id'])
    elif current_song["paused"]:
        # Resume paused song
        mixer.music.unpause()
        current_song["paused"] = False
        current_song["playing"] = True
        play_btn.configure(text="⏸️")
    elif current_song["playing"]:
        # Pause playing song
        mixer.music.pause()
        current_song["paused"] = True
        current_song["playing"] = False
        play_btn.configure(text="▶️")

def play_next_song():
    """Play the next song in the playlist"""
    # This is a placeholder that would be implemented with your playlist functionality
    messagebox.showinfo("Info", "Next song feature will be implemented with playlists")

def play_previous_song():
    """Play the previous song in the playlist"""
    # This is a placeholder that would be implemented with your playlist functionality
    messagebox.showinfo("Info", "Previous song feature will be implemented with playlists")

# ------------------- Navigation Functions -------------------
def open_search_page():
    """Open the search page"""
    try:
        subprocess.Popen(["python", "player/search.py"])
        root.destroy()
    except Exception as e:
        messagebox.showerror("Error", f"Unable to open search page: {e}")

def open_playlist_page():
    """Open the playlist page"""
    try:
        subprocess.Popen(["python", "player/playlist.py"])
        root.destroy()
    except Exception as e:
        messagebox.showerror("Error", f"Unable to open playlist page: {e}")

def open_download_page():
    """Open the download page"""
    try:
        subprocess.Popen(["python", "player/download.py"])
        root.destroy()
    except Exception as e:
        messagebox.showerror("Error", f"Unable to open download page: {e}")

def open_recommend_page():
    """Open the recommendations page"""
    try:
        subprocess.Popen(["python", "player/recommend.py"])
        root.destroy()
    except Exception as e:
        messagebox.showerror("Error", f"Unable to open recommendations page: {e}")

def open_login_page():
    """Logout and open the login page"""
    try:
        # Stop any playing music
        if mixer.music.get_busy():
            mixer.music.stop()
            
        # Remove current user file
        if os.path.exists("current_user.txt"):
            os.remove("current_user.txt")
            
        subprocess.Popen(["python", "login.py"])
        root.destroy()
    except Exception as e:
        messagebox.showerror("Error", f"Unable to logout: {e}")

def create_song_card(parent, song_id, title, artist):
    """Create a clickable song card"""
    # Create song card frame
    song_card = ctk.CTkFrame(parent, fg_color="#1A1A2E", corner_radius=10, 
                           width=150, height=180)
    song_card.pack_propagate(False)
    
    # Center the text vertically by adding a spacer frame
    spacer = ctk.CTkFrame(song_card, fg_color="#1A1A2E", height=30)
    spacer.pack(side="top")
    
    # Song title with larger font
    song_label = ctk.CTkLabel(song_card, text=title, 
                             font=("Arial", 16, "bold"), text_color="white")
    song_label.pack(pady=(5, 0))
    
    # Artist name below with smaller font
    artist_label = ctk.CTkLabel(song_card, text=artist, 
                               font=("Arial", 12), text_color="#A0A0A0")
    artist_label.pack(pady=(5, 0))
    
    # Play button
    play_song_btn = ctk.CTkButton(song_card, text="▶️ Play", 
                                font=("Arial", 12, "bold"),
                                fg_color="#B146EC", hover_color="#9333EA",
                                command=lambda: play_song(song_id))
    play_song_btn.pack(pady=(15, 0))
    
    return song_card

# ------------------- Main Application -------------------
if __name__ == "__main__":
    try:
        # Get current user info
        user = get_current_user()
        if not user:
            # Redirect to login if not logged in
            open_login_page()
            exit()

        # ---------------- Initialize App ----------------
        ctk.set_appearance_mode("dark")  # Dark mode
        ctk.set_default_color_theme("blue")  # Default theme

        root = ctk.CTk()
        root.title("Online Music System - Home")
        root.geometry("1000x600")  # Adjusted to match the image proportions
        root.resizable(False, False)

        # ---------------- Main Frame ----------------
        main_frame = ctk.CTkFrame(root, fg_color="#1E1E2E", corner_radius=15)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # ---------------- Sidebar Navigation ----------------
        sidebar = ctk.CTkFrame(main_frame, width=250, height=580, fg_color="#111827", corner_radius=10)
        sidebar.pack(side="left", fill="y", padx=(10, 0), pady=10)

        # Sidebar Title
        title_label = ctk.CTkLabel(sidebar, text="Online Music\nSystem", font=("Arial", 20, "bold"), text_color="white")
        title_label.pack(pady=(25, 30))

        # Sidebar Menu Items - Updated with navigation commands
        home_btn = ctk.CTkButton(sidebar, text="🏠 Home", font=("Arial", 14), 
                               fg_color="#111827", hover_color="#1E293B", text_color="white",
                               anchor="w", corner_radius=0, height=40)
        home_btn.pack(fill="x", pady=5, padx=10)

        search_btn = ctk.CTkButton(sidebar, text="🔍 Search", font=("Arial", 14), 
                                 fg_color="#111827", hover_color="#1E293B", text_color="#A0A0A0",
                                 anchor="w", corner_radius=0, height=40, command=open_search_page)
        search_btn.pack(fill="x", pady=5, padx=10)

        playlist_btn = ctk.CTkButton(sidebar, text="🎵 Playlist", font=("Arial", 14), 
                                   fg_color="#111827", hover_color="#1E293B", text_color="#A0A0A0",
                                   anchor="w", corner_radius=0, height=40, command=open_playlist_page)
        playlist_btn.pack(fill="x", pady=5, padx=10)

        download_btn = ctk.CTkButton(sidebar, text="⬇️ Download", font=("Arial", 14), 
                                   fg_color="#111827", hover_color="#1E293B", text_color="#A0A0A0",
                                   anchor="w", corner_radius=0, height=40, command=open_download_page)
        download_btn.pack(fill="x", pady=5, padx=10)

        recommend_btn = ctk.CTkButton(sidebar, text="🎧 Recommend Songs", font=("Arial", 14), 
                                     fg_color="#111827", hover_color="#1E293B", text_color="#A0A0A0",
                                     anchor="w", corner_radius=0, height=40, command=open_recommend_page)
        recommend_btn.pack(fill="x", pady=5, padx=10)

        logout_btn = ctk.CTkButton(sidebar, text="🚪 Logout", font=("Arial", 14), 
                                 fg_color="#111827", hover_color="#1E293B", text_color="#A0A0A0",
                                 anchor="w", corner_radius=0, height=40, command=open_login_page)
        logout_btn.pack(fill="x", pady=5, padx=10)

        # Now playing label
        now_playing_frame = ctk.CTkFrame(sidebar, fg_color="#111827", height=40)
        now_playing_frame.pack(side="bottom", fill="x", pady=(0, 10), padx=10)
        
        now_playing_label = ctk.CTkLabel(now_playing_frame, 
                                       text="Now Playing: No song playing", 
                                       font=("Arial", 12), 
                                       text_color="#A0A0A0",
                                       wraplength=220)
        now_playing_label.pack(pady=5)

        # Music player controls at bottom of sidebar
        player_frame = ctk.CTkFrame(sidebar, fg_color="#111827", height=50)
        player_frame.pack(side="bottom", fill="x", pady=10, padx=10)

        # Control buttons with functionality
        prev_btn = ctk.CTkButton(player_frame, text="⏮️", font=("Arial", 18), 
                               fg_color="#111827", hover_color="#1E293B", 
                               width=40, height=40, command=play_previous_song)
        prev_btn.pack(side="left", padx=10)

        play_btn = ctk.CTkButton(player_frame, text="▶️", font=("Arial", 18), 
                               fg_color="#111827", hover_color="#1E293B", 
                               width=40, height=40, command=toggle_play_pause)
        play_btn.pack(side="left", padx=10)

        next_btn = ctk.CTkButton(player_frame, text="⏭️", font=("Arial", 18), 
                               fg_color="#111827", hover_color="#1E293B", 
                               width=40, height=40, command=play_next_song)
        next_btn.pack(side="left", padx=10)

        # ---------------- Main Content ----------------
        content_frame = ctk.CTkFrame(main_frame, fg_color="#131B2E", corner_radius=10)
        content_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        # Header with username
        header_frame = ctk.CTkFrame(content_frame, fg_color="#131B2E", height=40)
        header_frame.pack(fill="x", padx=20, pady=(20, 0))

        # Left side: Home
        home_label = ctk.CTkLabel(header_frame, text="Home", font=("Arial", 18, "bold"), text_color="white")
        home_label.pack(side="left")

        # Right side: Username - updated with actual user name
        user_label = ctk.CTkLabel(header_frame, 
                                text=f"Hello, {user['first_name']} {user['last_name']}!", 
                                font=("Arial", 14), text_color="#A0A0A0")
        user_label.pack(side="right")

        # ---------------- Hero Section ----------------
        hero_frame = ctk.CTkFrame(content_frame, fg_color="#131B2E")
        hero_frame.pack(fill="x", padx=20, pady=(40, 20))

        # Main title
        title_label = ctk.CTkLabel(hero_frame, text="Discover Music & Play Instantly", 
                                 font=("Arial", 28, "bold"), text_color="#B146EC")
        title_label.pack(anchor="w")

        # Subtitle
        subtitle_label = ctk.CTkLabel(hero_frame, 
                                    text="Explore top trending songs, curated playlists, and personalized recommendations.", 
                                    font=("Arial", 14), text_color="#A0A0A0")
        subtitle_label.pack(anchor="w", pady=(10, 20))

        # Action Buttons with navigation
        button_frame = ctk.CTkFrame(hero_frame, fg_color="#131B2E")
        button_frame.pack(anchor="w")

        # Trending button (just scrolls to featured songs for now)
        trending_btn = ctk.CTkButton(button_frame, text="🔥 Trending", font=("Arial", 14, "bold"), 
                                   fg_color="#2563EB", hover_color="#1D4ED8", 
                                   corner_radius=8, height=40, width=150)
        trending_btn.pack(side="left", padx=(0, 10))

        # Playlists button
        playlists_btn = ctk.CTkButton(button_frame, text="🎵 Playlists", font=("Arial", 14, "bold"), 
                                    fg_color="#16A34A", hover_color="#15803D", 
                                    corner_radius=8, height=40, width=150,
                                    command=open_playlist_page)
        playlists_btn.pack(side="left", padx=10)

        # Download button
        download_btn = ctk.CTkButton(button_frame, text="⬇️ Download", font=("Arial", 14, "bold"), 
                                   fg_color="#B146EC", hover_color="#9333EA", 
                                   corner_radius=8, height=40, width=150,
                                   command=open_download_page)
        download_btn.pack(side="left", padx=10)

        # ---------------- Featured Songs Section ----------------
        featured_frame = ctk.CTkFrame(content_frame, fg_color="#131B2E")
        featured_frame.pack(fill="x", padx=20, pady=20)

        # Section title
        featured_title = ctk.CTkLabel(featured_frame, text="🔥 Featured Songs", 
                                    font=("Arial", 18, "bold"), text_color="#B146EC")
        featured_title.pack(anchor="w", pady=(0, 20))

        # Song cards container
        songs_frame = ctk.CTkFrame(featured_frame, fg_color="#131B2E")
        songs_frame.pack(fill="x")

        # Get featured songs from database
        featured_songs = get_featured_songs(3)
        
        # If database has no songs yet, use sample data
        if not featured_songs:
            featured_songs = [
                {"song_id": 1, "title": "Blinding\nLights", "artist_name": "The\nWeeknd"},
                {"song_id": 2, "title": "Levitating", "artist_name": "Dua Lipa"},
                {"song_id": 3, "title": "Shape of\nYou", "artist_name": "Ed\nSheeran"}
            ]
        
        # Create song cards for each featured song
        for song in featured_songs:
            song_card = create_song_card(
                songs_frame, 
                song["song_id"], 
                song["title"], 
                song["artist_name"]
            )
            song_card.pack(side="left", padx=10)

        # ---------------- Run Application ----------------
        root.mainloop()
        
    except Exception as e:
        import traceback
        print(f"Error in home.py: {e}")
        traceback.print_exc()
        messagebox.showerror("Error", f"An error occurred: {e}")
        input("Press Enter to exit...")  # This keeps console open