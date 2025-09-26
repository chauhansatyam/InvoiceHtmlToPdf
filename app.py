# app.py - Fixed ChromeDriver download URL
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import base64
import os
import time
import requests
import zipfile
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

def download_chromedriver():
    """Download ChromeDriver with working URL"""
    try:
        chromedriver_dir = "/tmp/chromedriver"
        chromedriver_path = f"{chromedriver_dir}/chromedriver"
        
        # Check if already exists
        if os.path.exists(chromedriver_path) and os.access(chromedriver_path, os.X_OK):
            print(f"Using existing ChromeDriver: {chromedriver_path}")
            return chromedriver_path
        
        print("Downloading ChromeDriver...")
        os.makedirs(chromedriver_dir, exist_ok=True)
        
        # Use Chrome for Testing stable version
        url = "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/119.0.6045.105/linux64/chromedriver-linux64.zip"
        
        response = requests.get(url, timeout=30)
        if response.status_code == 404:
            # Fallback to an older stable version
            print("Trying fallback ChromeDriver version...")
            url = "https://chromedriver.storage.googleapis.com/114.0.5735.90/chromedriver_linux64.zip"
            response = requests.get(url, timeout=30)
        
        response.raise_for_status()
        
        zip_path = f"{chromedriver_dir}/chromedriver.zip"
        with open(zip_path, 'wb') as f:
            f.write(response.content)
        
        # Extract
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(chromedriver_dir)
        
        # The new format might have chromedriver in a subfolder
        if not os.path.exists(chromedriver_path):
            # Look for chromedriver in subfolders
            for root, dirs, files in os.walk(chromedriver_dir):
                if 'chromedriver' in files:
                    old_path = os.path.join(root, 'chromedriver')
                    os.rename(old_path, chromedriver_path)
                    break
        
        # Make executable
        os.chmod(chromedriver_path, 0o755)
        
        print(f"ChromeDriver ready at: {chromedriver_path}")
        return chromedriver_path
        
    except Exception as e:
        print(f"ChromeDriver download failed: {e}")
        return None

def convert_url_to_pdf_chrome(url, wait_time=25):
    """Convert URL to PDF using Chrome."""
    driver = None
    
    try:
        chrome_binary = find_chrome_binary()
        if not chrome_binary:
            raise Exception("Chrome binary not found")
        
        chromedriver_path = download_chromedriver()
        if not chromedriver_path:
            raise Exception("ChromeDriver setup failed")
        
        print(f"Converting: {url}")
        print(f"Chrome: {chrome_binary}")
        print(f"ChromeDriver: {chromedriver_path}")

        options = webdriver.ChromeOptions()
        options.binary_location = chrome_binary
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--single-process")
        options.add_argument("--disable-extensions")
        options.add_argument("--hide-scrollbars")

        service = Service(chromedriver_path)
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(60)
        
        print("Loading page...")
        driver.get(url)
        
        print(f"Waiting {wait_time} seconds...")
        time.sleep(wait_time)
        
        print("Generating PDF...")
        result = driver.execute_cdp_cmd("Page.printToPDF", {
            "landscape": False,
            "displayHeaderFooter": False,
            "printBackground": True,
            "format": "A4"
        })
        
        pdf_bytes = base64.b64decode(result["data"])
        print(f"PDF generated ({len(pdf_bytes)} bytes)")
        return pdf_bytes

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

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

        pdf_bytes = convert_url_to_pdf_chrome(url, wait_time)

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
        return jsonify({'error': str(e), 'success': False}), 500

@app.route("/health", methods=["GET"])
def health():
    chrome_binary = find_chrome_binary()
    chromedriver_path = download_chromedriver()
    
    return jsonify({
        "status": "healthy",
        "chrome_binary": chrome_binary,
        "chromedriver_available": bool(chromedriver_path),
        "service": "Kairali PDF API"
    })

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Kairali Invoice PDF API",
        "status": "running"
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
