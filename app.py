import wave
import asyncio
from shazamio import Shazam
import yt_dlp
import os
import re
import requests
from urllib.parse import quote
from flask import Flask, make_response, request, jsonify, send_file, render_template, url_for

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

UPLOAD_FOLDER = 'uploads'
DOWNLOAD_FOLDER = 'downloads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

@app.route('/upload-audio', methods=['POST'])
def upload_audio():
    if 'audio' not in request.files:
        return jsonify({"success": False, "message": "No audio file uploaded"}), 400

    audio_file = request.files['audio']
    file_path = os.path.join(UPLOAD_FOLDER, 'recorded_audio.wav')
    audio_file.save(file_path)


    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(recognize_song(file_path))

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

@app.route('/download-song', methods=['GET'])
def download_song_route():
    file_path = os.path.join(DOWNLOAD_FOLDER, "downloaded_song.mp3")
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return jsonify({"success": False, "message": "File not found"}), 404

async def recognize_song(file_path):
    shazam = Shazam()
    try:
        out = await shazam.recognize(file_path)
        return out
    except Exception as e:
        print(f"Error recognizing song: {str(e)}")
        return None

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
            ydl.download([f'ytsearch:{search_query}'])
            return os.path.join(DOWNLOAD_FOLDER, 'downloaded_song.mp3')
    except Exception as e:
        print(f"Error downloading song: {str(e)}")
        return None

if __name__ == "__main__":
    app.run()
