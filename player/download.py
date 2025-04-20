import customtkinter as ctk
from tkinter import filedialog, messagebox, simpledialog
import os
import shutil
import subprocess
from pygame import mixer
from PIL import Image, ImageTk

# Import from our utils
from utils.db_utils import connect_db, get_current_user
from utils.audio_utils import (upload_song_to_db, play_song_from_db, 
                              format_file_size, record_listening_history)

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

# Keep track of selected song
selected_song = {
    "id": None,
    "title": None,
    "artist": None
}

# ------------------- Song Management Functions -------------------
def get_popular_songs(limit=8):
    """Get most popular songs from the database"""
    try:
        connection = connect_db()
        if not connection:
            return []
            
        cursor = connection.cursor(dictionary=True)
        
        # Get songs with most plays in listening history
        query = """
        SELECT s.song_id, s.title, a.name as artist_name, COUNT(lh.history_id) as play_count, 
               g.name as genre_name, s.file_size, s.file_type
        FROM Songs s
        JOIN Artists a ON s.artist_id = a.artist_id
        LEFT JOIN Genres g ON s.genre_id = g.genre_id
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
            SELECT s.song_id, s.title, a.name as artist_name, s.file_size, s.file_type,
                   g.name as genre_name, 0 as play_count
            FROM Songs s
            JOIN Artists a ON s.artist_id = a.artist_id
            LEFT JOIN Genres g ON s.genre_id = g.genre_id
            ORDER BY s.upload_date DESC
            LIMIT %s
            """
            cursor.execute(query, (limit,))
            songs = cursor.fetchall()
            
        # Format file sizes to human-readable format
        for song in songs:
            song['file_size_formatted'] = format_file_size(song['file_size'])
            
        return songs
        
    except Exception as e:
        print(f"Error fetching popular songs: {e}")
        return []
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()

def get_user_favorite_songs(limit=8):
    """Get the current user's favorite songs"""
    try:
        # Get current user ID
        user = get_current_user()
        if not user:
            return []
            
        connection = connect_db()
        if not connection:
            return []
            
        cursor = connection.cursor(dictionary=True)
        
        # Get songs the user has listened to most
        query = """
        SELECT s.song_id, s.title, a.name as artist_name, COUNT(lh.history_id) as play_count,
               g.name as genre_name, s.file_size, s.file_type
        FROM Listening_History lh
        JOIN Songs s ON lh.song_id = s.song_id
        JOIN Artists a ON s.artist_id = a.artist_id
        LEFT JOIN Genres g ON s.genre_id = g.genre_id
        WHERE lh.user_id = %s
        GROUP BY s.song_id
        ORDER BY play_count DESC
        LIMIT %s
        """
        
        cursor.execute(query, (user['user_id'], limit))
        songs = cursor.fetchall()
        
        # Format file sizes to human-readable format
        for song in songs:
            song['file_size_formatted'] = format_file_size(song['file_size'])
            
        return songs
        
    except Exception as e:
        print(f"Error getting user favorite songs: {e}")
        return []
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()

def get_artists():
    """Get list of artists from the database"""
    try:
        connection = connect_db()
        if not connection:
            return []
            
        cursor = connection.cursor(dictionary=True)
        
        query = "SELECT artist_id, name FROM Artists ORDER BY name"
        cursor.execute(query)
        
        return cursor.fetchall()
        
    except Exception as e:
        print(f"Error fetching artists: {e}")
        return []
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()

def get_genres():
    """Get list of genres from the database"""
    try:
        connection = connect_db()
        if not connection:
            return []
            
        cursor = connection.cursor(dictionary=True)
        
        query = "SELECT genre_id, name FROM Genres ORDER BY name"
        cursor.execute(query)
        
        return cursor.fetchall()
        
    except Exception as e:
        print(f"Error fetching genres: {e}")
        return []
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()

def download_song(song_id):
    """Download a song to local storage"""
    try:
        # Get song data
        song_data = get_song_data(song_id)
        if not song_data:
            messagebox.showerror("Error", "Could not retrieve song data")
            return False
        
        # Format the filename
        filename = f"{song_data['artist']} - {song_data['title']}.{song_data['type']}"
        # Replace invalid filename characters
        filename = filename.replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
        
        # Ask user for download location
        downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        save_path = filedialog.asksaveasfilename(
            initialdir=downloads_dir,
            initialfile=filename,
            defaultextension=f".{song_data['type']}",
            filetypes=[(f"{song_data['type'].upper()} files", f"*.{song_data['type']}"), ("All files", "*.*")]
        )
        
        if not save_path:  # User cancelled
            return False
        
        # Write song data to file
        with open(save_path, 'wb') as f:
            f.write(song_data['data'])
        
        messagebox.showinfo("Download Complete", f"Song has been downloaded to:\n{save_path}")
        return True
        
    except Exception as e:
        print(f"Error downloading song: {e}")
        messagebox.showerror("Error", f"Could not download song: {e}")
        return False

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
        # No song loaded - do nothing
        return
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
    """Placeholder for playing next song"""
    messagebox.showinfo("Info", "Next song feature will be implemented with playlists")

def play_previous_song():
    """Placeholder for playing previous song"""
    messagebox.showinfo("Info", "Previous song feature will be implemented with playlists")

# ------------------- Upload Function -------------------
def handle_upload_song():
    """Handle the upload song process"""
    # Ask user to select an audio file
    file_path = filedialog.askopenfilename(
        title="Select a song file",
        filetypes=[("Audio Files", "*.mp3 *.wav *.flac"), ("All files", "*.*")]
    )
    
    if not file_path:  # User cancelled
        return
    
    # Get song title from file name
    default_title = os.path.splitext(os.path.basename(file_path))[0]
    
    # Ask for song title
    title = simpledialog.askstring("Song Title", "Enter song title:", initialvalue=default_title)
    if not title:  # User cancelled
        return
    
    # Get artists from database
    artists = get_artists()
    if not artists:
        messagebox.showerror("Error", "No artists found in database")
        
        # Ask if user wants to add a new artist
        artist_name = simpledialog.askstring("New Artist", "Enter artist name:")
        if not artist_name:  # User cancelled
            return
            
        # Add new artist to database
        connection = connect_db()
        if not connection:
            return
            
        try:
            cursor = connection.cursor()
            cursor.execute("INSERT INTO Artists (name) VALUES (%s)", (artist_name,))
            connection.commit()
            artist_id = cursor.lastrowid
            cursor.close()
            connection.close()
        except Exception as e:
            messagebox.showerror("Error", f"Could not add artist: {e}")
            return
    else:
        # Create a dialog to select artist
        artist_select = ctk.CTkToplevel(root)
        artist_select.title("Select Artist")
        artist_select.geometry("300x400")
        artist_select.transient(root)
        artist_select.grab_set()
        
        # Center the dialog
        artist_select.update_idletasks()
        width = artist_select.winfo_width()
        height = artist_select.winfo_height()
        x = (artist_select.winfo_screenwidth() // 2) - (width // 2)
        y = (artist_select.winfo_screenheight() // 2) - (height // 2)
        artist_select.geometry(f"{width}x{height}+{x}+{y}")
        
        # Label
        ctk.CTkLabel(artist_select, text="Select Artist", font=("Arial", 16, "bold")).pack(pady=10)
        
        # Create a scrollable frame for artists
        artists_frame = ctk.CTkScrollableFrame(artist_select, width=250, height=250)
        artists_frame.pack(pady=10, padx=10, fill="both", expand=True)
        
        # Artist variable
        artist_var = ctk.StringVar()
        
        # Add radio buttons for each artist
        for artist in artists:
            ctk.CTkRadioButton(artists_frame, text=artist["name"], variable=artist_var, value=str(artist["artist_id"])).pack(anchor="w", pady=5)
        
        # Select first artist by default
        if artists:
            artist_var.set(str(artists[0]["artist_id"]))
        
        # Button to add a new artist
        def add_new_artist():
            artist_name = simpledialog.askstring("New Artist", "Enter artist name:")
            if artist_name:
                connection = connect_db()
                if connection:
                    try:
                        cursor = connection.cursor()
                        cursor.execute("INSERT INTO Artists (name) VALUES (%s)", (artist_name,))
                        connection.commit()
                        new_id = cursor.lastrowid
                        cursor.close()
                        connection.close()
                        
                        # Add to list and select it
                        ctk.CTkRadioButton(artists_frame, text=artist_name, variable=artist_var, value=str(new_id)).pack(anchor="w", pady=5)
                        artist_var.set(str(new_id))
                    except Exception as e:
                        messagebox.showerror("Error", f"Could not add artist: {e}")
        
        ctk.CTkButton(artist_select, text="+ Add New Artist", command=add_new_artist).pack(pady=5)
        
        # Confirm button
        def confirm_artist():
            nonlocal artist_id
            if artist_var.get():
                artist_id = int(artist_var.get())
                artist_select.destroy()
            else:
                messagebox.showwarning("Warning", "Please select an artist")
        
        # Variable to store selected artist ID
        artist_id = None
        
        ctk.CTkButton(artist_select, text="Confirm", command=confirm_artist).pack(pady=10)
        
        # Wait for dialog to close
        root.wait_window(artist_select)
        
        # If no artist selected, cancel upload
        if artist_id is None:
            return
    
    # Get genres from database
    genres = get_genres()
    
    # Create a dialog to select genre
    genre_select = ctk.CTkToplevel(root)
    genre_select.title("Select Genre")
    genre_select.geometry("300x400")
    genre_select.transient(root)
    genre_select.grab_set()
    
    # Center the dialog
    genre_select.update_idletasks()
    width = genre_select.winfo_width()
    height = genre_select.winfo_height()
    x = (genre_select.winfo_screenwidth() // 2) - (width // 2)
    y = (genre_select.winfo_screenheight() // 2) - (height // 2)
    genre_select.geometry(f"{width}x{height}+{x}+{y}")
    
    # Label
    ctk.CTkLabel(genre_select, text="Select Genre", font=("Arial", 16, "bold")).pack(pady=10)
    
    # Create a scrollable frame for genres
    genres_frame = ctk.CTkScrollableFrame(genre_select, width=250, height=250)
    genres_frame.pack(pady=10, padx=10, fill="both", expand=True)
    
    # Genre variable
    genre_var = ctk.StringVar()
    
    # Add radio buttons for each genre
    for genre in genres:
        ctk.CTkRadioButton(genres_frame, text=genre["name"], variable=genre_var, value=str(genre["genre_id"])).pack(anchor="w", pady=5)
    
    # Option for no genre
    ctk.CTkRadioButton(genres_frame, text="No Genre", variable=genre_var, value="0").pack(anchor="w", pady=5)
    
    # Select first genre by default
    if genres:
        genre_var.set(str(genres[0]["genre_id"]))
    else:
        genre_var.set("0")  # No genre
    
    # Confirm button
    def confirm_genre():
        nonlocal genre_id
        genre_id = int(genre_var.get()) if genre_var.get() != "0" else None
        genre_select.destroy()
    
    # Variable to store selected genre ID
    genre_id = None
    
    ctk.CTkButton(genre_select, text="Confirm", command=confirm_genre).pack(pady=10)
    
    # Wait for dialog to close
    root.wait_window(genre_select)
    
    # Upload the song
    song_id = upload_song_to_db(file_path, title, artist_id, genre_id)
    
    if song_id:
        messagebox.showinfo("Success", f"Song '{title}' uploaded successfully!")
        # Refresh the song list
        refresh_song_list()

def select_song_for_download(song_id, title, artist, song_frame):
    """Select a song for download"""
    global selected_song, song_frames
    
    # Reset highlight on all frames
    for frame in song_frames:
        frame.configure(fg_color="#1A1A2E")
    
    # Highlight selected frame
    song_frame.configure(fg_color="#2A2A4E")
    
    # Update selected song info
    selected_song["id"] = song_id
    selected_song["title"] = title
    selected_song["artist"] = artist

def refresh_song_list():
    """Refresh the song list"""
    global song_frames
    
    # Clear current song frames list
    song_frames = []
    
    # Clear current songs
    for widget in favorite_songs_frame.winfo_children():
        if widget != title_label and widget != subtitle_label and widget != button_frame and widget != tabs:
            widget.destroy()
    
    # Display favorite songs tab
    display_favorite_songs_tab()
    
    # Display popular songs tab
    display_popular_songs_tab()

def download_selected_song():
    """Download the selected song"""
    global selected_song
    
    if not selected_song["id"]:
        messagebox.showwarning("Warning", "Please select a song to download")
        return
    
    # Download the song
    download_song(selected_song["id"])

def display_favorite_songs_tab():
    """Display the user's favorite songs tab"""
    global song_frames
    
    # Get favorite songs
    favorite_songs = get_user_favorite_songs()
    
    if not favorite_songs:
        no_songs_label = ctk.CTkLabel(
            favorite_tab, 
            text="You haven't listened to any songs yet.", 
            font=("Arial", 14), 
            text_color="#A0A0A0"
        )
        no_songs_label.pack(pady=30)
        return
    
    # Create song frames for each song
    for song in favorite_songs:
        song_frame = ctk.CTkFrame(favorite_tab, fg_color="#1A1A2E", corner_radius=10, height=50)
        song_frame.pack(fill="x", pady=5, ipady=5)
        
        # Prevent frame from resizing
        song_frame.pack_propagate(False)
        
        # Song icon and title - left side
        song_icon = "🎵"
        song_label = ctk.CTkLabel(
            song_frame, 
            text=f"{song_icon} {song['artist_name']} - {song['title']}", 
            font=("Arial", 14), 
            text_color="white",
            anchor="w"
        )
        song_label.pack(side="left", padx=20)
        
        # File size and type - right side
        file_info = ctk.CTkLabel(
            song_frame, 
            text=f"{song['file_size_formatted']} ({song['file_type']})", 
            font=("Arial", 12), 
            text_color="#A0A0A0"
        )
        file_info.pack(side="right", padx=(0, 20))
        
        # Play button - right side
        play_btn = ctk.CTkButton(
            song_frame, 
            text="▶️", 
            font=("Arial", 14), 
            fg_color="#1E293B",
            hover_color="#2A3749",
            width=30, height=30,
            command=lambda sid=song['song_id']: play_song(sid)
        )
        play_btn.pack(side="right", padx=5)
        
        # Make frame selectable
        song_frame.bind(
            "<Button-1>", 
            lambda e, sid=song['song_id'], title=song['title'], artist=song['artist_name'], frame=song_frame: 
                select_song_for_download(sid, title, artist, frame)
        )
        song_label.bind(
            "<Button-1>", 
            lambda e, sid=song['song_id'], title=song['title'], artist=song['artist_name'], frame=song_frame: 
                select_song_for_download(sid, title, artist, frame)
        )
        
        # Add to list of song frames
        song_frames.append(song_frame)

def display_popular_songs_tab():
    """Display the popular songs tab"""
    global song_frames
    
    # Get popular songs
    popular_songs = get_popular_songs()
    
    if not popular_songs:
        no_songs_label = ctk.CTkLabel(
            popular_tab, 
            text="No songs found in the database.", 
            font=("Arial", 14), 
            text_color="#A0A0A0"
        )
        no_songs_label.pack(pady=30)
        return
    
    # Create song frames for each song
    for song in popular_songs:
        song_frame = ctk.CTkFrame(popular_tab, fg_color="#1A1A2E", corner_radius=10, height=50)
        song_frame.pack(fill="x", pady=5, ipady=5)
        
        # Prevent frame from resizing
        song_frame.pack_propagate(False)
        
        # Song icon and title - left side
        song_icon = "🎵"
        song_label = ctk.CTkLabel(
            song_frame, 
            text=f"{song_icon} {song['artist_name']} - {song['title']}", 
            font=("Arial", 14), 
            text_color="white",
            anchor="w"
        )
        song_label.pack(side="left", padx=20)
        
        file_info = ctk.CTkLabel(
            song_frame, 
            text=f"{song['file_size_formatted']} ({song['file_type']})", 
            font=("Arial", 12), 
            text_color="#A0A0A0"
        )
        file_info.pack(side="right", padx=(0, 20))
        
        # Play button - right side
        play_btn = ctk.CTkButton(
            song_frame, 
            text="▶️", 
            font=("Arial", 14), 
            fg_color="#1E293B",
            hover_color="#2A3749",
            width=30, height=30,
            command=lambda sid=song['song_id']: play_song(sid)
        )
        play_btn.pack(side="right", padx=5)
        
        # Make frame selectable
        song_frame.bind(
            "<Button-1>", 
            lambda e, sid=song['song_id'], title=song['title'], artist=song['artist_name'], frame=song_frame: 
                select_song_for_download(sid, title, artist, frame)
        )
        song_label.bind(
            "<Button-1>", 
            lambda e, sid=song['song_id'], title=song['title'], artist=song['artist_name'], frame=song_frame: 
                select_song_for_download(sid, title, artist, frame)
        )
        
        # Add to list of song frames
        song_frames.append(song_frame)

# ------------------- Navigation Functions -------------------
def open_home_page():
    """Open the home page"""
    try:
        subprocess.Popen(["python", "player/home.py"])
        root.destroy()
    except Exception as e:
        messagebox.showerror("Error", f"Unable to open home page: {e}")

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

# ------------------- Main Application ------------------- 
def init_download_page():
    """Initialize and run the download page"""
    global root, favorite_songs_frame, title_label, subtitle_label, button_frame, tabs
    global favorite_tab, popular_tab, song_frames, now_playing_label, play_btn
    
    # Get current user info
    user = get_current_user()
    if not user:
        # Redirect to login if not logged in
        open_login_page()
        return

    # --------------- Initialize App ---------------
    ctk.set_appearance_mode("dark")  # Dark mode
    ctk.set_default_color_theme("blue")  # Default theme

    root = ctk.CTk()
    root.title("Online Music System - Download Songs")
    root.geometry("1000x600")  # Adjusted to match the image proportions
    root.resizable(False, False)

    # --------------- Main Frame ---------------
    main_frame = ctk.CTkFrame(root, fg_color="#1E1E2E", corner_radius=15)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # --------------- Sidebar Navigation ---------------
    sidebar = ctk.CTkFrame(main_frame, width=250, height=580, fg_color="#111827", corner_radius=10)
    sidebar.pack(side="left", fill="y", padx=(10, 0), pady=10)

    # Sidebar Title
    title_label = ctk.CTkLabel(sidebar, text="Online Music\nSystem", font=("Arial", 20, "bold"), text_color="white")
    title_label.pack(pady=(25, 30))

    # Sidebar Menu Items with navigation commands
    home_btn = ctk.CTkButton(sidebar, text="🏠 Home", font=("Arial", 14), 
                          fg_color="#111827", hover_color="#1E293B", text_color="#A0A0A0",
                          anchor="w", corner_radius=0, height=40, command=open_home_page)
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
                              fg_color="#111827", hover_color="#1E293B", text_color="white",
                              anchor="w", corner_radius=0, height=40)
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

    # --------------- Main Content ---------------
    content_frame = ctk.CTkFrame(main_frame, fg_color="#131B2E", corner_radius=10)
    content_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

    # Header with username
    header_frame = ctk.CTkFrame(content_frame, fg_color="#131B2E", height=40)
    header_frame.pack(fill="x", padx=20, pady=(20, 0))

    # Left side: Download Songs
    download_label = ctk.CTkLabel(header_frame, text="Download Songs", font=("Arial", 24, "bold"), text_color="white")
    download_label.pack(side="left")

    # Right side: Username - updated with actual user name
    user_label = ctk.CTkLabel(header_frame, 
                           text=f"Hello, {user['first_name']} {user['last_name']}!", 
                           font=("Arial", 14), text_color="#A0A0A0")
    user_label.pack(side="right")

    # --------------- Download Your Favorite Songs ---------------
    favorite_songs_frame = ctk.CTkFrame(content_frame, fg_color="#131B2E")
    favorite_songs_frame.pack(fill="both", expand=True, padx=20, pady=(40, 0))

    # Section title - centered
    title_label = ctk.CTkLabel(favorite_songs_frame, text="Download Your Favorite Songs 🎵", 
                              font=("Arial", 24, "bold"), text_color="#B146EC")
    title_label.pack(pady=(0, 5))

    # Subtitle - centered
    subtitle_label = ctk.CTkLabel(favorite_songs_frame, text="Select a song to download or upload your own.", 
                                 font=("Arial", 14), text_color="#A0A0A0")
    subtitle_label.pack(pady=(0, 20))

    # Tabview for different song sections
    tabs = ctk.CTkTabview(favorite_songs_frame, fg_color="#131B2E")
    tabs.pack(fill="both", expand=True)
    
    # Add tabs
    favorite_tab = tabs.add("Your Favorites")
    popular_tab = tabs.add("Popular Songs")
    
    # Initialize song frames list
    song_frames = []
    
    # Display favorite songs tab
    display_favorite_songs_tab()
    
    # Display popular songs tab
    display_popular_songs_tab()

    # Button frame at the bottom
    button_frame = ctk.CTkFrame(favorite_songs_frame, fg_color="#131B2E")
    button_frame.pack(pady=25)

    # Download button
    download_button = ctk.CTkButton(button_frame, text="⬇️ Download Selected", font=("Arial", 14, "bold"), 
                                   fg_color="#B146EC", hover_color="#9333EA", 
                                   corner_radius=5, height=40, width=210, 
                                   command=download_selected_song)
    download_button.pack(side="left", padx=10)

    # Upload button
    upload_button = ctk.CTkButton(button_frame, text="⬆️ Upload New Song", font=("Arial", 14, "bold"), 
                                 fg_color="#2563EB", hover_color="#1D4ED8", 
                                 corner_radius=5, height=40, width=210,
                                 command=handle_upload_song)
    upload_button.pack(side="left", padx=10)

    # --------------- Run Application ---------------
    root.mainloop()

# Run the application if this script is executed directly
if __name__ == "__main__":
    try:
        # Create necessary directories
        os.makedirs("temp", exist_ok=True)
        
        # Run the application
        init_download_page()
    except Exception as e:
        import traceback
        print(f"Error in download.py: {e}")
        traceback.print_exc()
        messagebox.showerror("Error", f"An error occurred: {e}")
        input("Press Enter to exit...")  # This keeps console open