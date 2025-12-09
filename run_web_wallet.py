#!/usr/bin/env python3

import os
import sys
import argparse
import socket

# Add the project directory to the path so we can import the qrl module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qrl.web_wallet import app


def _is_port_free(port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind(("0.0.0.0", port))
    except OSError:
        return False
    finally:
        try:
            s.close()
        except Exception:
            pass
    return True

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run QRL Web Wallet")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "5001")), help="Port to bind (default: 5001 or $PORT)")
    args = parser.parse_args()

    port = int(args.port)
    if not _is_port_free(port):
        base = port
        for candidate in range(base + 1, base + 21):
            if _is_port_free(candidate):
                print(f"Port {base} in use, switching to available port {candidate}")
                port = candidate
                break
        else:
            print(f"No free port found in range {base+1}-{base+20}. Set PORT or use --port to specify a free port.")
            sys.exit(1)

    print(f"Starting QRL Web Wallet on http://localhost:{port}")
    print("Press Ctrl+C to stop the server")
    
    # Explicitly set up the app context
    with app.app_context():
        try:
            # Enable debug mode for better error messages
            app.debug = True
            # Run the app with explicit host and port
            app.run(host='0.0.0.0', port=port, use_reloader=False, threaded=True)
        except Exception as e:
            print(f"Error starting server: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)