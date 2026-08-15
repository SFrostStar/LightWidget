import threading
import json
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
from core.storage import StorageManager
from core.parser import parse_message

def get_local_ip():
    """Returns local network IP address of the Mac."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

class StatusRequestHandler(BaseHTTPRequestHandler):
    storage: StorageManager = None
    on_message_callback = None

    def _set_headers(self, content_type='application/json'):
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        path = self.path.split('?')[0]
        if path in ['/', '/api/status', '/status.json']:
            self._set_headers()
            state = StatusRequestHandler.storage.get_state()
            self.wfile.write(json.dumps(state, ensure_ascii=False, indent=2).encode('utf-8'))
        elif path == '/api/health':
            self._set_headers()
            self.wfile.write(json.dumps({"status": "ok", "app": "LightWidget"}, ensure_ascii=False).encode('utf-8'))
        elif path == '/api/history':
            self._set_headers()
            history = StatusRequestHandler.storage.get_history()
            self.wfile.write(json.dumps(history, ensure_ascii=False, indent=2).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path in ['/api/message', '/api/inject']:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(body) if body.startswith('{') else {"text": body}
                msg_text = data.get("text", "")
                parsed = parse_message(msg_text)
                if parsed:
                    StatusRequestHandler.storage.save_state(parsed)
                    StatusRequestHandler.storage.add_history(parsed)
                    if StatusRequestHandler.on_message_callback:
                        StatusRequestHandler.on_message_callback(parsed)
                    self._set_headers()
                    self.wfile.write(json.dumps({"success": True, "state": parsed}, ensure_ascii=False).encode('utf-8'))
                    return
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
                return
        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        # Silence standard HTTP access logging to keep console clean
        return

class ReusableHTTPServer(HTTPServer):
    allow_reuse_address = True

class APIServer:
    def __init__(self, host="0.0.0.0", port=8088, storage=None, on_message=None):
        self.host = host
        self.port = port
        self.storage = storage or StorageManager()
        self.on_message = on_message
        self.server = None
        self.thread = None

    def start(self):
        StatusRequestHandler.storage = self.storage
        StatusRequestHandler.on_message_callback = self.on_message
        try:
            self.server = ReusableHTTPServer((self.host, self.port), StatusRequestHandler)
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            print(f"[API Server] Running at http://{get_local_ip()}:{self.port}/api/status")
        except Exception as e:
            print(f"[API Server] Warning: could not start HTTP server on port {self.port}: {e}")

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
