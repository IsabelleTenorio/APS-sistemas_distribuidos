"""
admin/client.py
Gerencia a comunicação TCP com o servidor central no papel de admin.
Cada comando abre sua própria conexão — sem estado compartilhado entre operações.
"""

import socket
import json
from contextlib import contextmanager

BUFFER_SIZE = 8192


class AdminClient:
    """
    Cliente TCP para o servidor de administração.
    Cada método de comando abre uma conexão, executa e fecha.
    O modo WATCH mantém a conexão aberta enquanto o gerador estiver ativo.
    """

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

    # ── Comandos do protocolo ─────────────────────────────────────────────

    def status(self, service_id: str | None = None) -> dict:
        cmd = f"STATUS|{service_id}" if service_id else "STATUS"
        return self._one_shot(cmd)

    def summary(self) -> dict:
        return self._one_shot("SUMMARY")

    def history(self, service_id: str, last_n: int = 20) -> dict:
        return self._one_shot(f"HISTORY|{service_id}|{last_n}")

    def list_services(self) -> dict:
        return self._one_shot("LIST")

    def ping(self) -> dict:
        return self._one_shot("PING")

    def watch(self, interval: int = 5):
        """
        Gerador que emite updates do servidor enquanto a conexão estiver aberta.
        A conexão é fechada quando o gerador for abandonado (close() ou garbage collect).
        """
        with self._connection() as (sock, buf):
            _send_raw(sock, f"WATCH|{interval}")
            _recv_line(sock, buf)   # ACK inicial
            while True:
                yield _recv_line(sock, buf)

    # ── Conexão inicial (usado pelo main.py para verificar conectividade) ─

    def connect(self) -> dict:
        """Testa a conectividade e retorna a mensagem de boas-vindas."""
        return self._one_shot("PING")

    def close(self) -> None:
        pass   # sem estado persistente para fechar

    # ── Internos ──────────────────────────────────────────────────────────

    def _one_shot(self, cmd: str) -> dict:
        """Abre conexão, envia um comando, lê resposta e fecha."""
        with self._connection() as (sock, buf):
            _send_raw(sock, cmd)
            return _recv_line(sock, buf)

    @contextmanager
    def _connection(self):
        """Abre conexão TCP, faz handshake admin, cede (sock, buf), fecha ao sair."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        buf  = [""]
        try:
            sock.connect((self.host, self.port))
            _send_json(sock, {"role": "admin"})
            _recv_line(sock, buf)   # descarta boas-vindas
            yield sock, buf
        finally:
            try:
                sock.close()
            except OSError:
                pass


# ── Funções de protocolo (módulo-privadas) ────────────────────────────────────

def _send_json(sock: socket.socket, obj: dict) -> None:
    sock.sendall((json.dumps(obj, ensure_ascii=False) + "\n").encode())


def _send_raw(sock: socket.socket, text: str) -> None:
    sock.sendall((text.strip() + "\n").encode())


def _recv_line(sock: socket.socket, buf: list[str]) -> dict:
    while "\n" not in buf[0]:
        chunk = sock.recv(BUFFER_SIZE)
        if not chunk:
            raise ConnectionError("Servidor desconectado.")
        buf[0] += chunk.decode("utf-8", errors="replace")
    line, buf[0] = buf[0].split("\n", 1)
    return json.loads(line.strip())