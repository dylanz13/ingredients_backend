import os
import logging
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from services.ocr_processor import OCRProcessor
import signal
import sys

# Configure logging for production
if os.environ.get('FLASK_ENV') == 'production':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s %(message)s'
    )
else:
    logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Enable CORS for mobile app compatibility
CORS(app, origins=["*"])

# Initialize OCR processor
ocr_processor = OCRProcessor()

# Graceful shutdown handler
def signal_handler(sig, frame):
    logger.info('Gracefully shutting down...')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

@app.route('/')
def index():
    """Serve the documentation and testing interface"""
    return render_template('index.html')

@app.route('/api/process-ocr', methods=['POST'])
def process_ocr():
    """
    Process OCR text containing dish names and partial ingredients
    Returns structured ingredient lists
    """
    try:
        # Validate request
        if not request.is_json:
            return jsonify({
                'error': 'Content-Type must be application/json'
            }), 400
        
        data = request.get_json()
        
        # Validate required fields
        if 'ocr_text' not in data:
            return jsonify({
                'error': 'Missing required field: ocr_text'
            }), 400
        
        ocr_text = data['ocr_text'].strip()
        if not ocr_text:
            return jsonify({
                'error': 'ocr_text cannot be empty'
            }), 400
        
        logger.info(f"Processing OCR text: {ocr_text[:100]}...")
        
        # Process the OCR text
        result = ocr_processor.process_ocr_text(ocr_text)
        
        logger.info(f"Successfully processed OCR text, found {len(result.get('dishes', []))} dishes")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error processing OCR text: {str(e)}")
        return jsonify({
            'error': 'Internal server error occurred while processing OCR text',
            'details': str(e) if app.debug else None
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'OCR Processing API is running',
        'environment': os.environ.get('FLASK_ENV', 'development')
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Only run Flask dev server in development
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    
    if debug:
        logger.warning("Running in development mode")
        app.run(host='0.0.0.0', port=port, debug=True)
    else:
        logger.info("Use 'gunicorn wsgi:app' for production")
