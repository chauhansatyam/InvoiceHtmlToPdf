# app.py - Chrome with Railway-specific flags
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
    """Convert URL to PDF using Chrome with Railway-specific flags."""
    chrome_binary = find_chrome_binary()
    if not chrome_binary:
        raise Exception("Chrome binary not found")
    
    # Create temporary file for PDF output
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
        pdf_path = tmp_file.name
    
    try:
        print(f"Converting URL: {url}")
        print(f"Chrome binary: {chrome_binary}")
        print(f"PDF output: {pdf_path}")
        
        # Comprehensive Chrome flags for containerized environments
        cmd = [
            chrome_binary,
            '--headless',
            '--no-sandbox',
            '--disable-gpu',
            '--disable-dev-shm-usage',
            '--disable-extensions',
            '--disable-plugins',
            '--disable-background-networking',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
            '--disable-features=TranslateUI,BlinkGenPropertyTrees',
            '--disable-web-security',
            '--disable-features=VizDisplayCompositor',
            '--disable-ipc-flooding-protection',
            '--single-process',
            '--no-zygote',
            '--disable-dev-tools',
            '--disable-logging',
            '--disable-software-rasterizer',
            '--hide-scrollbars',
            # Font and display fixes for Railway/Nix
            '--font-render-hinting=none',
            '--disable-font-subpixel-positioning',
            '--force-color-profile=srgb',
            '--disable-lcd-text',
            # Network and system fixes
            '--disable-dbus',
            '--disable-features=AudioServiceOutOfProcess',
            '--disable-features=DialMediaRouteProvider',
            '--no-first-run',
            '--no-default-browser-check',
            # PDF specific
            f'--virtual-time-budget={wait_time * 1000}',
            '--run-all-compositor-stages-before-draw',
            f'--print-to-pdf={pdf_path}',
            '--print-to-pdf-no-header',
            # Target URL
            url
        ]
        
        print("Running Chrome with comprehensive flags...")
        
        # Set environment variables to handle missing system resources
        env = os.environ.copy()
        env.update({
            'DISPLAY': ':99',
            'CHROME_DEVEL_SANDBOX': '',
            'FONTCONFIG_PATH': '/tmp',
            'XDG_RUNTIME_DIR': '/tmp'
        })
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=90,  # Increased timeout
            cwd='/tmp',
            env=env
        )
        
        print(f"Chrome exit code: {result.returncode}")
        if result.stdout:
            print(f"Chrome stdout: {result.stdout[:500]}...")  # Truncate long output
        if result.stderr:
            print(f"Chrome stderr (first 500 chars): {result.stderr[:500]}...")
        
        # Wait longer for file to be written
        time.sleep(3)
        
        # Check if PDF was created
        if os.path.exists(pdf_path):
            file_size = os.path.getsize(pdf_path)
            print(f"PDF file size: {file_size} bytes")
            
            if file_size > 0:
                with open(pdf_path, 'rb') as f:
                    pdf_bytes = f.read()
                print(f"PDF generated successfully ({len(pdf_bytes)} bytes)")
                return pdf_bytes
            else:
                print("PDF file is empty")
                return None
        else:
            print("PDF file not created")
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
        wait_time = int(data.get('wait_time', 30))  # Increased default

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
            return jsonify({'error': 'PDF generation failed - Chrome could not generate PDF', 'success': False}), 500

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
        "service": "Kairali PDF API (Railway Optimized)"
    })

@app.route("/test-simple", methods=["GET"])
def test_simple():
    """Test Chrome with the simplest possible page"""
    try:
        # Create a simple local HTML file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as tmp_file:
            tmp_file.write('<html><body><h1>Test Page</h1><p>This is a test.</p></body></html>')
            html_path = tmp_file.name
        
        try:
            result = convert_url_to_pdf_direct(f"file://{html_path}", 5)
            return jsonify({
                "test": "success" if result else "failed",
                "pdf_size": len(result) if result else 0
            })
        finally:
            os.unlink(html_path)
            
    except Exception as e:
        return jsonify({"test": "error", "error": str(e)})

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Kairali Invoice PDF API (Railway Optimized)",
        "status": "running",
        "endpoints": {
            "/health": "GET - Health check",
            "/test-simple": "GET - Test Chrome with simple HTML", 
            "/convert-to-pdf-base64": "POST - Convert URL to PDF"
        }
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
