# app.py - Main Flask application
from flask import Flask, request, jsonify, send_file
from playwright.sync_api import sync_playwright
import base64
import io
import os
import time
from datetime import datetime

app = Flask(__name__)

def convert_url_to_pdf_sync(url, wait_time=15):
    """Convert URL to PDF using Playwright"""
    
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-web-security'
            ]
        )
        
        try:
            # Create page
            page = browser.new_page(
                viewport={'width': 1200, 'height': 1600},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            
            print(f"🌐 Loading page: {url}")
            
            # Navigate to page
            page.goto(url, wait_until='networkidle', timeout=30000)
            
            print("⏳ Waiting for dynamic content...")
            
            # Wait for loading text to disappear
            try:
                page.wait_for_function(
                    "() => !document.body.textContent.includes('Loading...')",
                    timeout=wait_time * 1000
                )
                print("✅ Loading text disappeared")
            except:
                print("⚠️ Loading text timeout - continuing...")
            
            # Wait for table with data
            try:
                page.wait_for_selector("table", timeout=10000)
                page.wait_for_function(
                    "() => document.querySelectorAll('table td').length > 5",
                    timeout=wait_time * 1000
                )
                print("✅ Table populated with data")
            except:
                print("⚠️ Table timeout - continuing...")
            
            # Final stabilization wait
            time.sleep(3)
            
            # Check content status
            content_text = page.inner_text('body')
            loading_count = content_text.count('Loading')
            print(f"📊 Content check: {loading_count} 'Loading' instances found")
            
            # Generate PDF
            print("📄 Generating PDF...")
            pdf_bytes = page.pdf(
                format='A4',
                margin={
                    'top': '1cm',
                    'right': '1cm',
                    'bottom': '1cm',
                    'left': '1cm'
                },
                print_background=True,
                prefer_css_page_size=True
            )
            
            print(f"✅ PDF generated ({len(pdf_bytes)} bytes)")
            return pdf_bytes
            
        finally:
            browser.close()

@app.route('/convert-to-pdf-base64', methods=['POST'])
def convert_to_pdf_base64():
    """Convert HTML URL to PDF and return as base64"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'JSON body required', 'success': False}), 400
            
        url = data.get('url')
        wait_time = data.get('wait_time', 15)
        
        if not url:
            return jsonify({'error': 'URL parameter is required', 'success': False}), 400
        
        print(f"🚀 Starting conversion: {url}")
        
        # Generate PDF
        pdf_bytes = convert_url_to_pdf_sync(url, wait_time)
        
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
            'size_bytes': len(pdf_bytes),
            'loading_instances_found': pdf_bytes and True or False
        })
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/debug-content', methods=['POST'])
def debug_content():
    """Debug endpoint to check page content"""
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'URL required'}), 400
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                page.goto(url, wait_until='networkidle')
                time.sleep(8)  # Wait 8 seconds
                
                content_text = page.inner_text('body')
                loading_count = content_text.count('Loading')
                
                return jsonify({
                    'title': page.title(),
                    'loading_instances': loading_count,
                    'has_table': len(page.query_selector_all('table')) > 0,
                    'table_rows': len(page.query_selector_all('table tr')),
                    'content_length': len(content_text),
                    'content_preview': content_text[:300]
                })
                
            finally:
                browser.close()
                
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'Kairali PDF API'
    })

@app.route('/', methods=['GET'])
def home():
    """API documentation"""
    return jsonify({
        'message': 'Kairali Invoice PDF API',
        'version': '1.0',
        'endpoints': {
            '/': 'GET - This documentation',
            '/health': 'GET - Health check',
            '/convert-to-pdf-base64': 'POST - Convert URL to PDF (base64)',
            '/debug-content': 'POST - Debug page content'
        },
        'example_request': {
            'url': 'POST /convert-to-pdf-base64',
            'body': {
                'url': 'https://www.kairali.ai/Google/invoice_ktahv/invoice.html?Id=KTAHV-PMS-6790&bookingType=Individual',
                'wait_time': 20
            }
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=True, host='0.0.0.0', port=port)