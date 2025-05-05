from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
from werkzeug.utils import secure_filename
from PIL import Image, ImageDraw, ImageFont, ImageOps
import cv2
import numpy as np
import os
import datetime

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'webp'}
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB limit
app.secret_key = 'your-secret-key-here'  # Change this for production

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def apply_cartoon_filter(img):
    # Convert to RGB (OpenCV uses BGR)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # Edge-preserving filter for cartoon effect
    cartoon = cv2.stylization(img, sigma_s=100, sigma_r=0.3)
    
    # Enhance colors
    hsv = cv2.cvtColor(cartoon, cv2.COLOR_RGB2HSV)
    hsv[:,:,1] = hsv[:,:,1] * 1.2  # Increase saturation
    hsv[:,:,2] = np.clip(hsv[:,:,2] * 1.1, 0, 255)  # Increase brightness
    cartoon = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
    
    return cartoon

def apply_comic_filter(img):
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Apply adaptive threshold
    gray = cv2.medianBlur(gray, 5)
    edges = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, 
                                cv2.THRESH_BINARY, 9, 9)
    
    # Color quantization
    quantized = img.copy()
    for i in range(3):
        quantized[:,:,i] = (quantized[:,:,i]//64)*64
    
    # Combine edges with quantized color
    cartoon = cv2.bitwise_and(quantized, quantized, mask=edges)
    return cartoon

def add_text_to_image(img_pil, text, position, text_size=50, font_path=None):
    draw = ImageDraw.Draw(img_pil)
    
    # Adjust text size based on image dimensions
    base_size = min(img_pil.size) // 10
    text_size = int(base_size * (text_size / 100))
    
    try:
        # Try to load a fun font if available
        if font_path and os.path.exists(font_path):
            font = ImageFont.truetype(font_path, text_size)
        else:
            font = ImageFont.truetype("arial.ttf", text_size)
    except:
        font = ImageFont.load_default()
    
    # Calculate text width and position
    text_width = draw.textlength(text, font=font)
    x = (img_pil.width - text_width) / 2
    
    if position == "top":
        y = 20
    else:  # bottom
        y = img_pil.height - text_size - 30
    
    # Add text with outline
    border_width = max(2, text_size // 20)
    draw.text((x, y), text, font=font, fill="green", 
             stroke_width=border_width, stroke_fill="black")
    return img_pil

@app.route('/')
def index():
    # Clean up old files (older than 1 hour)
    try:
        now = datetime.datetime.now()
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file_time = datetime.datetime.fromtimestamp(os.path.getmtime(filepath))
            if (now - file_time).total_seconds() > 3600:  # 1 hour
                os.remove(filepath)
    except Exception as e:
        print(f"Error cleaning up files: {e}")
    
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        flash('No file selected')
        return redirect(url_for('index'))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('index'))
    
    if file and allowed_file(file.filename):
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{timestamp}_{secure_filename(file.filename)}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Create thumbnail for preview
        img = Image.open(filepath)
        img.thumbnail((400, 400))
        thumb_filename = f"thumb_{filename}"
        thumb_path = os.path.join(app.config['UPLOAD_FOLDER'], thumb_filename)
        img.save(thumb_path)
        
        return redirect(url_for('editor', filename=filename))
    
    flash('Allowed file types are png, jpg, jpeg, webp')
    return redirect(url_for('index'))

@app.route('/editor/<filename>')
def editor(filename):
    thumb_filename = f"thumb_{filename}"
    return render_template('editor.html', 
                         filename=filename,
                         thumb_filename=thumb_filename)

@app.route('/generate_meme', methods=['POST'])
def generate_meme():
    filename = request.form['filename']
    top_text = request.form.get('top_text', '')
    bottom_text = request.form.get('bottom_text', '')
    text_size = int(request.form.get('text_size', 50))
    filter_type = request.form.get('filter', 'none')
    
    # Process image
    img_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    img = cv2.imread(img_path)
    
    if img is None:
        flash('Error processing image')
        return redirect(url_for('index'))
    
    # Apply filters
    if filter_type == 'cartoon':
        img = apply_cartoon_filter(img)
    elif filter_type == 'comic':
        img = apply_comic_filter(img)
    elif filter_type == 'pencil_sketch':
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        inverted = cv2.bitwise_not(gray)
        blurred = cv2.GaussianBlur(inverted, (21, 21), 0)
        inverted_blurred = cv2.bitwise_not(blurred)
        img = cv2.divide(gray, inverted_blurred, scale=256.0)
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    
    # Convert to PIL and add text
    img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    
    # Try to find a fun font
    font_path = None
    possible_fonts = [
        'impact.ttf', 
        'arial.ttf', 
        '/usr/share/fonts/truetype/freefont/Impact.ttf',
        '/Library/Fonts/Impact.ttf'
    ]
    
    for font in possible_fonts:
        if os.path.exists(font):
            font_path = font
            break
    
    if top_text:
        img_pil = add_text_to_image(img_pil, top_text, "top", text_size, font_path)
    if bottom_text:
        img_pil = add_text_to_image(img_pil, bottom_text, "bottom", text_size, font_path)
    
    # Save meme
    meme_filename = f"meme_{filename}"
    meme_path = os.path.join(app.config['UPLOAD_FOLDER'], meme_filename)
    
    # Convert to RGB if needed and save
    if img_pil.mode != 'RGB':
        img_pil = img_pil.convert('RGB')
    
    img_pil.save(meme_path, quality=95)
    
    # Create a thumbnail for display
    img_pil.thumbnail((600, 600))
    display_filename = f"display_{meme_filename}"
    display_path = os.path.join(app.config['UPLOAD_FOLDER'], display_filename)
    img_pil.save(display_path)
    
    return redirect(url_for('view_meme', 
                          meme_filename=meme_filename,
                          display_filename=display_filename))

@app.route('/view_meme/<meme_filename>/<display_filename>')
def view_meme(meme_filename, display_filename):
    return render_template('view_meme.html',
                         meme_filename=meme_filename,
                         display_filename=display_filename)

@app.route('/download_meme/<filename>')
def download_meme(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)