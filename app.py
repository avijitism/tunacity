import os
import wave
import asyncio
import io
from shazamio import Shazam
import yt_dlp
from flask import Flask, make_response, request, jsonify, send_file, render_template
from flask_cors import CORS


app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload-audio', methods=['POST'])
async def upload_audio():
    if 'audio' not in request.files:
        return jsonify({"success": False, "message": "No audio file uploaded"}), 400

    audio_file = request.files['audio']
    audio_data = audio_file.read()  # Read audio data into memory

    # Recognize song asynchronously
    result = await recognize_song(audio_data)

    if result:
        song_title = result['track']['title']
        artist = result['track']['subtitle']
        downloaded_file = await download_song(song_title, artist)  # Await download process
        if downloaded_file:
            return jsonify({"success": True, "songTitle": song_title, "artist": artist}), 200
        else:
            return jsonify({"success": False, "message": "Song download failed"}), 500
    else:
        return jsonify({"success": False, "message": "Song not recognized"}), 400

@app.route('/download-song', methods=['GET'])
def download_song_route():
    file_path = os.path.join('downloads', "downloaded_song.mp3")
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return jsonify({"success": False, "message": "File not found"}), 404

async def recognize_song(audio_data):
    """ Recognize song from audio file """
    shazam = Shazam()
    try:
        out = await shazam.recognize_song(io.BytesIO(audio_data))  # Pass in-memory BytesIO object
        return out
    except Exception as e:
        print(f"Error recognizing song: {str(e)}")
        return None

async def download_song(song_title, artist):
    """ Download song from YouTube using yt-dlp """
    search_query = f'{song_title} {artist} lyrics'
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': '-',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(f'ytsearch:{search_query}', download=False)
            video_url = info_dict['entries'][0]['url']
            return video_url
    except Exception as e:
        print(f"Error downloading song: {str(e)}")
        return None

if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=10000)

