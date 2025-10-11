#!/usr/bin/env python3

import os
import sys

# Add the project directory to the path so we can import the qrl module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qrl.web_wallet import app

if __name__ == '__main__':
    port = 5001
    print(f"Starting QRL Web Wallet on http://localhost:{port}")
    print("Press Ctrl+C to stop the server")
    app.run(debug=True, host='0.0.0.0', port=port)