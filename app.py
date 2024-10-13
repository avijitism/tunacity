import wave
import asyncio
from shazamio import Shazam
import yt_dlp
import os
import re
from flask import Flask, make_response, request, jsonify, send_file, render_template, url_for

app = Flask(__name__)

# Set upload and download folders
UPLOAD_FOLDER = 'uploads'
DOWNLOAD_FOLDER = 'downloads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Route for homepage
@app.route('/')
def index():
    return render_template('index.html')

# Route to handle audio upload
@app.route('/upload-audio', methods=['POST'])
def upload_audio():
    if 'audio' not in request.files:
        return jsonify({"success": False, "message": "No audio file uploaded"}), 400

    audio_file = request.files['audio']
    file_path = os.path.join(UPLOAD_FOLDER, 'recorded_audio.wav')
    audio_file.save(file_path)
    
    # Check if the file was saved correctly
    if not os.path.exists(file_path):
        return jsonify({"success": False, "message": "Audio file could not be saved"}), 500

    # Run the song recognition using asyncio
    result = asyncio.run(recognize_song(file_path))

    if result:
        song_title = result['track']['title']
        artist = result['track']['subtitle']
        downloaded_file = download_song(song_title, artist)
        if downloaded_file:
            return jsonify({"success": True, "songTitle": song_title, "artist": artist}), 200
        else:
            return jsonify({"success": False, "message": "Song download failed"}), 500
    else:
        return jsonify({"success": False, "message": "Song not recognized"}), 400

# Route to handle song download
@app.route('/download-song', methods=['GET'])
def download_song_route():
    file_path = os.path.join(DOWNLOAD_FOLDER, "downloaded_song.mp3")
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return jsonify({"success": False, "message": "File not found"}), 404

# Function to recognize song using Shazamio
async def recognize_song(file_path):
    shazam = Shazam()
    try:
        print(f"Recognizing song from file: {file_path}")
        out = await shazam.recognize(file_path)
        print(f"Recognition result: {out}")
        return out
    except Exception as e:
        print(f"Error recognizing song: {str(e)}")
        return None

# Function to download the song using yt-dlp
def download_song(song_title, artist):
    search_query = f'{song_title} {artist} lyrics'
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, 'downloaded_song.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"Downloading song: {search_query}")
            ydl.download([f'ytsearch:{search_query}'])
            return os.path.join(DOWNLOAD_FOLDER, 'downloaded_song.mp3')
    except Exception as e:
        print(f"Error downloading song: {str(e)}")
        return None

# Uncomment below if you want to run this locally
# if __name__ == "__main__":
#     app.run(debug=False, host='0.0.0.0')
