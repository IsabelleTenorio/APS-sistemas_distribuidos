"""
admin/client.py
Gerencia a comunicação TCP com o servidor central no papel de admin.
Cada comando abre sua própria conexão — sem estado compartilhado entre operações.
"""

import socket
import json

BUFFER_SIZE = 8192


class AdminClient:

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

    # ── Comandos do protocolo ─────────────────────────────────────────────

    def ping(self) -> dict:
        return self._one_shot("PING")

    def status(self, service_id: str | None = None) -> dict:
        cmd = f"STATUS|{service_id}" if service_id else "STATUS"
        return self._one_shot(cmd)

    def summary(self) -> dict:
        return self._one_shot("SUMMARY")

    def history(self, service_id: str, last_n: int = 20) -> dict:
        return self._one_shot(f"HISTORY|{service_id}|{last_n}")

    def list_services(self) -> dict:
        return self._one_shot("LIST")

    def watch(self, interval: int = 5):
        """
        Gerador que emite WATCH_UPDATEs enquanto a conexão estiver aberta.
        A conexão é fechada quando o gerador sair do escopo.
        """
        sock, buf = self._open()
        try:
            sock.sendall((_fmt("WATCH|{}".format(interval))).encode())
            _recv(sock, buf)   # ACK do WATCH
            while True:
                yield _recv(sock, buf)
        finally:
            _close(sock)

    def close(self) -> None:
        pass   # sem estado persistente

    # ── Internos ──────────────────────────────────────────────────────────

    def _one_shot(self, cmd: str) -> dict:
        sock, buf = self._open()
        try:
            sock.sendall(_fmt(cmd).encode())
            return _recv(sock, buf)
        finally:
            _close(sock)

    def _open(self) -> tuple:
        """Abre conexão TCP, faz handshake e descarta boas-vindas. Retorna (sock, buf)."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.host, self.port))
        buf = [""]
        # Handshake: envia role=admin
        sock.sendall((_fmt_json({"role": "admin"})).encode())
        # Descarta boas-vindas do servidor
        _recv(sock, buf)
        return sock, buf


# ── Helpers de protocolo ──────────────────────────────────────────────────────

def _fmt(cmd: str) -> str:
    return json.dumps(cmd.strip()) + "\n"

def _fmt_json(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False) + "\n"

def _recv(sock: socket.socket, buf: list) -> dict:
    while True:
        while "\n" not in buf[0]:
            chunk = sock.recv(BUFFER_SIZE)
            if not chunk:
                raise ConnectionError("Servidor desconectou.")
            buf[0] += chunk.decode("utf-8", errors="replace")
        line, buf[0] = buf[0].split("\n", 1)
        line = line.strip()
        if line:
            return json.loads(line)

def _close(sock: socket.socket) -> None:
    try:
        sock.close()
    except OSError:
        pass