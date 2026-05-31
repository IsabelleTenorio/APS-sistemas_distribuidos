import socket
import json
import threading
import logging
import time
from datetime import datetime

from .registry import ServiceRegistry

HOST = "0.0.0.0"
PORT = 9999

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s  %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger("server")

def start_background() -> None:
    threading.Thread(target=start, daemon=True).start()

def _cleanup_loop(registry: ServiceRegistry):
    """Marca como OFFLINE serviços que pararam de enviar datagramas UDP."""
    while True:
        time.sleep(5)
        for sid in registry.service_ids():
            svc = registry.snapshot(sid)
            last_seen_str = svc.get("last_seen")
            if last_seen_str and svc.get("status") != "OFFLINE":
                last_seen = datetime.fromisoformat(last_seen_str)
                if (datetime.now() - last_seen).total_seconds() > 12:
                    registry.mark_offline(sid)
                    log.info("PROBE  %-20s  offline (timeout UDP)", sid)

def start() -> None:
    registry = ServiceRegistry()
    threading.Thread(target=_cleanup_loop, args=(registry,), daemon=True).start()

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as srv:
        srv.bind((HOST, PORT))

        log.info("═" * 52)
        log.info("  Dashboard de Microsserviços — Servidor UDP")
        log.info("  Escutando datagramas em %s:%d", HOST, PORT)
        log.info("═" * 52)

        while True:
            try:
                # Recebe pacote UDP solto
                data, addr = srv.recvfrom(65535)
                msg = json.loads(data.decode("utf-8", errors="replace"))
                role = msg.get("role", "").lower()

                if role == "probe":
                    sid = msg.get("service_id")
                    if sid:
                        registry.register(sid, msg) # Atualiza metadados
                        if msg.get("type") == "SAMPLE":
                            registry.record_sample(sid, msg)

                elif role == "admin":
                    cmd = msg.get("cmd", "")
                    parts = cmd.strip().split("|")
                    action = parts[0].upper()
                    resp = {"ok": False, "error": "Comando desconhecido"}

                    if action == "PING":
                        resp = {"ok": True, "type": "PONG"}
                    elif action == "STATUS":
                        sid = parts[1] if len(parts) > 1 else None
                        resp = {"ok": True, "data": registry.snapshot(sid) if sid else registry.snapshot()}
                    elif action == "SUMMARY":
                        resp = {"ok": True, "data": registry.summary()}
                    elif action == "HISTORY":
                        if len(parts) >= 2:
                            sid = parts[1]
                            n = max(1, min(int(parts[2]), 60)) if len(parts) > 2 else 20
                            resp = {"ok": True, "service_id": sid, "samples": registry.history(sid, n)}
                    elif action == "LIST":
                        ids = registry.service_ids()
                        resp = {"ok": True, "services": ids, "total": len(ids)}
                    
                    # Envia a resposta de volta para o cliente UDP
                    srv.sendto((json.dumps(resp)+"\n").encode(), addr)
            except Exception:
                pass # Pacotes UDP malformados são apenas ignorados silenciosamente