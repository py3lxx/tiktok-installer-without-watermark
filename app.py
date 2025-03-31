from flask import Flask, request, jsonify, send_file, send_from_directory
from werkzeug.utils import secure_filename
from flask_cors import CORS
import yt_dlp
import os
import tempfile
import json
import logging
import mimetypes
import time

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='.')
CORS(app)

@app.route('/')
def serve_index():
    return send_file('index.html')

@app.route('/downloads/<path:filename>')
def download_file(filename):
    try:
        # Güvenli dosya adı oluştur
        safe_filename = secure_filename(filename)
        downloads_dir = os.path.join(os.path.dirname(__file__), 'downloads')
        filepath = os.path.join(downloads_dir, safe_filename)
        
        if not os.path.exists(filepath):
            logger.error(f"File not found: {filepath}")
            return "Dosya bulunamadı", 404

        # Dosya türünü belirle
        mime_type, _ = mimetypes.guess_type(filepath)
        if not mime_type:
            mime_type = 'application/octet-stream'

        return send_file(
            filepath,
            mimetype=mime_type,
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        logger.exception(f"Error serving file: {filename}")
        return str(e), 500

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

@app.route('/api/download', methods=['POST'])
def download_video():
    try:
        logger.debug("Received download request")
        request_data = request.get_data()
        logger.debug(f"Raw request data: {request_data}")

        try:
            data = request.get_json()
            if data is None:
                logger.error("No JSON data in request")
                return jsonify({'error': 'JSON verisi bulunamadı'}), 400
        except Exception as e:
            logger.error(f"JSON parsing error: {e}")
            return jsonify({'error': 'Geçersiz JSON verisi'}), 400

        url = data.get('url')
        if not url:
            logger.error("Missing URL")
            return jsonify({'error': 'Video bağlantısı gerekli'}), 400

        if 'tiktok.com' not in url:
            logger.error("Not a TikTok URL")
            return jsonify({'error': 'Lütfen geçerli bir TikTok video bağlantısı girin'}), 400

        # Create temporary directory for download
        temp_dir = tempfile.mkdtemp()
        logger.debug(f"Created temp directory: {temp_dir}")
        
        # Configure yt-dlp options
        ydl_opts = {
            'format': 'best',
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'quiet': False,
            'no_warnings': False,
            'extract_flat': False,
            'add_header': [
                'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
                'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language: en-US,en;q=0.9',
                'Sec-Fetch-Site: none',
                'Sec-Fetch-Mode: navigate',
                'Sec-Fetch-User: ?1',
                'Sec-Fetch-Dest: document',
                'Sec-Ch-Ua: "Chromium";v="123"',
                'Sec-Ch-Ua-Mobile: ?0',
                'Sec-Ch-Ua-Platform: "Windows"',
                'Accept-Encoding: gzip, deflate, br'
            ],
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9'
            }
        }

        # Download video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                logger.info(f"Starting download from URL: {url}")
                info = ydl.extract_info(url, download=True)
                logger.debug(f"Video info: {info}")
                
                video_path = ydl.prepare_filename(info)
                logger.info(f"Video downloaded to: {video_path}")
                
                if not os.path.exists(video_path):
                    logger.error(f"Video file not found at: {video_path}")
                    return jsonify({'error': 'Video dosyası bulunamadı'}), 500
                
                # Get video format
                format_ext = os.path.splitext(video_path)[1][1:]
                
                # Move video to a more permanent location
                output_dir = os.path.join(os.path.dirname(__file__), 'downloads')
                os.makedirs(output_dir, exist_ok=True)
                
                # Benzersiz bir dosya adı oluştur
                timestamp = int(time.time())
                output_filename = f"tiktok_video_{timestamp}.{format_ext}"
                output_path = os.path.join(output_dir, output_filename)
                
                # If file exists, remove it
                if os.path.exists(output_path):
                    logger.debug(f"Removing existing file: {output_path}")
                    os.remove(output_path)
                    
                os.rename(video_path, output_path)
                logger.info(f"Video moved to: {output_path}")
                
                # Create response with download URL
                response_data = {
                    'downloadUrl': f'/downloads/{output_filename}',
                    'format': format_ext
                }
                logger.debug(f"Sending response: {json.dumps(response_data)}")
                return jsonify(response_data)

            except Exception as e:
                logger.exception("Error during download")
                error_message = str(e)
                if "Unable to extract video title" in error_message:
                    error_message = "Video bulunamadı veya özel bir video olabilir"
                elif "Unable to extract sigi state" in error_message:
                    error_message = "TikTok'un son güncellemesi nedeniyle şu anda video indirilemiyor. Lütfen daha sonra tekrar deneyin."
                logger.error(error_message)
                return jsonify({'error': f"Video indirme hatası: {error_message}"}), 500
            
    except Exception as e:
        logger.exception("General error")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Create downloads directory if it doesn't exist
    downloads_dir = os.path.join(os.path.dirname(__file__), 'downloads')
    os.makedirs(downloads_dir, exist_ok=True)
    logger.info(f"Downloads directory: {downloads_dir}")
    
    # Register common MIME types
    mimetypes.add_type('video/mp4', '.mp4')
    mimetypes.add_type('video/webm', '.webm')
    mimetypes.add_type('video/quicktime', '.mov')
    
    app.run(debug=True, port=5000)
