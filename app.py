# app.py - Simplified Railway version without ChromeDriverManager
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import base64
import os
import time
import shutil
import subprocess
import requests
import zipfile
from datetime import datetime

app = Flask(__name__)

def find_chrome_binary():
    """Find Chrome binary in Railway environment."""
    candidates = [
        "/root/.nix-profile/bin/chromium",
        "/usr/bin/chromium",
        "/usr/bin/google-chrome",
        "chromium"
    ]
    for c in candidates:
        if os.path.exists(c) and os.access(c, os.X_OK):
            print(f"Found Chrome binary: {c}")
            return c
    print("No Chrome binary found")
    return None

def download_chromedriver():
    """Download ChromeDriver directly"""
    try:
        chromedriver_dir = "/tmp/chromedriver"
        chromedriver_path = f"{chromedriver_dir}/chromedriver"
        
        # Check if already downloaded
        if os.path.exists(chromedriver_path) and os.access(chromedriver_path, os.X_OK):
            print(f"Using existing ChromeDriver: {chromedriver_path}")
            return chromedriver_path
        
        print("Downloading ChromeDriver...")
        os.makedirs(chromedriver_dir, exist_ok=True)
        
        # Download a stable version that works with most Chrome versions
        url = "https://chromedriver.storage.googleapis.com/119.0.6045.105/chromedriver_linux64.zip"
        
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        zip_path = f"{chromedriver_dir}/chromedriver.zip"
        with open(zip_path, 'wb') as f:
            f.write(response.content)
        
        # Extract
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(chromedriver_dir)
        
        # Make executable
        os.chmod(chromedriver_path, 0o755)
        
        print(f"ChromeDriver downloaded to: {chromedriver_path}")
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
        
        # Get ChromeDriver
        chromedriver_path = download_chromedriver()
        if not chromedriver_path:
            raise Exception("ChromeDriver not available")
        
        print(f"Converting URL: {url}")
        print(f"Chrome: {chrome_binary}")
        print(f"ChromeDriver: {chromedriver_path}")

        # Chrome options
        options = webdriver.ChromeOptions()
        options.binary_location = chrome_binary
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--single-process")
        options.add_argument("--disable-extensions")
        options.add_argument("--hide-scrollbars")
        options.add_argument("--disable-web-security")

        service = Service(chromedriver_path)
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(60)
        
        print("Loading page...")
        driver.get(url)
        
        print(f"Waiting {wait_time} seconds...")
        time.sleep(wait_time)
        
        # Generate PDF
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
    return jsonify({
        "status": "healthy",
        "chrome_binary": chrome_binary,
        "service": "Kairali PDF API"
    })

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Kairali Invoice PDF API",
        "status": "running",
        "endpoints": {"/health": "GET", "/convert-to-pdf-base64": "POST"}
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
