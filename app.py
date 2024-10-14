import os
import asyncio
from flask import Flask, render_template, request, jsonify, send_file
from shazamio import Shazam
import yt_dlp
import subprocess
import tempfile

app = Flask(__name__)

# Ensure upload folder exists
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
async def upload_audio():
    if 'audio_data' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    # Save the uploaded audio file
    audio_file = request.files['audio_data']
    file_path = os.path.join(UPLOAD_FOLDER, audio_file.filename)
    audio_file.save(file_path)

    # Recognize song using Shazam
    try:
        result = await recognize_song(file_path)
        if 'track' in result:
            song_title = result['track']['title']
            artist = result['track']['subtitle']
            return jsonify({"song_title": song_title, "artist": artist})
        else:
            return jsonify({"error": "Song not recognized"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

async def recognize_song(file_path):
    shazam = Shazam()
    try:
        result = await shazam.recognize(file_path)
        return result
    except Exception as e:
        raise e

@app.route('/download', methods=['POST'])
def download_song():
    data = request.get_json()
    song_title = data.get("song_title")
    artist = data.get("artist")

    if not song_title or not artist:
        return jsonify({"error": "Invalid song information"}), 400

    # Search and download the song using yt-dlp
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            download_path = os.path.join(tmpdir, f"{song_title}.mp3")
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': download_path,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([f"ytsearch:{song_title} {artist}"])

            return send_file(download_path, as_attachment=True, download_name=f"{song_title}.mp3")
    except Exception as e:
        return jsonify({"error": f"Failed to download song: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
