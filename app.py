import os
import logging
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from services.ocr_processor import OCRProcessor

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Enable CORS for mobile app compatibility
CORS(app, origins=["*"])

# Initialize OCR processor
ocr_processor = OCRProcessor()

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
            'details': str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'OCR Processing API is running'
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
