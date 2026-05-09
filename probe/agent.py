"""
probe/agent.py
Gerencia a conexão TCP com o servidor central e o loop de envio de amostras.
Não sabe como coletar métricas — delega para metrics.py.
"""

import socket
import json
import time
import logging
import threading

from .metrics import collect

log = logging.getLogger("probe.agent")

BUFFER_SIZE = 4096


class ProbeAgent:
    """
    Mantém uma conexão TCP persistente com o servidor.
    Reconecta automaticamente se a conexão cair.
    """

    def __init__(
        self,
        service_id:  str,
        name:        str,
        server_host: str,
        server_port: int,
        target_host: str,
        target_port: int,
        interval:    int,
        tags:        list[str],
    ):
        self.service_id  = service_id
        self.name        = name
        self.server_host = server_host
        self.server_port = server_port
        self.target_host = target_host
        self.target_port = target_port
        self.interval    = interval
        self.tags        = tags

        self._sock: socket.socket | None = None
        self._buf  = ""
        self._stop = threading.Event()

    # ── Interface pública ─────────────────────────────────────────────────

    def run(self) -> None:
        """Bloqueia até stop() ser chamado, reconectando quando necessário."""
        log.info(
            "Probe '%s' iniciado → servidor %s:%d | alvo %s:%d | intervalo %ds",
            self.service_id, self.server_host, self.server_port,
            self.target_host, self.target_port, self.interval,
        )
        while not self._stop.is_set():
            try:
                self._connect_and_loop()
            except (ConnectionRefusedError, ConnectionError, OSError) as exc:
                log.warning("Desconectado: %s. Reconectando em 5s...", exc)
                self._close_socket()
                self._stop.wait(5)

    def stop(self) -> None:
        self._stop.set()
        self._close_socket()

    # ── Conexão e loop de envio ───────────────────────────────────────────

    def _connect_and_loop(self) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.connect((self.server_host, self.server_port))
        self._buf = ""

        self._register()

        while not self._stop.is_set():
            sample = collect(self.target_host, self.target_port)
            self._send(sample)
            self._recv_ack()
            self._log_sample(sample)
            self._stop.wait(self.interval)

    def _register(self) -> None:
        hello = {
            "role":       "probe",
            "service_id": self.service_id,
            "name":       self.name,
            "host":       f"{self.target_host}:{self.target_port}",
            "tags":       self.tags,
        }
        self._send(hello)
        resp = self._recv_line()
        if resp.get("ok"):
            log.info("Registrado como '%s'.", self.service_id)
        else:
            raise ConnectionError(resp.get("error", "Falha no registro"))

    # ── Protocolo ─────────────────────────────────────────────────────────

    def _send(self, obj: dict) -> None:
        self._sock.sendall((json.dumps(obj, ensure_ascii=False) + "\n").encode())

    def _recv_ack(self) -> None:
        self._recv_line()   # descarta ACK do servidor

    def _recv_line(self) -> dict:
        while "\n" not in self._buf:
            chunk = self._sock.recv(BUFFER_SIZE)
            if not chunk:
                raise ConnectionError("Servidor fechou a conexão.")
            self._buf += chunk.decode("utf-8", errors="replace")
        line, self._buf = self._buf.split("\n", 1)
        return json.loads(line.strip())

    # ── Utilitários ───────────────────────────────────────────────────────

    def _close_socket(self) -> None:
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    def _log_sample(self, sample: dict) -> None:
        icons = {"UP": "✔", "DOWN": "✘", "DEGRADED": "⚠"}
        icon  = icons.get(sample["status"], "?")
        lat   = f"{sample['latency_ms']}ms" if sample["latency_ms"] else "n/a"
        log.info(
            "%s  status=%-8s  latência=%-8s  cpu=%.1f%%  mem=%.1f%%",
            icon, sample["status"], lat,
            sample.get("cpu_pct") or 0,
            sample.get("mem_pct") or 0,
        )