import json
import socket
import threading
import secrets
from pathlib import Path

class IpcServer:
    def __init__(self, endpoint_path: str | Path):
        self.endpoint_path = Path(endpoint_path)
        self.token = secrets.token_hex(16)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(("127.0.0.1", 0))
        self.host, self.port = self.sock.getsockname()
        self.running = False
        self.thread = None

    def start(self):
        self.sock.listen(5)
        self.running = True
        
        # Write endpoint info
        ep_data = {
            "host": self.host,
            "port": self.port,
            "token": self.token
        }
        self.endpoint_path.parent.mkdir(parents=True, exist_ok=True)
        self.endpoint_path.write_text(json.dumps(ep_data))
        
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _loop(self):
        while self.running:
            try:
                self.sock.settimeout(1.0)
                conn, _ = self.sock.accept()
                threading.Thread(target=self._handle, args=(conn,), daemon=True).start()
            except socket.timeout:
                continue
            except Exception:
                if self.running:
                    pass

    def _handle(self, conn: socket.socket):
        try:
            buf = b""
            while self.running:
                chunk = conn.recv(65536)
                if not chunk:
                    break
                buf += chunk
                if b"\n" in buf:
                    lines = buf.split(b"\n")
                    for line in lines[:-1]:
                        if not line: continue
                        req = json.loads(line.decode("utf-8"))
                        if req.get("token") != self.token:
                            resp = {"error": "Invalid token"}
                        else:
                            resp = {"result": "ok", "id": req.get("id")}
                        conn.sendall(json.dumps(resp).encode("utf-8") + b"\n")
                    buf = lines[-1]
        finally:
            conn.close()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        self.sock.close()
        if self.endpoint_path.exists():
            self.endpoint_path.unlink()
