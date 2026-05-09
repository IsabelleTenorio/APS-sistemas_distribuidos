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

# Catálogo de serviços fictícios para a demo
DEMO_SERVICES = [
    {"id": "api-gateway",  "name": "API Gateway",     "host": "httpbin.org:80",        "tags": ["prod", "frontend"]},
    {"id": "auth-service", "name": "Auth Service",    "host": "google.com:80",          "tags": ["prod", "backend"]},
    {"id": "user-db",      "name": "User Database",   "host": "127.0.0.1:5432",        "tags": ["prod", "database"]},
    {"id": "cache-redis",  "name": "Redis Cache",     "host": "127.0.0.1:6379",        "tags": ["prod", "cache"]},
    {"id": "file-storage", "name": "File Storage",    "host": "s3.amazonaws.com:80",   "tags": ["prod", "storage"]},
    {"id": "email-svc",    "name": "Email Service",   "host": "smtp.gmail.com:587",    "tags": ["prod", "notify"]},
    {"id": "analytics",    "name": "Analytics Engine","host": "127.0.0.1:8080",        "tags": ["staging"]},
    {"id": "payment-gw",   "name": "Payment Gateway", "host": "api.stripe.com:443",    "tags": ["prod", "payments"]},
]


def _simulate_sample(state: dict) -> dict:
    """Gera uma amostra simulada com variação realista."""
    jitter     = random.gauss(0, state["base_latency"] * 0.3)
    latency_ms = max(1.0, state["base_latency"] + jitter)
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


def _run_simulated_probe(svc: dict, interval: int) -> None:
    """Loop de um probe simulado com reconexão automática."""
    state = {
        "base_latency": random.uniform(5, 200),
        "cpu_base":     random.uniform(10, 60),
        "mem_base":     random.uniform(30, 70),
        "fail_chance":  random.uniform(0.02, 0.12),
    }

    while True:
        sock = None
        buf  = ""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((SERVER_HOST, SERVER_PORT))

            # Registro
            hello = {"role": "probe", **svc}
            sock.sendall((json.dumps(hello) + "\n").encode())

            # Lê ACK do registro
            while "\n" not in buf:
                buf += sock.recv(4096).decode()
            buf = buf.split("\n", 1)[1]

            print(f"  [demo] {svc['id']:<20} conectado")

            while True:
                sample = _simulate_sample(state)
                sock.sendall((json.dumps(sample) + "\n").encode())

                # Lê ACK da amostra
                while "\n" not in buf:
                    buf += sock.recv(4096).decode()
                buf = buf.split("\n", 1)[1]

                time.sleep(interval + random.uniform(-1, 1))

        except Exception as exc:
            print(f"  [demo] {svc['id']:<20} reconectando... ({exc})")
        finally:
            if sock:
                try:
                    sock.close()
                except OSError:
                    pass
        time.sleep(3)


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
    print(f"\n  Iniciando {len(services)} probe(s) simulado(s) → {args.server}:{args.port}")
    print(f"  Intervalo: {args.interval}s   |   Ctrl+C para encerrar\n")

    for i, svc in enumerate(services):
        threading.Thread(
            target=_run_simulated_probe,
            args=(svc, args.interval),
            daemon=True,
        ).start()
        time.sleep(0.2)   # stagger para evitar thundering herd

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n  Demo encerrado.")


if __name__ == "__main__":
    main()