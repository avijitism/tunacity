import os
import re
import asyncio
import yt_dlp
import requests
from shazamio import Shazam
from flask import Flask, request, render_template, redirect, url_for, flash, send_file
from urllib.parse import quote

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DOWNLOAD_FOLDER'] = 'static/downloads'

# Ensure directories exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
if not os.path.exists(app.config['DOWNLOAD_FOLDER']):
    os.makedirs(app.config['DOWNLOAD_FOLDER'])


def sanitize_filename(filename):
    """Sanitize filename to prevent filesystem issues."""
    return re.sub(r'[\\/*?:"<>|]', "", filename)


# Main route for the app, where users upload audio files
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'audio_file' not in request.files:
            flash('No file selected')
            return redirect(request.url)

        file = request.files['audio_file']
        if file.filename == '':
            flash('No file selected')
            return redirect(request.url)

        if file:
            # Save file to the upload folder
            filename = sanitize_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Recognize song asynchronously
            result = asyncio.run(recognize_song(file_path))

            if result and 'track' in result:
                song_title = result['track']['title']
                artist = result['track']['subtitle']
                flash(f"Recognized: {song_title} by {artist}")

                # Redirect to the download route to download song
                return redirect(url_for('download_song', song_title=song_title, artist=artist))
            else:
                flash("Sorry, the song could not be recognized.")
                return redirect(request.url)

    return render_template('index.html')


async def recognize_song(file_path):
    """Uses Shazam API to recognize the song."""
    shazam = Shazam()
    try:
        return await shazam.recognize(file_path)
    except Exception as e:
        flash(f"Error recognizing song: {str(e)}")
        return None


@app.route('/download')
def download_song():
    """Download song based on the recognized title and artist."""
    song_title = request.args.get('song_title')
    artist = request.args.get('artist')

    # Search for the song on YouTube and download the audio
    try:
        download_path = download_from_youtube(song_title, artist)
        return send_file(download_path, as_attachment=True)
    except Exception as e:
        flash(f"Error downloading the song: {str(e)}")
        return redirect(url_for('index'))


def download_from_youtube(song_title, artist):
    """Downloads the audio track from YouTube."""
    search_query = f"{song_title} {artist} lyrics"
    query = quote(search_query)
    url = f"https://www.youtube.com/results?search_query={query}"

    # Search YouTube for the song
    response = requests.get(url)
    video_id = re.search(r"watch\?v=(\S{11})", response.text)

    if not video_id:
        raise Exception("YouTube video not found for the song.")

    video_url = f"https://www.youtube.com/watch?v={video_id.group(1)}"
    sanitized_title = sanitize_filename(f"{song_title} - {artist or 'Unknown Artist'}")

    # Path to save the mp3
    download_dir = app.config['DOWNLOAD_FOLDER']
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(download_dir, f"{sanitized_title}.%(ext)s"),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True
    }

    # Download the audio using yt-dlp
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

    # Return the path of the downloaded mp3
    return os.path.join(download_dir, f"{sanitized_title}.mp3")

# Uncomment below if you want to run this locally
# if __name__ == "__main__":
#     app.run(debug=False, host='0.0.0.0')
