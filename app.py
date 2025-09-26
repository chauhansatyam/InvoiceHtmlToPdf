# app.py - Direct Chrome PDF generation (no Selenium)
from flask import Flask, request, jsonify
import subprocess
import base64
import os
import time
import tempfile
from datetime import datetime

app = Flask(__name__)

def find_chrome_binary():
    """Find Chrome binary in Railway environment."""
    candidates = [
        "/root/.nix-profile/bin/chromium",
        "/usr/bin/chromium",
        "/usr/bin/google-chrome"
    ]
    for c in candidates:
        if os.path.exists(c) and os.access(c, os.X_OK):
            print(f"Found Chrome binary: {c}")
            return c
    return None

def convert_url_to_pdf_direct(url, wait_time=25):
    """Convert URL to PDF using Chrome directly via subprocess."""
    chrome_binary = find_chrome_binary()
    if not chrome_binary:
        raise Exception("Chrome binary not found")
    
    # Create temporary file for PDF output
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
        pdf_path = tmp_file.name
    
    try:
        print(f"Converting URL: {url}")
        print(f"Chrome binary: {chrome_binary}")
        print(f"Wait time: {wait_time} seconds")
        
        # Chrome command for direct PDF generation
        cmd = [
            chrome_binary,
            '--headless',
            '--no-sandbox',
            '--disable-gpu',
            '--disable-dev-shm-usage',
            '--disable-extensions',
            '--disable-plugins',
            '--disable-images',  # Faster loading
            '--hide-scrollbars',
            '--single-process',
            '--disable-web-security',
            '--disable-features=VizDisplayCompositor',
            f'--virtual-time-budget={wait_time * 1000}',  # Wait for JS
            '--run-all-compositor-stages-before-draw',
            f'--print-to-pdf={pdf_path}',
            '--print-to-pdf-no-header',
            url
        ]
        
        print("Running Chrome command...")
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=60,
            cwd='/tmp'
        )
        
        print(f"Chrome exit code: {result.returncode}")
        if result.stdout:
            print(f"Chrome stdout: {result.stdout}")
        if result.stderr:
            print(f"Chrome stderr: {result.stderr}")
        
        # Wait a bit for file to be written
        time.sleep(2)
        
        # Check if PDF was created
        if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
            print(f"PDF generated successfully ({len(pdf_bytes)} bytes)")
            return pdf_bytes
        else:
            print("PDF file not created or empty")
            return None
            
    except subprocess.TimeoutExpired:
        print("Chrome command timed out")
        return None
    except Exception as e:
        print(f"Error generating PDF: {e}")
        return None
    finally:
        # Clean up temp file
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)

@app.route("/convert-to-pdf-base64", methods=["POST"])
def convert_to_pdf_base64():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON required', 'success': False}), 400
            
        url = data.get('url')
        wait_time = int(data.get('wait_time', 25))

        if not url:
            return jsonify({'error': 'URL required', 'success': False}), 400

        print(f"Starting conversion: {url}")
        pdf_bytes = convert_url_to_pdf_direct(url, wait_time)

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
        print(f"Error in endpoint: {e}")
        return jsonify({'error': str(e), 'success': False}), 500

@app.route("/health", methods=["GET"])
def health():
    chrome_binary = find_chrome_binary()
    return jsonify({
        "status": "healthy",
        "chrome_binary": chrome_binary,
        "chrome_available": bool(chrome_binary),
        "service": "Kairali PDF API"
    })

@app.route("/test-chrome", methods=["GET"])
def test_chrome():
    """Test Chrome directly with a simple page"""
    try:
        result = convert_url_to_pdf_direct("https://example.com", 10)
        return jsonify({
            "test": "success" if result else "failed",
            "pdf_size": len(result) if result else 0
        })
    except Exception as e:
        return jsonify({"test": "error", "error": str(e)})

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Kairali Invoice PDF API (Direct Chrome)",
        "status": "running",
        "endpoints": {
            "/health": "GET - Health check",
            "/test-chrome": "GET - Test Chrome with example.com", 
            "/convert-to-pdf-base64": "POST - Convert URL to PDF"
        }
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
