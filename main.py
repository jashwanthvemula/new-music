"""
Online Music System
Main entry point for the application
"""
import os
import mysql.connector
import tkinter as tk
from tkinter import messagebox
import subprocess
import customtkinter as ctk
import hashlib
import random
import time
from utils.db_utils import connect_db, hash_password

# ------------------- Database Setup Functions -------------------
def connect_db_server():
    """Connect to MySQL server without specifying a database"""
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="new_password"
        )
        return connection
    except mysql.connector.Error as err:
        print(f"Error connecting to MySQL server: {err}")
        return None

def create_database():
    """Create the database and tables"""
    try:
        # First connect to server
        connection = connect_db_server()
        if not connection:
            return False
            
        cursor = connection.cursor()
        
        # Create database
        print("Creating database...")
        cursor.execute("CREATE DATABASE IF NOT EXISTS online_music_system")
        cursor.execute("USE online_music_system")
        
        # Create Users table
        print("Creating Users table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            user_id INT AUTO_INCREMENT PRIMARY KEY,
            first_name VARCHAR(50) NOT NULL,
            last_name VARCHAR(50) NOT NULL,
            email VARCHAR(100) NOT NULL UNIQUE,
            password VARCHAR(64) NOT NULL,
            is_admin BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Create Artists table
        print("Creating Artists table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Artists (
            artist_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            bio TEXT,
            image_url VARCHAR(255)
        )
        """)
        
        # Create Albums table
        print("Creating Albums table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Albums (
            album_id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(100) NOT NULL,
            artist_id INT,
            release_year INT,
            cover_art MEDIUMBLOB,
            FOREIGN KEY (artist_id) REFERENCES Artists(artist_id) ON DELETE SET NULL
        )
        """)
        
        # Create Genres table
        print("Creating Genres table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Genres (
            genre_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(50) NOT NULL UNIQUE
        )
        """)
        
        # Create Songs table
        print("Creating Songs table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Songs (
            song_id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(100) NOT NULL,
            artist_id INT,
            album_id INT,
            genre_id INT,
            duration INT,
            file_data LONGBLOB NOT NULL,
            file_type VARCHAR(10) NOT NULL,
            file_size INT NOT NULL,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (artist_id) REFERENCES Artists(artist_id) ON DELETE SET NULL,
            FOREIGN KEY (album_id) REFERENCES Albums(album_id) ON DELETE SET NULL,
            FOREIGN KEY (genre_id) REFERENCES Genres(genre_id) ON DELETE SET NULL
        )
        """)
        
        # Create Playlists table
        print("Creating Playlists table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Playlists (
            playlist_id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
        )
        """)
        
        # Create Playlist_Songs junction table
        print("Creating Playlist_Songs table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Playlist_Songs (
            playlist_id INT NOT NULL,
            song_id INT NOT NULL,
            position INT NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (playlist_id, song_id),
            FOREIGN KEY (playlist_id) REFERENCES Playlists(playlist_id) ON DELETE CASCADE,
            FOREIGN KEY (song_id) REFERENCES Songs(song_id) ON DELETE CASCADE
        )
        """)
        
        # Create User_Favorites table
        print("Creating User_Favorites table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS User_Favorites (
            user_id INT NOT NULL,
            song_id INT NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, song_id),
            FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (song_id) REFERENCES Songs(song_id) ON DELETE CASCADE
        )
        """)
        
        # Create Listening_History table
        print("Creating Listening_History table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Listening_History (
            history_id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            song_id INT NOT NULL,
            played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (song_id) REFERENCES Songs(song_id) ON DELETE CASCADE
        )
        """)
        
        connection.commit()
        cursor.close()
        connection.close()
        
        print("Database and tables created successfully!")
        return True
        
    except mysql.connector.Error as err:
        print(f"Error creating database: {err}")
        return False

def add_default_users():
    """Add default users including admin"""
    try:
        connection = connect_db()
        if not connection:
            return False
            
        cursor = connection.cursor()
        
        # Check if users already exist
        cursor.execute("SELECT COUNT(*) FROM Users")
        user_count = cursor.fetchone()[0]
        
        if user_count > 0:
            print(f"Users table already has {user_count} records. Skipping default users.")
            cursor.close()
            connection.close()
            return True
        
        # Default users
        default_users = [
            # Admin user
            ("Admin", "User", "admin@music.com", hash_password("admin123"), True),
            # Regular users
            ("John", "Doe", "john@example.com", hash_password("password123"), False),
            ("Jane", "Smith", "jane@example.com", hash_password("password123"), False),
            ("Alice", "Johnson", "alice@example.com", hash_password("password123"), False),
            ("Bob", "Williams", "bob@example.com", hash_password("password123"), False)
        ]
        
        # Insert users
        print("Adding default users...")
        for first_name, last_name, email, password, is_admin in default_users:
            cursor.execute(
                "INSERT INTO Users (first_name, last_name, email, password, is_admin) VALUES (%s, %s, %s, %s, %s)",
                (first_name, last_name, email, password, is_admin)
            )
        
        connection.commit()
        print(f"Added {len(default_users)} default users successfully!")
        
        cursor.close()
        connection.close()
        return True
        
    except mysql.connector.Error as err:
        print(f"Error adding default users: {err}")
        return False

def add_default_genres():
    """Add default music genres"""
    try:
        connection = connect_db()
        if not connection:
            return False
            
        cursor = connection.cursor()
        
        # Check if genres already exist
        cursor.execute("SELECT COUNT(*) FROM Genres")
        genre_count = cursor.fetchone()[0]
        
        if genre_count > 0:
            print(f"Genres table already has {genre_count} records. Skipping default genres.")
            cursor.close()
            connection.close()
            return True
        
        # Default genres
        default_genres = [
            "Pop", "Rock", "Hip Hop", "R&B", "Country", 
            "Jazz", "Classical", "Electronic", "Blues", "Reggae",
            "Folk", "Metal", "Punk", "Soul", "Funk",
            "Disco", "Techno", "House", "Ambient", "Indie"
        ]
        
        # Insert genres
        print("Adding default genres...")
        for genre in default_genres:
            cursor.execute("INSERT INTO Genres (name) VALUES (%s)", (genre,))
        
        connection.commit()
        print(f"Added {len(default_genres)} default genres successfully!")
        
        cursor.close()
        connection.close()
        return True
        
    except mysql.connector.Error as err:
        print(f"Error adding default genres: {err}")
        return False

def add_default_artists():
    """Add default artists"""
    try:
        connection = connect_db()
        if not connection:
            return False
            
        cursor = connection.cursor()
        
        # Check if artists already exist
        cursor.execute("SELECT COUNT(*) FROM Artists")
        artist_count = cursor.fetchone()[0]
        
        if artist_count > 0:
            print(f"Artists table already has {artist_count} records. Skipping default artists.")
            cursor.close()
            connection.close()
            return True
        
        # Default artists with bios
        default_artists = [
            ("The Weeknd", "Abel Makkonen Tesfaye, known professionally as the Weeknd, is a Canadian singer, songwriter, and record producer."),
            ("Dua Lipa", "Dua Lipa is an English singer and songwriter. After working as a model, she signed with Warner Bros. Records in 2014."),
            ("Ed Sheeran", "Edward Christopher Sheeran MBE is an English singer-songwriter, record producer, musician, and actor."),
            ("Taylor Swift", "Taylor Alison Swift is an American singer-songwriter. Her discography spans multiple genres, and her songwriting is often inspired by her personal life."),
            ("Billie Eilish", "Billie Eilish Pirate Baird O'Connell is an American singer-songwriter. She first gained public attention in 2015 with her debut single 'Ocean Eyes'."),
            ("Drake", "Aubrey Drake Graham is a Canadian rapper, singer, and actor. Drake initially gained recognition as an actor on the teen drama television series Degrassi: The Next Generation."),
            ("Ariana Grande", "Ariana Grande-Butera is an American singer, songwriter, and actress. Her four-octave vocal range has received critical acclaim."),
            ("Beyoncé", "Beyoncé Giselle Knowles-Carter is an American singer, songwriter, record producer, and actress."),
            ("Post Malone", "Austin Richard Post, known professionally as Post Malone, is an American rapper, singer, and songwriter."),
            ("Justin Bieber", "Justin Drew Bieber is a Canadian singer. He was discovered by American record executive Scooter Braun.")
        ]
        
        # Insert artists
        print("Adding default artists...")
        for name, bio in default_artists:
            cursor.execute(
                "INSERT INTO Artists (name, bio) VALUES (%s, %s)",
                (name, bio)
            )
        
        connection.commit()
        print(f"Added {len(default_artists)} default artists successfully!")
        
        cursor.close()
        connection.close()
        return True
        
    except mysql.connector.Error as err:
        print(f"Error adding default artists: {err}")
        return False

def create_temp_directory():
    """Create a temp directory for storing temporary files"""
    try:
        os.makedirs("temp", exist_ok=True)
        os.makedirs("assets/uploads", exist_ok=True)
        print("Created temp and uploads directories.")
        return True
    except Exception as e:
        print(f"Error creating directories: {e}")
        return False

# ------------------- Splash Screen -------------------
def show_splash_screen():
    """Display a splash screen while setting up the database"""
    # Setup splash window
    splash_root = ctk.CTk()
    splash_root.title("Online Music System - Setup")
    splash_root.geometry("400x300")
    splash_root.overrideredirect(True)  # No window border
    
    # Center the window
    screen_width = splash_root.winfo_screenwidth()
    screen_height = splash_root.winfo_screenheight()
    x = (screen_width - 400) // 2
    y = (screen_height - 300) // 2
    splash_root.geometry(f"400x300+{x}+{y}")
    
    # Create a frame with rounded corners and purple color
    splash_frame = ctk.CTkFrame(splash_root, corner_radius=20, fg_color="#B146EC")
    splash_frame.pack(fill="both", expand=True, padx=0, pady=0)
    
    # App title
    ctk.CTkLabel(
        splash_frame, 
        text="Online Music System", 
        font=("Arial", 28, "bold"),
        text_color="white"
    ).pack(pady=(40, 5))
    
    # App icon/logo
    ctk.CTkLabel(
        splash_frame, 
        text="🎵🐦", 
        font=("Arial", 50),
        text_color="white"
    ).pack(pady=10)
    
    # Loading text
    loading_label = ctk.CTkLabel(
        splash_frame, 
        text="Initializing...", 
        font=("Arial", 14),
        text_color="white"
    )
    loading_label.pack(pady=10)
    
    # Progress bar
    progress = ctk.CTkProgressBar(splash_frame, width=320)
    progress.pack(pady=10)
    progress.set(0)
    
    # Status message
    status_label = ctk.CTkLabel(
        splash_frame,
        text="",
        font=("Arial", 12),
        text_color="white"
    )
    status_label.pack(pady=5)
    
    # Setup steps with corresponding progress values
    setup_steps = [
        ("Creating database schema...", 0.1, create_database),
        ("Adding default users...", 0.3, add_default_users),
        ("Adding music genres...", 0.5, add_default_genres),
        ("Adding artists...", 0.7, add_default_artists),
        ("Creating temporary directories...", 0.9, create_temp_directory)
    ]
    
    # Function to run setup in steps
    def run_setup():
        # Initialize progress
        progress.set(0.05)
        loading_label.configure(text="Starting setup...")
        splash_root.update_idletasks()
        time.sleep(0.5)
        
        # Run each setup step
        setup_success = True
        for message, prog_value, step_function in setup_steps:
            # Update UI
            loading_label.configure(text=message)
            status_label.configure(text="")
            progress.set(prog_value)
            splash_root.update_idletasks()
            
            # Run step
            try:
                result = step_function()
                if not result:
                    setup_success = False
                    status_label.configure(text="Error! Check console for details.")
            except Exception as e:
                setup_success = False
                print(f"Error during setup: {e}")
                status_label.configure(text=f"Error: {str(e)[:30]}...")
            
            # Small delay for visual feedback
            time.sleep(0.3)
        
        # Complete setup
        progress.set(1.0)
        
        if setup_success:
            loading_label.configure(text="Setup completed successfully!")
            status_label.configure(text="Launching application...")
        else:
            loading_label.configure(text="Setup completed with errors.")
            status_label.configure(text="See console for details. Launching application...")
        
        splash_root.update_idletasks()
        time.sleep(1.5)
        
        # Close splash and launch application
        splash_root.destroy()
        launch_application()
    
    # Start setup after a short delay
    splash_root.after(500, run_setup)
    
    # Start the splash screen
    splash_root.mainloop()

# ------------------- Launch Application -------------------
def launch_application():
    """Launch the application starting with the login screen"""
    try:
        # Clear any existing user session
        if os.path.exists("current_user.txt"):
            os.remove("current_user.txt")
        
        if os.path.exists("current_admin.txt"):
            os.remove("current_admin.txt")
        
        # Start the login page
        subprocess.Popen(["python", "login.py"])
    except Exception as e:
        print(f"Error launching application: {e}")
        messagebox.showerror("Error", f"Failed to launch application: {e}")

# ------------------- Main Entry Point -------------------
if __name__ == "__main__":
    try:
        # Set the appearance mode for splash screen
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Show splash screen and setup database
        show_splash_screen()
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()
        
        # Try to start login page directly if splash screen fails
        try:
            launch_application()
        except:
            pass
        
        # Keep console open in case of error
        input("Press Enter to exit...")