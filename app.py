# app.py - wkhtmltopdf version
from flask import Flask, request, jsonify
import subprocess
import base64
import os
import shutil
import tempfile
from datetime import datetime

app = Flask(__name__)

def check_wkhtmltopdf():
    """Check if wkhtmltopdf is available"""
    return shutil.which('wkhtmltopdf') is not None

def convert_url_to_pdf_wkhtmltopdf(url, wait_time=15):
    """Convert URL to PDF using wkhtmltopdf"""
    
    if not check_wkhtmltopdf():
        raise Exception("wkhtmltopdf not found on system")
    
    try:
        print(f"Converting URL: {url}")
        print(f"JavaScript delay: {wait_time} seconds")
        
        # wkhtmltopdf command with comprehensive options
        cmd = [
            'wkhtmltopdf',
            '--page-size', 'A4',
            '--orientation', 'Portrait',
            '--margin-top', '0.5in',
            '--margin-right', '0.5in', 
            '--margin-bottom', '0.5in',
            '--margin-left', '0.5in',
            '--encoding', 'UTF-8',
            '--no-header-line',  # Remove header line
            '--no-footer-line',  # Remove footer line
            '--disable-smart-shrinking',
            '--print-media-type',
            '--no-background',  # Can help with rendering
            f'--javascript-delay', str(wait_time * 1000),  # Wait for JS in milliseconds
            '--enable-javascript',
            '--debug-javascript',  # For debugging
            '--load-error-handling', 'ignore',
            '--load-media-error-handling', 'ignore',
            url,
            '-'  # Output to stdout
        ]
        
        print("Running wkhtmltopdf command...")
        print(f"Command: {' '.join(cmd[:10])}...")  # Show first part of command
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=120,  # 2 minute timeout
            cwd='/tmp'
        )
        
        print(f"wkhtmltopdf exit code: {result.returncode}")
        
        if result.stderr:
            stderr_text = result.stderr.decode('utf-8', errors='ignore')
            print(f"wkhtmltopdf stderr: {stderr_text[:500]}...")  # Truncate long output
        
        if result.returncode == 0 and result.stdout:
            pdf_bytes = result.stdout
            print(f"PDF generated successfully ({len(pdf_bytes)} bytes)")
            return pdf_bytes
        else:
            print(f"wkhtmltopdf failed with exit code {result.returncode}")
            return None
            
    except subprocess.TimeoutExpired:
        print("wkhtmltopdf command timed out")
        return None
    except Exception as e:
        print(f"Error generating PDF: {e}")
        return None

@app.route("/convert-to-pdf-base64", methods=["POST"])
def convert_to_pdf_base64():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON required', 'success': False}), 400
            
        url = data.get('url')
        wait_time = int(data.get('wait_time', 15))  # Default 15 seconds

        if not url:
            return jsonify({'error': 'URL required', 'success': False}), 400

        print(f"Starting conversion: {url}")
        pdf_bytes = convert_url_to_pdf_wkhtmltopdf(url, wait_time)

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
    wkhtmltopdf_available = check_wkhtmltopdf()
    wkhtmltopdf_path = shutil.which('wkhtmltopdf')
    
    return jsonify({
        "status": "healthy",
        "wkhtmltopdf_available": wkhtmltopdf_available,
        "wkhtmltopdf_path": wkhtmltopdf_path,
        "service": "Kairali PDF API (wkhtmltopdf)"
    })

@app.route("/test-wkhtmltopdf", methods=["GET"])
def test_wkhtmltopdf():
    """Test wkhtmltopdf with a simple page"""
    try:
        # Test with example.com
        result = convert_url_to_pdf_wkhtmltopdf("https://example.com", 5)
        return jsonify({
            "test": "success" if result else "failed",
            "pdf_size": len(result) if result else 0,
            "wkhtmltopdf_available": check_wkhtmltopdf()
        })
    except Exception as e:
        return jsonify({"test": "error", "error": str(e)})

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Kairali Invoice PDF API (wkhtmltopdf)",
        "status": "running",
        "endpoints": {
            "/health": "GET - Health check",
            "/test-wkhtmltopdf": "GET - Test with example.com",
            "/convert-to-pdf-base64": "POST - Convert URL to PDF"
        }
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
