# app.py - Render.com compatible version
from flask import Flask, request, jsonify
import subprocess
import base64
import os
import shutil
import tempfile
import requests
from datetime import datetime

app = Flask(__name__)

def check_wkhtmltopdf():
    """Check if wkhtmltopdf is available"""
    return shutil.which('wkhtmltopdf') is not None

def convert_with_weasyprint_fallback(url):
    """Fallback using WeasyPrint (pure Python, no system deps)"""
    try:
        from weasyprint import HTML
        
        # Fetch HTML content
        response = requests.get(url, timeout=30)
        html_content = response.text
        
        # Generate PDF with WeasyPrint
        html_doc = HTML(string=html_content, base_url=url)
        pdf_bytes = html_doc.write_pdf()
        
        print(f"WeasyPrint PDF generated ({len(pdf_bytes)} bytes)")
        return pdf_bytes
    except ImportError:
        print("WeasyPrint not available")
        return None
    except Exception as e:
        print(f"WeasyPrint error: {e}")
        return None

def convert_url_to_pdf(url, wait_time=15):
    """Convert URL to PDF - try wkhtmltopdf first, fallback to WeasyPrint"""
    
    # Try wkhtmltopdf first
    if check_wkhtmltopdf():
        print("Using wkhtmltopdf...")
        try:
            cmd = [
                'wkhtmltopdf',
                '--page-size', 'A4',
                '--margin-top', '0.5in',
                '--margin-right', '0.5in',
                '--margin-bottom', '0.5in', 
                '--margin-left', '0.5in',
                '--no-header-line',
                '--no-footer-line',
                '--encoding', 'UTF-8',
                '--javascript-delay', str(wait_time * 1000),
                '--enable-javascript',
                '--load-error-handling', 'ignore',
                url,
                '-'
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=90)
            
            if result.returncode == 0 and result.stdout:
                print(f"wkhtmltopdf success ({len(result.stdout)} bytes)")
                return result.stdout
            else:
                print(f"wkhtmltopdf failed: {result.stderr.decode('utf-8', errors='ignore')[:200]}")
        except Exception as e:
            print(f"wkhtmltopdf error: {e}")
    
    # Fallback to WeasyPrint
    print("Falling back to WeasyPrint...")
    return convert_with_weasyprint_fallback(url)

@app.route("/convert-to-pdf-base64", methods=["POST"])
def convert_to_pdf_base64():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON required', 'success': False}), 400
            
        url = data.get('url')
        wait_time = int(data.get('wait_time', 15))

        if not url:
            return jsonify({'error': 'URL required', 'success': False}), 400

        print(f"Converting: {url}")
        pdf_bytes = convert_url_to_pdf(url, wait_time)

        if pdf_bytes:
            pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"kairali_invoice_{timestamp}.pdf"
            
            return jsonify({
                'success': True,
                'pdf_base64': pdf_base64,
                'filename': filename,
                'size_bytes': len(pdf_bytes)
            })
        else:
            return jsonify({'error': 'PDF generation failed', 'success': False}), 500

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e), 'success': False}), 500

@app.route("/health", methods=["GET"])
def health():
    wkhtmltopdf_available = check_wkhtmltopdf()
    
    try:
        from weasyprint import HTML
        weasyprint_available = True
    except ImportError:
        weasyprint_available = False
    
    return jsonify({
        "status": "healthy",
        "wkhtmltopdf_available": wkhtmltopdf_available,
        "weasyprint_available": weasyprint_available,
        "service": "Kairali PDF API (Render)"
    })

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Kairali Invoice PDF API",
        "status": "running",
        "platform": "Render.com"
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
    
