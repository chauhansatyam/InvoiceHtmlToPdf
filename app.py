# app.py - Enhanced version with forced wkhtmltopdf installation
from flask import Flask, request, jsonify
import subprocess
import base64
import os
import shutil
import tempfile
import requests
from datetime import datetime
import time

app = Flask(__name__)

def force_install_wkhtmltopdf():
    """Aggressively try to install wkhtmltopdf on Render"""
    try:
        print("Attempting to install wkhtmltopdf...")
        
        # Method 1: Try apt-get with sudo-like permissions
        try:
            subprocess.run(['apt-get', 'update'], check=False, capture_output=True)
            result = subprocess.run(['apt-get', 'install', '-y', 'wkhtmltopdf'], 
                                  check=False, capture_output=True, timeout=120)
            if result.returncode == 0:
                print("wkhtmltopdf installed via apt-get")
                return True
        except Exception as e:
            print(f"apt-get method failed: {e}")
        
        # Method 2: Download and install .deb package directly
        try:
            print("Trying direct .deb installation...")
            deb_url = "https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-2/wkhtmltox_0.12.6.1-2.focal_amd64.deb"
            
            # Download
            subprocess.run(['wget', '-O', '/tmp/wkhtmltox.deb', deb_url], 
                         check=True, timeout=60)
            
            # Install
            subprocess.run(['dpkg', '-i', '/tmp/wkhtmltox.deb'], check=False)
            subprocess.run(['apt-get', '-f', 'install', '-y'], check=False)
            
            if shutil.which('wkhtmltopdf'):
                print("wkhtmltopdf installed via .deb package")
                return True
                
        except Exception as e:
            print(f"Direct .deb installation failed: {e}")
        
        # Method 3: Try alternative binary
        try:
            print("Trying alternative binary...")
            binary_url = "https://github.com/wkhtmltopdf/wkhtmltopdf/releases/download/0.12.5/wkhtmltox_0.12.5-1.focal_amd64.deb"
            subprocess.run(['wget', '-O', '/tmp/wkhtmltox_alt.deb', binary_url], 
                         check=True, timeout=60)
            subprocess.run(['dpkg', '-i', '/tmp/wkhtmltox_alt.deb'], check=False)
            subprocess.run(['apt-get', '-f', 'install', '-y'], check=False)
            
            if shutil.which('wkhtmltopdf'):
                print("wkhtmltopdf installed via alternative binary")
                return True
                
        except Exception as e:
            print(f"Alternative binary failed: {e}")
            
        print("All wkhtmltopdf installation methods failed")
        return False
        
    except Exception as e:
        print(f"wkhtmltopdf installation error: {e}")
        return False

def check_wkhtmltopdf():
    """Check if wkhtmltopdf is available"""
    return shutil.which('wkhtmltopdf') is not None

def convert_with_wkhtmltopdf_preload(url, wait_time=30):
    """Pre-load content, then convert with wkhtmltopdf"""
    try:
        print(f"Pre-loading content from: {url}")
        
        # First, fetch the page to trigger loading, then wait
        response = requests.get(url, timeout=30)
        print(f"Initial fetch completed, status: {response.status_code}")
        
        # Add extra wait time for the page to fully load its JavaScript
        time.sleep(5)
        
        # Use wkhtmltopdf with aggressive JavaScript settings
        cmd = [
            'wkhtmltopdf',
            '--page-size', 'A4',
            '--margin-top', '0.4in',
            '--margin-right', '0.4in', 
            '--margin-bottom', '0.4in',
            '--margin-left', '0.4in',
            '--encoding', 'UTF-8',
            '--no-header-line',
            '--no-footer-line',
            '--enable-javascript',
            '--javascript-delay', str(wait_time * 1000),  # Convert to milliseconds
            '--debug-javascript',
            '--load-error-handling', 'ignore',
            '--load-media-error-handling', 'ignore',
            '--disable-smart-shrinking',
            '--print-media-type',
            '--zoom', '1.0',
            '--dpi', '96',
            # More aggressive settings for dynamic content
            '--enable-local-file-access',
            '--allow', url,
            '--custom-header', 'User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            '--window-status', 'ready',  # Wait for window.status = 'ready'
            '--run-script', 'window.setTimeout(function(){window.status="ready";}, ' + str(wait_time * 1000) + ');',
            url,
            '-'
        ]
        
        print(f"Running wkhtmltopdf with {wait_time}s JavaScript delay...")
        
        result = subprocess.run(cmd, capture_output=True, timeout=180)
        
        if result.returncode == 0 and result.stdout:
            print(f"Success! PDF size: {len(result.stdout)} bytes")
            return result.stdout
        else:
            stderr_text = result.stderr.decode('utf-8', errors='ignore')
            print(f"wkhtmltopdf failed. Stderr: {stderr_text[:300]}")
            return None
            
    except Exception as e:
        print(f"Error: {e}")
        return None

def convert_with_weasyprint_fallback(url):
    """Fallback using WeasyPrint"""
    try:
        from weasyprint import HTML
        
        print("Using WeasyPrint fallback...")
        response = requests.get(url, timeout=30)
        html_content = response.text
        
        # Add some basic CSS for better formatting
        enhanced_css = """
        <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        table { border-collapse: collapse; width: 100%; margin: 10px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .header { text-align: center; margin-bottom: 20px; }
        .invoice-details { margin: 20px 0; }
        </style>
        """
        
        if '</head>' in html_content:
            html_content = html_content.replace('</head>', enhanced_css + '</head>')
        else:
            html_content = enhanced_css + html_content
        
        html_doc = HTML(string=html_content, base_url=url)
        pdf_bytes = html_doc.write_pdf()
        
        print(f"WeasyPrint generated PDF ({len(pdf_bytes)} bytes)")
        return pdf_bytes
        
    except ImportError:
        print("WeasyPrint not available")
        return None
    except Exception as e:
        print(f"WeasyPrint error: {e}")
        return None

def convert_url_to_pdf(url, wait_time=20):
    """Main conversion function - try wkhtmltopdf first, fallback to WeasyPrint"""
    
    # Try wkhtmltopdf first (handles JavaScript)
    if check_wkhtmltopdf():
        print("wkhtmltopdf is available, using it...")
        pdf_bytes = convert_with_wkhtmltopdf_preload(url, wait_time)
        if pdf_bytes:
            return pdf_bytes
        else:
            print("wkhtmltopdf failed, trying WeasyPrint...")
    else:
        print("wkhtmltopdf not available, trying to install...")
        if force_install_wkhtmltopdf():
            print("wkhtmltopdf installed successfully, trying conversion...")
            pdf_bytes = convert_with_wkhtmltopdf_preload(url, wait_time)
            if pdf_bytes:
                return pdf_bytes
        
        print("wkhtmltopdf unavailable, using WeasyPrint...")
    
    # Fallback to WeasyPrint
    return convert_with_weasyprint_fallback(url)

@app.route("/convert-to-pdf-base64", methods=["POST"])
def convert_to_pdf_base64():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON required', 'success': False}), 400
            
        url = data.get('url')
        wait_time = int(data.get('wait_time', 20))  # Increased default

        if not url:
            return jsonify({'error': 'URL required', 'success': False}), 400

        print(f"Converting: {url} (wait: {wait_time}s)")
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
    wkhtmltopdf_path = shutil.which('wkhtmltopdf')
    
    try:
        from weasyprint import HTML
        weasyprint_available = True
    except ImportError:
        weasyprint_available = False
    
    return jsonify({
        "status": "healthy",
        "wkhtmltopdf_available": wkhtmltopdf_available,
        "wkhtmltopdf_path": wkhtmltopdf_path,
        "weasyprint_available": weasyprint_available,
        "service": "Kairali PDF API (Enhanced)"
    })

@app.route("/force-install", methods=["POST"])
def force_install():
    """Endpoint to manually trigger wkhtmltopdf installation"""
    try:
        success = force_install_wkhtmltopdf()
        return jsonify({
            "installation_success": success,
            "wkhtmltopdf_available": check_wkhtmltopdf(),
            "wkhtmltopdf_path": shutil.which('wkhtmltopdf')
        })
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Kairali Invoice PDF API (Enhanced)",
        "status": "running",
        "platform": "Render.com",
        "endpoints": {
            "/health": "GET - System status",
            "/force-install": "POST - Force install wkhtmltopdf",
            "/convert-to-pdf-base64": "POST - Convert URL to PDF"
        }
    })

# Try to install wkhtmltopdf at startup
if not check_wkhtmltopdf():
    print("wkhtmltopdf not found at startup, attempting installation...")
    force_install_wkhtmltopdf()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
