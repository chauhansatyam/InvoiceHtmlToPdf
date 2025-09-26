# app.py - Railway-compatible version
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import base64
import os
import time
import shutil
import subprocess
from datetime import datetime

app = Flask(__name__)

def get_chrome_version(chrome_path):
    """Get Chrome version from binary"""
    try:
        result = subprocess.run([chrome_path, '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version = result.stdout.strip().split()[-1]
            return version
        return None
    except:
        return None

def find_chrome_binary():
    """Locate Chromium/Chrome binary in Railway's environment."""
    candidates = [
        "/root/.nix-profile/bin/chromium",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser", 
        "/usr/bin/google-chrome",
        "chromium",
        "google-chrome"
    ]
    for c in candidates:
        if os.path.exists(c) and os.access(c, os.X_OK):
            print(f"Found Chrome binary: {c}")
            return c
        path = shutil.which(c)
        if path:
            print(f"Found Chrome binary: {path}")
            return path
    print("No Chrome binary found")
    return None

def setup_chromedriver():
    """Setup ChromeDriver for Railway environment"""
    try:
        # First try to use system chromedriver if available
        chromedriver_path = shutil.which('chromedriver')
        if chromedriver_path:
            print(f"Using system ChromeDriver: {chromedriver_path}")
            return chromedriver_path
        
        # Try manual ChromeDriverManager with specific version
        from webdriver_manager.chrome import ChromeDriverManager
        try:
            # Try with latest version
            driver_path = ChromeDriverManager(version="latest").install()
            print(f"ChromeDriverManager installed at: {driver_path}")
            return driver_path
        except Exception as e:
            print(f"ChromeDriverManager failed: {e}")
            
            # Try with a specific stable version
            try:
                driver_path = ChromeDriverManager(version="119.0.6045.105").install()
                print(f"ChromeDriverManager with specific version: {driver_path}")
                return driver_path
            except Exception as e2:
                print(f"ChromeDriverManager with specific version failed: {e2}")
        
        raise Exception("No ChromeDriver could be set up")
        
    except Exception as e:
        print(f"ChromeDriver setup failed: {e}")
        return None

def convert_url_to_pdf_chrome(url, wait_time=25):
    """Convert a URL to PDF using Selenium + Chrome."""
    pdf_bytes = None
    driver = None
    
    try:
        chrome_binary = find_chrome_binary()
        if not chrome_binary:
            raise Exception("Chrome binary not found")
            
        print(f"Converting URL: {url}")
        print(f"Wait time: {wait_time} seconds")
        print(f"Chrome binary: {chrome_binary}")
        
        # Get Chrome version
        chrome_version = get_chrome_version(chrome_binary)
        print(f"Chrome version: {chrome_version}")

        # Chrome options optimized for Railway
        options = webdriver.ChromeOptions()
        options.binary_location = chrome_binary
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--hide-scrollbars")
        options.add_argument("--disable-web-security")
        options.add_argument("--single-process")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-renderer-backgrounding")
        options.add_argument("--disable-features=VizDisplayCompositor")
        options.add_argument("--disable-ipc-flooding-protection")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-background-networking")

        # Setup ChromeDriver
        driver_path = setup_chromedriver()
        if not driver_path:
            raise Exception("ChromeDriver setup failed")

        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(60)
        
        print("Loading page...")
        driver.get(url)
        
        print(f"Waiting {wait_time} seconds for dynamic content...")
        time.sleep(wait_time)
        
        # Check if page loaded
        page_title = driver.title
        page_source_length = len(driver.page_source)
        print(f"Page title: {page_title}")
        print(f"Page source length: {page_source_length}")

        # Use Chrome DevTools Protocol to generate PDF
        print("Generating PDF...")
        print_options = {
            "landscape": False,
            "displayHeaderFooter": False,
            "printBackground": True,
            "preferCSSPageSize": True,
            "format": "A4",
            "margin": {
                "top": 0.4,
                "bottom": 0.4,
                "left": 0.4,
                "right": 0.4
            }
        }
        
        result = driver.execute_cdp_cmd("Page.printToPDF", print_options)
        pdf_bytes = base64.b64decode(result["data"])
        
        print(f"PDF generated successfully ({len(pdf_bytes)} bytes)")
        return pdf_bytes

    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
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
    """Convert HTML URL to PDF and return as base64"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'JSON body required', 'success': False}), 400
            
        url = data.get('url')
        wait_time = int(data.get('wait_time', 25))

        if not url:
            return jsonify({'error': 'URL parameter is required', 'success': False}), 400

        print(f"Starting conversion: {url}")
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
            return jsonify({'error': 'Failed to generate PDF', 'success': False}), 500

    except Exception as e:
        print(f"Error in convert endpoint: {str(e)}")
        return jsonify({'error': str(e), 'success': False}), 500

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    chrome_binary = find_chrome_binary()
    chrome_version = get_chrome_version(chrome_binary) if chrome_binary else None
    chromedriver_path = setup_chromedriver()
    
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "chrome_binary": chrome_binary,
        "chrome_version": chrome_version,
        "chromedriver_path": chromedriver_path,
        "service": "Kairali PDF API"
    })

@app.route("/", methods=["GET"])
def home():
    """Home endpoint"""
    return jsonify({
        "message": "Kairali Invoice PDF API",
        "status": "running",
        "endpoints": {
            "/health": "GET - Health check",
            "/convert-to-pdf-base64": "POST - Convert URL to PDF"
        }
    })

@app.route("/debug", methods=["GET"])
def debug():
    """Debug Chrome and ChromeDriver setup"""
    chrome_binary = find_chrome_binary()
    chrome_version = get_chrome_version(chrome_binary) if chrome_binary else None
    chromedriver_path = setup_chromedriver()
    
    debug_info = {
        "chrome_binary": chrome_binary,
        "chrome_version": chrome_version,
        "chromedriver_path": chromedriver_path,
        "environment": {
            "PATH": os.environ.get("PATH", ""),
            "PWD": os.getcwd()
        }
    }
    
    return jsonify(debug_info)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)