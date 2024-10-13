import asyncio
import io
from shazamio import Shazam
import yt_dlp
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "https://beatsnatch.onrender.com"}})

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload-audio', methods=['POST'])
def upload_audio():
    if 'audio' not in request.files:
        return jsonify({"success": False, "message": "No audio file uploaded"}), 400

    audio_file = request.files['audio']
    
    # Use an in-memory stream instead of saving to disk
    audio_bytes = io.BytesIO(audio_file.read())

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(recognize_song(audio_bytes))

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

async def recognize_song(audio_bytes):
    shazam = Shazam()
    try:
        # Use the in-memory bytes stream for recognition
        out = await shazam.recognize(audio_bytes)
        return out
    except Exception as e:
        print(f"Error recognizing song: {str(e)}")
        return None

def download_song(song_title, artist):
    search_query = f'{song_title} {artist} lyrics'
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'downloads/downloaded_song.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f'ytsearch:{search_query}'])
            return 'downloads/downloaded_song.mp3'
    except Exception as e:
        print(f"Error downloading song: {str(e)}")
        return None

# if __name__ == "__main__":
#     app.run()
