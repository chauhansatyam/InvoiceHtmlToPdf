


    

    # app_chrome.py - Uses system Chrome instead of Playwright
from flask import Flask, request, jsonify
import subprocess
import base64
import tempfile
import os
from datetime import datetime
import time

app = Flask(__name__)

def create_clean_html_for_pdf(url, wait_time=25):
    """Create a clean HTML version without print headers"""
    try:
        import requests
        # Fetch the original HTML
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        html_content = response.text
        
        # CSS to hide print headers and style for clean PDF
        clean_css = """
        <style>
        @media print {
            @page {
                margin: 0.5in;
                size: A4;
                /* Remove default headers/footers */
                @top-left { content: ""; }
                @top-center { content: ""; }
                @top-right { content: ""; }
                @bottom-left { content: ""; }
                @bottom-center { content: ""; }
                @bottom-right { content: ""; }
            }
            
            body {
                margin: 0;
                padding: 20px;
                font-family: Arial, sans-serif;
            }
            
            /* Ensure content fits properly */
            .container, .invoice-container, .main-content {
                width: 100% !important;
                max-width: none !important;
                margin: 0 !important;
            }
        }
        
        @page :first {
            margin-top: 0.5in;
        }
        </style>
        """
        
        # Insert CSS before closing head tag or at the beginning
        if '</head>' in html_content:
            html_content = html_content.replace('</head>', clean_css + '\n</head>')
        elif '<head>' in html_content:
            html_content = html_content.replace('<head>', '<head>\n' + clean_css)
        else:
            # If no head tag, add at the beginning
            html_content = clean_css + '\n' + html_content
        
        return html_content
        
    except Exception as e:
        print(f"Error fetching HTML: {e}")
        return None

def convert_url_to_pdf_chrome_clean(url, wait_time=25):
    """Convert URL to PDF with clean formatting"""
    
    # Get clean HTML content
    html_content = create_clean_html_for_pdf(url, wait_time)
    
    if not html_content:
        # Fallback to original method
        return convert_url_to_pdf_chrome(url, wait_time)
    
    # Create temporary HTML file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as tmp_html:
        tmp_html.write(html_content)
        html_path = tmp_html.name
    
    # Create temporary PDF file
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_pdf:
        pdf_path = tmp_pdf.name
    
    try:
        print(f"Converting clean HTML to PDF...")
        
        # Chrome command for local HTML file
        chrome_cmd = [
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            '--headless',
            '--disable-gpu',
            '--no-sandbox',
            '--disable-dev-shm-usage',
            f'--virtual-time-budget={wait_time * 1000}',
            f'--print-to-pdf={pdf_path}',
            '--hide-scrollbars',
            f'file://{html_path}'
        ]
        
        result = subprocess.run(chrome_cmd, capture_output=True, text=True, timeout=40)
        
        if result.returncode != 0:
            print(f"Chrome error: {result.stderr}")
            return None
        
        time.sleep(2)
        
        if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
            with open(pdf_path, 'rb') as pdf_file:
                pdf_bytes = pdf_file.read()
            print(f"Clean PDF generated ({len(pdf_bytes)} bytes)")
            return pdf_bytes
        else:
            return None
            
    except subprocess.TimeoutExpired:
        print("Chrome command timed out")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        # Clean up temp files
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)
        if os.path.exists(html_path):
            os.unlink(html_path)

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
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '--headless',
    '--disable-gpu',
    '--no-sandbox',
    '--disable-dev-shm-usage',
    f'--virtual-time-budget={wait_time * 1000}',
    '--run-all-compositor-stages-before-draw',
    '--disable-background-timer-throttling',
    '--disable-backgrounding-occluded-windows',
    '--disable-renderer-backgrounding',
    f'--print-to-pdf={pdf_path}',
    # Add these lines to remove headers/footers:
    '--disable-print-preview',
    '--kiosk-printing', 
    '--disable-default-apps',
    '--disable-extensions',
    '--no-first-run',
    '--disable-web-security',
    '--user-data-dir=/tmp/chrome_user_data',  # Use temporary user data
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
        pdf_bytes = convert_url_to_pdf_chrome_clean(url, wait_time)
        
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