# app_chrome.py
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.utils import ChromeType
import base64
import tempfile
import os
import time
import shutil
import subprocess
import re

app = Flask(__name__)

def find_chrome_binary():
    # try common names
    candidates = [
        "chromium",
        "chromium-browser",
        "google-chrome",
        "google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome"
    ]
    for c in candidates:
        path = shutil.which(c)
        if path:
            return path
        # also check literal path
        if os.path.exists(c) and os.access(c, os.X_OK):
            return c
    return None

def convert_url_to_pdf_chrome(url, wait_time=25):
    """Convert URL to PDF using Selenium + Chromium installed by Nixpacks."""
    pdf_bytes = None
    chrome_binary = find_chrome_binary()
    print("Detected chrome binary:", chrome_binary)

    options = webdriver.ChromeOptions()
    # headless for modern Chrome:
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--hide-scrollbars")
    options.add_argument("--disable-web-security")
    options.add_argument("--single-process")
    # optional: reduce resource usage
    options.add_argument("--disable-extensions")

    if chrome_binary:
        options.binary_location = chrome_binary

    try:
        # get chromedriver built for Chromium
        driver_path = ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()
        service = Service(driver_path)

        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(60)
        driver.get(url)

        # let JS / XHRs finish
        time.sleep(wait_time)

        # Use Chrome DevTools Protocol to print to PDF
        print_options = {
            "landscape": False,
            "displayHeaderFooter": False,
            "printBackground": True,
            "preferCSSPageSize": True,
            # "paperWidth": 8.27, "paperHeight": 11.69  # A4 in inches (optional)
        }
        result = driver.execute_cdp_cmd("Page.printToPDF", print_options)
        driver.quit()

        pdf_bytes = base64.b64decode(result["data"])
        return pdf_bytes

    except Exception as e:
        print("Error generating PDF:", e)
        try:
            driver.quit()
        except:
            pass
        return None


@app.route("/convert", methods=["POST"])
def convert():
    data = request.json or {}
    url = data.get("url")
    wait_time = int(data.get("wait_time", 25))

    if not url:
        return jsonify({"error": "url required"}), 400

    pdf_bytes = convert_url_to_pdf_chrome(url, wait_time)

    if pdf_bytes:
        encoded = base64.b64encode(pdf_bytes).decode("utf-8")
        return jsonify({"pdf_base64": encoded})
    else:
        return jsonify({"error": "Failed to generate PDF"}), 500


if __name__ == "__main__":
    # port 8080 so Railway / containers pick it up
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
