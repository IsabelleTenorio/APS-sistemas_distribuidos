"""
admin/client.py
Gerencia a conexão TCP com o servidor central no papel de admin.
Não sabe nada de cores, menus ou renderização — só protocolo.
"""

import socket
import json

BUFFER_SIZE = 8192


class AdminClient:
    """
    Conexão TCP persistente com o servidor no papel de admin.
    Expõe métodos de alto nível que mapeiam 1-para-1 com os
    comandos do protocolo (STATUS, SUMMARY, HISTORY, LIST, WATCH, PING).
    """

    def __init__(self, host: str, port: int):
        self.host  = host
        self.port  = port
        self._sock: socket.socket | None = None
        self._buf  = ""

    # ── Ciclo de vida ─────────────────────────────────────────────────────

    def connect(self) -> dict:
        """Abre conexão e faz handshake com role=admin. Retorna mensagem de boas-vindas."""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.connect((self.host, self.port))
        self._buf = ""
        self._send_json({"role": "admin"})
        return self._recv_line()

    def close(self) -> None:
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    # ── Comandos do protocolo ─────────────────────────────────────────────

    def status(self, service_id: str | None = None) -> dict:
        cmd = f"STATUS|{service_id}" if service_id else "STATUS"
        return self._cmd(cmd)

    def summary(self) -> dict:
        return self._cmd("SUMMARY")

    def history(self, service_id: str, last_n: int = 20) -> dict:
        return self._cmd(f"HISTORY|{service_id}|{last_n}")

    def list_services(self) -> dict:
        return self._cmd("LIST")

    def ping(self) -> dict:
        return self._cmd("PING")

    def watch(self, interval: int = 5):
        """
        Gerador que emite updates do servidor indefinidamente.
        Levanta StopIteration (ou a conexão cai) quando encerrado.
        """
        self._cmd(f"WATCH|{interval}")   # ACK do servidor
        while True:
            yield self._recv_line()

    # ── Protocolo interno ─────────────────────────────────────────────────

    def _cmd(self, raw: str) -> dict:
        self._send_raw(raw)
        return self._recv_line()

    def _send_json(self, obj: dict) -> None:
        self._sock.sendall((json.dumps(obj, ensure_ascii=False) + "\n").encode())

    def _send_raw(self, text: str) -> None:
        self._sock.sendall((text.strip() + "\n").encode())

    def _recv_line(self) -> dict:
        while "\n" not in self._buf:
            chunk = self._sock.recv(BUFFER_SIZE)
            if not chunk:
                raise ConnectionError("Servidor desconectado.")
            self._buf += chunk.decode("utf-8", errors="replace")
        line, self._buf = self._buf.split("\n", 1)
        return json.loads(line.strip())