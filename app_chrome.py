# app_chrome.py - Uses system Chrome instead of Playwright
from flask import Flask, request, jsonify
import subprocess
import base64
import tempfile
import os
from datetime import datetime
import time

app = Flask(__name__)

def convert_url_to_pdf_chrome(url, wait_time=25):
    """Convert URL to PDF using system Chrome"""
    
    # Create temporary file for PDF
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
        pdf_path = tmp_file.name
    
    try:
        print(f"Converting: {url}")
        print(f"Wait time: {wait_time} seconds")
        
        # Chrome command with PDF generation
        # chrome_cmd = [
        #     '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        #     '--headless',
        #     '--disable-gpu',
        #     '--no-sandbox',
        #     '--disable-dev-shm-usage',
        #     '--virtual-time-budget=25000',  # Wait 25 seconds for JS
        #     '--run-all-compositor-stages-before-draw',
        #     '--disable-background-timer-throttling',
        #     '--disable-backgrounding-occluded-windows',
        #     '--disable-renderer-backgrounding',
        #     f'--print-to-pdf={pdf_path}',
        #     '--print-to-pdf-no-header',
        #     '--hide-scrollbars',
        #     url
        # ]
        chrome_cmd = [
    '/app/.chrome-for-testing/chrome-linux64/chrome',
    '--headless',
    '--disable-gpu',
    '--no-sandbox',
    '--disable-dev-shm-usage',
    f'--virtual-time-budget={wait_time * 1000}',
    f'--print-to-pdf={pdf_path}',
    '--hide-scrollbars',
    '--disable-web-security',
    '--single-process',  # Important for Heroku
    '--disable-dev-shm-usage',
    '--remote-debugging-port=0',
    url
]
        
        print("Running Chrome to generate PDF...")
        result = subprocess.run(chrome_cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            print(f"Chrome error: {result.stderr}")
            return None
            
        # Wait for file to be written
        time.sleep(2)
        
        if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
            with open(pdf_path, 'rb') as pdf_file:
                pdf_bytes = pdf_file.read()
            print(f"PDF generated ({len(pdf_bytes)} bytes)")
            return pdf_bytes
        else:
            print("PDF file not created or empty")
            return None
            
    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        # Clean up temp file
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)

@app.route('/convert-to-pdf-base64', methods=['POST'])
def convert_to_pdf_base64():
    """Convert HTML URL to PDF and return as base64"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'JSON body required', 'success': False}), 400
            
        url = data.get('url')
        wait_time = data.get('wait_time', 25)
        
        if not url:
            return jsonify({'error': 'URL parameter is required', 'success': False}), 400
        
        print(f"Starting conversion: {url}")
        
        # Generate PDF
        pdf_bytes = convert_url_to_pdf_chrome(url, wait_time)
        
        if not pdf_bytes:
            return jsonify({'error': 'Failed to generate PDF', 'success': False}), 500
        
        # Convert to base64
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"kairali_invoice_{timestamp}.pdf"
        
        return jsonify({
            'success': True,
            'pdf_base64': pdf_base64,
            'filename': filename,
            'size_bytes': len(pdf_bytes)
        })
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'Kairali PDF API (Chrome)'
    })

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'message': 'Kairali Invoice PDF API (System Chrome)',
        'endpoints': {
            '/health': 'GET - Health check',
            '/convert-to-pdf-base64': 'POST - Convert URL to PDF (base64)'
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=True, host='0.0.0.0', port=port)

