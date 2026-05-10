"""
probe/demo_probes.py
Lança N probes simulados em threads para demonstrar o sistema sem
precisar de serviços reais rodando.
Execute com o servidor já rodando.
"""

import argparse
import json
import random
import socket
import threading
import time

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 9999

DEMO_SERVICES = [
    {"service_id": "api-gateway",  "name": "API Gateway",      "host": "api:80",     "tags": ["prod", "frontend"]},
    {"service_id": "auth-service", "name": "Auth Service",      "host": "auth:80",    "tags": ["prod", "backend"]},
    {"service_id": "user-db",      "name": "User Database",     "host": "db:5432",    "tags": ["prod", "database"]},
    {"service_id": "cache-redis",  "name": "Redis Cache",       "host": "redis:6379", "tags": ["prod", "cache"]},
    {"service_id": "file-storage", "name": "File Storage",      "host": "fs:80",      "tags": ["prod", "storage"]},
    {"service_id": "email-svc",    "name": "Email Service",     "host": "mail:587",   "tags": ["prod", "notify"]},
    {"service_id": "analytics",    "name": "Analytics Engine",  "host": "analytics:8080", "tags": ["staging"]},
    {"service_id": "payment-gw",   "name": "Payment Gateway",   "host": "pay:443",    "tags": ["prod", "payments"]},
]


# ── Comunicação TCP ───────────────────────────────────────────────────────────

class ProbeConn:
    """Gerencia a conexão TCP de um probe simulado com o servidor."""

    def __init__(self, host: str, port: int):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.connect((host, port))
        self._buf = ""

    def send(self, obj: dict) -> None:
        self._sock.sendall((json.dumps(obj) + "\n").encode())

    def recv(self) -> dict:
        while "\n" not in self._buf:
            chunk = self._sock.recv(4096)
            if not chunk:
                raise ConnectionError("Servidor fechou a conexão.")
            self._buf += chunk.decode("utf-8", errors="replace")
        line, self._buf = self._buf.split("\n", 1)
        return json.loads(line.strip())

    def close(self) -> None:
        try:
            self._sock.close()
        except OSError:
            pass


# ── Geração de amostras simuladas ─────────────────────────────────────────────

def _make_state() -> dict:
    return {
        "base_latency": random.uniform(5, 200),
        "cpu_base":     random.uniform(10, 60),
        "mem_base":     random.uniform(30, 70),
        "fail_chance":  random.uniform(0.02, 0.12),
    }


def _simulate_sample(state: dict) -> dict:
    latency_ms = max(1.0, state["base_latency"] + random.gauss(0, state["base_latency"] * 0.3))
    cpu_pct    = min(100, max(0, random.gauss(state["cpu_base"], 8)))
    mem_pct    = min(100, max(0, random.gauss(state["mem_base"], 4)))

    r = random.random()
    if r < state["fail_chance"] * 0.3:
        status, latency_ms = "DOWN", None
    elif r < state["fail_chance"]:
        status     = "DEGRADED"
        latency_ms = latency_ms * random.uniform(3, 10)
    else:
        status = "UP"

    return {
        "type":       "SAMPLE",
        "status":     status,
        "latency_ms": round(latency_ms, 2) if latency_ms else None,
        "cpu_pct":    round(cpu_pct, 1),
        "mem_pct":    round(mem_pct, 1),
    }


# ── Loop do probe ─────────────────────────────────────────────────────────────

def _run_probe(svc: dict, interval: int) -> None:
    sid   = svc["service_id"]
    state = _make_state()

    while True:
        conn = None
        try:
            conn = ProbeConn(SERVER_HOST, SERVER_PORT)

            # 1. Envia hello com role=probe e aguarda ACK
            conn.send({"role": "probe", **svc})
            ack = conn.recv()
            if not ack.get("ok"):
                raise ConnectionError(f"Registro recusado: {ack.get('error')}")
            (f"  [probe] {sid:<20} conectado")

            # 2. Loop de amostras: envia → aguarda ACK → aguarda intervalo
            while True:
                sample = _simulate_sample(state)
                conn.send(sample)
                conn.recv()   # ACK do servidor — garante sincronismo
                time.sleep(interval + random.uniform(-0.5, 0.5))

        except Exception as exc:
            (f"  [probe] {sid:<20} reconectando em 3s... ({exc})")
        finally:
            if conn:
                conn.close()
        time.sleep(3)


# ── Entry point ───────────────────────────────────────────────────────────────

def start_probes_background(count: int = len(DEMO_SERVICES), interval: int = 4) -> None:
    """Sobe N probes simulados em threads daemon e retorna imediatamente."""
    for svc in DEMO_SERVICES[:count]:
        threading.Thread(
            target=_run_probe,
            args=(svc, interval),
            daemon=True,
        ).start()
        time.sleep(0.3)


def main() -> None:
    p = argparse.ArgumentParser(description="Demo: probes simulados")
    p.add_argument("--server",   default="127.0.0.1", help="Host do servidor")
    p.add_argument("--port",     default=9999, type=int)
    p.add_argument("--interval", default=4,   type=int, help="Intervalo de envio (seg)")
    p.add_argument("--count",    default=len(DEMO_SERVICES), type=int,
                   help=f"Quantos probes lançar (máx {len(DEMO_SERVICES)})")
    args = p.parse_args()

    global SERVER_HOST, SERVER_PORT
    SERVER_HOST = args.server
    SERVER_PORT = args.port

    services = DEMO_SERVICES[: args.count]
    (f"\n  Iniciando {len(services)} probe(s) → {args.server}:{args.port}")
    (f"  Intervalo: {args.interval}s   |   Ctrl+C para encerrar\n")

    for svc in services:
        threading.Thread(
            target=_run_probe,
            args=(svc, args.interval),
            daemon=True,
        ).start()
        time.sleep(0.3)   # stagger: evita que todos conectem ao mesmo tempo

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        ("\n  Demo encerrado.")


if __name__ == "__main__":
    main()