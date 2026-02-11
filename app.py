from flask import Flask, render_template, request, send_file, jsonify
from flask_cors import CORS
import qrcode
from qrcode.image.svg import SvgPathImage
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer, CircleModuleDrawer, GappedSquareModuleDrawer
from qrcode.image.styles.colormasks import SolidFillColorMask, RadialGradiantColorMask
from PIL import Image
import io
import re
from urllib.parse import urlparse
import base64

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

def get_domain_name(url):
    """Extract domain name from URL and create a safe filename"""
    try:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        domain = domain.replace('www.', '')
        domain = domain.split(':')[0]
        safe_domain = re.sub(r'[^\w\-.]', '_', domain)
        safe_domain = safe_domain.rstrip('.')
        
        return safe_domain if safe_domain else "qrcode"
    except Exception:
        return "qrcode"

def create_styled_qr(url, theme):
    """Create styled QR code based on selected theme"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    if theme == "matrix":
        img = qr.make_image(
            image_factory=StyledPilImage,
            module_drawer=RoundedModuleDrawer(),
            color_mask=SolidFillColorMask(
                back_color=(0, 0, 0),
                front_color=(0, 255, 65)
            )
        )
    elif theme == "cyberpunk":
        img = qr.make_image(
            image_factory=StyledPilImage,
            module_drawer=CircleModuleDrawer(),
            color_mask=RadialGradiantColorMask(
                back_color=(10, 10, 35),
                center_color=(255, 0, 255),
                edge_color=(0, 255, 255)
            )
        )
    elif theme == "terminal":
        img = qr.make_image(
            image_factory=StyledPilImage,
            module_drawer=GappedSquareModuleDrawer(),
            color_mask=SolidFillColorMask(
                back_color=(30, 30, 30),
                front_color=(0, 255, 0)
            )
        )
    else:
        img = qr.make_image(fill_color="black", back_color="white")
    
    return img

def generate_qr_code(url, output_format, theme=None):
    """Generate QR code and return as bytes"""
    domain = get_domain_name(url)
    
    if output_format == "styled":
        img = create_styled_qr(url, theme)
        filename = f"{domain}_{theme}.png"
        img_format = "PNG"
    elif output_format == "svg":
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(image_factory=SvgPathImage)
        filename = f"{domain}.svg"
        img_format = "SVG"
    else:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        if output_format == "jpeg":
            img = img.convert("RGB")
            filename = f"{domain}.jpeg"
            img_format = "JPEG"
        else:
            filename = f"{domain}.png"
            img_format = "PNG"
    
    # Save to bytes
    img_io = io.BytesIO()
    if img_format == "SVG":
        img.save(img_io)
    else:
        img.save(img_io, img_format)
    img_io.seek(0)
    
    return img_io, filename, img_format

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.json
        url = data.get('url', '').strip()
        output_format = data.get('format', 'png')
        theme = data.get('theme', None)
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        img_io, filename, img_format = generate_qr_code(url, output_format, theme)
        
        # Convert to base64 for preview
        img_io.seek(0)
        img_base64 = base64.b64encode(img_io.read()).decode()
        
        if img_format == "SVG":
            data_uri = f"data:image/svg+xml;base64,{img_base64}"
        else:
            data_uri = f"data:image/{img_format.lower()};base64,{img_base64}"
        
        return jsonify({
            'success': True,
            'image': data_uri,
            'filename': filename
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download', methods=['POST'])
def download():
    try:
        data = request.json
        url = data.get('url', '').strip()
        output_format = data.get('format', 'png')
        theme = data.get('theme', None)
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        img_io, filename, img_format = generate_qr_code(url, output_format, theme)
        
        mimetype = 'image/svg+xml' if img_format == 'SVG' else f'image/{img_format.lower()}'
        
        return send_file(
            img_io,
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

import os

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)