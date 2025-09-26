# app_chrome.py - Uses Selenium + webdriver_manager instead of system Chrome
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import base64
import tempfile
import os
from datetime import datetime
import time

app = Flask(__name__)

def convert_url_to_pdf_chrome(url, wait_time=25):
    """Convert URL to PDF using Selenium Chrome"""

    # Create temporary file for PDF
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
        pdf_path = tmp_file.name

    try:
        print(f"Converting: {url}")
        print(f"Wait time: {wait_time} seconds")

        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")  # new headless mode
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--hide-scrollbars")
        options.add_argument("--disable-web-security")
        options.add_argument("--single-process")
        options.add_argument(f"--virtual-time-budget={wait_time * 1000}")

        # Start Chrome with webdriver_manager
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        driver.get(url)
        time.sleep(wait_time)

        # Save page as PDF
        pdf = driver.print_page()
        driver.quit()

        # Write PDF bytes
        with open(pdf_path, "wb") as f:
            f.write(base64.b64decode(pdf))

        return pdf_path

    except Exception as e:
        print("Error generating PDF:", e)
        return None


@app.route("/convert", methods=["POST"])
def convert():
    data = request.json
    url = data.get("url")
    wait_time = data.get("wait_time", 25)

    pdf_path = convert_url_to_pdf_chrome(url, wait_time)

    if pdf_path and os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        os.remove(pdf_path)
        return jsonify({"pdf_base64": base64.b64encode(pdf_bytes).decode("utf-8")})
    else:
        return jsonify({"error": "Failed to generate PDF"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
