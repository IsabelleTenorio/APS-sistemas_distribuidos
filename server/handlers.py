"""
server/handlers.py
Funções que gerenciam cada conexão TCP aberta.
Não sabe nada sobre como o servidor aceita conexões — só como processá-las.
"""

import socket
import json
import time
import logging
from datetime import datetime

from .registry import ServiceRegistry

log = logging.getLogger("handlers")

BUFFER_SIZE = 8192


# ── Helpers de protocolo ──────────────────────────────────────────────────────

def encode(obj: dict) -> bytes:
    """Serializa um dict como linha JSON terminada em newline."""
    return (json.dumps(obj, ensure_ascii=False) + "\n").encode()


def recv_line(sock: socket.socket, buf: list[str]) -> dict:
    """
    Lê uma linha JSON completa do socket.
    `buf` é uma lista de um elemento usada como acumulador mutável.
    """
    while "\n" not in buf[0]:
        chunk = sock.recv(BUFFER_SIZE)
        if not chunk:
            raise ConnectionError("Conexão fechada pelo cliente.")
        buf[0] += chunk.decode("utf-8", errors="replace")
    line, buf[0] = buf[0].split("\n", 1)
    return json.loads(line.strip())


# ── Dispatcher ────────────────────────────────────────────────────────────────

def dispatch(conn: socket.socket, addr: tuple, registry: ServiceRegistry) -> None:
    """
    Lê o primeiro pacote JSON para determinar o papel da conexão:
      role="probe"  →  handle_probe()
      role="admin"  →  handle_admin()
    """
    buf = [""]
    try:
        conn.settimeout(10)
        hello = recv_line(conn, buf)
        conn.settimeout(None)
    except (socket.timeout, json.JSONDecodeError):
        conn.sendall(encode({"ok": False, "error": "Primeiro pacote deve ser JSON com campo 'role'."}))
        return

    role = hello.get("role", "").lower()
    rest = buf[0]   # bytes já lidos além do primeiro \n

    if role == "probe":
        handle_probe(conn, addr, registry, hello, rest)
    elif role == "admin":
        handle_admin(conn, addr, registry, rest)
    else:
        conn.sendall(encode({"ok": False, "error": "Campo 'role' deve ser 'probe' ou 'admin'."}))


# ── Handler de Probe ──────────────────────────────────────────────────────────

def handle_probe(conn: socket.socket, addr: tuple, registry: ServiceRegistry,
                 hello: dict, initial_buf: str) -> None:
    """
    Mantém a conexão aberta com um probe.
    O 'hello' já contém os metadados de registro.
    """
    service_id = hello.get("service_id")
    if not service_id:
        conn.sendall(encode({"ok": False, "error": "service_id obrigatório."}))
        return

    registry.register(service_id, hello)
    conn.sendall(encode({"ok": True, "message": f"Probe '{service_id}' registrado."}))
    log.info("PROBE  %-20s  conectado   %s:%d", service_id, addr[0], addr[1])

    buf = [initial_buf]
    try:
        with conn:
            while True:
                msg = recv_line(conn, buf)
                response = _process_probe_message(msg, service_id, registry)
                conn.sendall(encode(response))
    except (ConnectionResetError, BrokenPipeError, ConnectionError):
        pass
    except Exception as exc:
        log.error("Erro probe %s — %s", service_id, exc)
    finally:
        registry.mark_offline(service_id)
        log.info("PROBE  %-20s  offline     %s:%d", service_id, addr[0], addr[1])


def _process_probe_message(msg: dict, service_id: str, registry: ServiceRegistry) -> dict:
    msg_type = msg.get("type", "").upper()

    if msg_type == "SAMPLE":
        registry.record_sample(service_id, msg)
        return {"ok": True, "recorded": True}

    if msg_type == "REGISTER":
        registry.register(service_id, msg)
        return {"ok": True, "message": "Metadados atualizados."}

    if msg_type == "PING":
        return {"ok": True, "type": "PONG"}

    return {"ok": False, "error": f"type desconhecido: '{msg_type}'"}


# ── Handler de Admin ──────────────────────────────────────────────────────────

def handle_admin(conn: socket.socket, addr: tuple, registry: ServiceRegistry,
                 initial_buf: str) -> None:
    """
    Atende comandos de um cliente administrador.
    Suporta consultas pontuais e o modo WATCH (push periódico).
    """
    conn.sendall(encode({
        "ok": True,
        "message": "Admin conectado. Comandos: STATUS[|id], SUMMARY, HISTORY|id[|n], LIST, WATCH[|s], PING",
    }))
    log.info("ADMIN  conectado   %s:%d", addr[0], addr[1])

    buf = [initial_buf]
    try:
        with conn:
            while True:
                raw = recv_line(conn, buf)
                # Aceita tanto string (comando) quanto dict (extensibilidade futura)
                cmd = raw if isinstance(raw, str) else raw.get("cmd", "")
                response = _process_admin_command(cmd, registry, conn)
                if response is None:
                    break   # WATCH encerrou (cliente desconectou)
                conn.sendall(encode(response))
    except (ConnectionResetError, BrokenPipeError, ConnectionError):
        pass
    except Exception as exc:
        log.error("Erro admin %s:%d — %s", addr[0], addr[1], exc)
    finally:
        log.info("ADMIN  desconectado %s:%d", addr[0], addr[1])


def _process_admin_command(cmd: str, registry: ServiceRegistry,
                           conn: socket.socket) -> dict | None:
    parts  = cmd.strip().split("|")
    action = parts[0].upper()

    if action == "STATUS":
        sid  = parts[1] if len(parts) > 1 else None
        data = registry.snapshot(sid) if sid else registry.snapshot()
        return {"ok": True, "data": data}

    if action == "SUMMARY":
        return {"ok": True, "data": registry.summary()}

    if action == "HISTORY":
        if len(parts) < 2:
            return {"ok": False, "error": "Uso: HISTORY|service_id[|n]"}
        sid  = parts[1]
        n    = int(parts[2]) if len(parts) > 2 else 20
        return {"ok": True, "service_id": sid, "samples": registry.history(sid, n)}

    if action == "LIST":
        ids = registry.service_ids()
        return {"ok": True, "services": ids, "total": len(ids)}

    if action == "WATCH":
        interval = max(1, min(int(parts[1]) if len(parts) > 1 else 5, 60))
        _watch_loop(conn, registry, interval)
        return None   # sinaliza que o loop encerrou

    if action == "PING":
        return {"ok": True, "type": "PONG"}

    return {"ok": False, "error": f"Comando desconhecido: '{action}'"}


def _watch_loop(conn: socket.socket, registry: ServiceRegistry, interval: int) -> None:
    """Envia atualizações periódicas enquanto o cliente estiver conectado."""
    conn.sendall(encode({"ok": True, "message": f"Watch ativo a cada {interval}s."}))
    try:
        while True:
            conn.sendall(encode({
                "type":     "WATCH_UPDATE",
                "ts":       datetime.now().isoformat(),
                "summary":  registry.summary(),
                "services": registry.snapshot(),
            }))
            time.sleep(interval)
    except (BrokenPipeError, ConnectionResetError, OSError):
        pass