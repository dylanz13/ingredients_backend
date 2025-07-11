from app import app  # noqa: F401
import os

if __name__ == '__main__':
    # Only for development - production uses Gunicorn
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)  # Set debug=False for production
