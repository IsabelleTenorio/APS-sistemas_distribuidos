"""
server/server.py
Ponto de entrada do servidor central.
Só faz uma coisa: aceitar conexões e delegar para handlers.py.
"""

import socket
import threading
import logging

from .handlers import dispatch
from .registry import ServiceRegistry

HOST = "0.0.0.0"
PORT = 9999

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("server")


def start() -> None:
    registry = ServiceRegistry()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, PORT))
        srv.listen(100)

        log.info("═" * 52)
        log.info("  Dashboard de Microsserviços — Servidor Central")
        log.info("  Escutando em %s:%d", HOST, PORT)
        log.info("  Roles aceitos: 'probe' | 'admin'")
        log.info("═" * 52)

        try:
            while True:
                conn, addr = srv.accept()
                threading.Thread(
                    target=dispatch,
                    args=(conn, addr, registry),
                    daemon=True,
                ).start()
        except KeyboardInterrupt:
            log.info("Servidor encerrado.")


if __name__ == "__main__":
    start()