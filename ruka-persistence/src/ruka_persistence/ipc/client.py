import json
import time
import socket
from pathlib import Path

def encode_message(msg: dict) -> bytes:
    return json.dumps(msg, separators=(',', ':')).encode('utf-8') + b'\n'

def decode_message(msg: bytes) -> dict:
    return json.loads(msg.decode('utf-8').strip())

def make_request(seq: int, method: str, params: dict | None, token: str) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": seq,
        "method": method,
        "params": params or {},
        "token": token
    }

class IpcClient:
    """Klien dengan reconnect ber-backoff — untuk uji dan untuk
    penggunaan Electron-side (konsep sama di JS)."""
    def __init__(self, endpoint_path: str | Path,
                 max_retries: int = 5, base_delay: float = 0.2):
        self.endpoint_path = Path(endpoint_path)
        self.max_retries = max_retries
        self.base_delay = base_delay
        self._sock: socket.socket | None = None
        self._seq = 0
        self._endpoint: dict | None = None

    def _read_endpoint(self) -> dict:
        data = json.loads(self.endpoint_path.read_text(encoding="utf-8"))
        self._endpoint = data
        return data

    def connect(self) -> None:
        ep = self._read_endpoint()
        last_exc: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                s = socket.create_connection((ep["host"], ep["port"]),
                                             timeout=2.0)
                self._sock = s
                return
            except OSError as exc:
                last_exc = exc
                time.sleep(min(self.base_delay * (2 ** attempt), 5.0))
        raise ConnectionError(
            f"tidak bisa terhubung setelah {self.max_retries} "
            f"percobaan: {last_exc}")

    def call(self, method: str, params: dict | None = None) -> dict:
        if self._sock is None:
            self.connect()
        self._seq += 1
        ep = self._endpoint or self._read_endpoint()
        req = make_request(self._seq, method, params, ep["token"])
        self._sock.sendall(encode_message(req))
        buf = b""
        while b"\n" not in buf:
            chunk = self._sock.recv(65536)
            if not chunk:
                raise ConnectionError("server menutup koneksi")
            buf += chunk
        return decode_message(buf)

    def close(self) -> None:
        if self._sock:
            self._sock.close()
            self._sock = None
