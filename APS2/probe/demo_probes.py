import argparse, json, random, socket, threading, time

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 9999

DEMO_SERVICES = [
    {"service_id": "api-gateway",  "name": "API Gateway",      "host": "api:80",     "tags": ["prod", "frontend"]},
    {"service_id": "auth-service", "name": "Auth Service",     "host": "auth:80",    "tags": ["prod", "backend"]},
    {"service_id": "user-db",      "name": "User Database",    "host": "db:5432",    "tags": ["prod", "database"]},
    {"service_id": "cache-redis",  "name": "Redis Cache",      "host": "redis:6379", "tags": ["prod", "cache"]},
    {"service_id": "file-storage", "name": "File Storage",     "host": "fs:80",      "tags": ["prod", "storage"]},
    {"service_id": "email-svc",    "name": "Email Service",    "host": "mail:587",   "tags": ["prod", "notify"]},
    {"service_id": "analytics",    "name": "Analytics Engine", "host": "analytics:8080", "tags": ["staging"]},
    {"service_id": "payment-gw",   "name": "Payment Gateway",  "host": "pay:443",    "tags": ["prod", "payments"]},
]

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
        status, latency_ms = "DEGRADED", latency_ms * random.uniform(3, 10)
    else:
        status = "UP"

    return {
        "type": "SAMPLE", "status": status,
        "latency_ms": round(latency_ms, 2) if latency_ms else None,
        "cpu_pct": round(cpu_pct, 1), "mem_pct": round(mem_pct, 1),
    }

def _run_probe(svc: dict, interval: int) -> None:
    sid = svc["service_id"]
    state = _make_state()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    while True:
        try:
            sample = _simulate_sample(state)
            # No UDP, enviamos metadados junto com a amostra
            msg = {"role": "probe", "service_id": sid, "name": svc["name"], "host": svc["host"], "tags": svc["tags"], **sample}
            sock.sendto(json.dumps(msg).encode(), (SERVER_HOST, SERVER_PORT))
        except Exception:
            pass
        time.sleep(interval + random.uniform(-0.5, 0.5))

def start_probes_background(count: int = len(DEMO_SERVICES), interval: int = 4) -> None:
    for svc in DEMO_SERVICES[:count]:
        threading.Thread(target=_run_probe, args=(svc, interval), daemon=True).start()
        time.sleep(0.3)

def main() -> None:
    p = argparse.ArgumentParser(description="Demo: probes simulados")
    p.add_argument("--server", default="127.0.0.1")
    p.add_argument("--port", default=9999, type=int)
    p.add_argument("--interval", default=4, type=int)
    p.add_argument("--count", default=len(DEMO_SERVICES), type=int)
    args = p.parse_args()

    global SERVER_HOST, SERVER_PORT
    SERVER_HOST, SERVER_PORT = args.server, args.port

    print(f"\n  Iniciando probes UDP → {SERVER_HOST}:{SERVER_PORT}")
    start_probes_background(args.count, args.interval)

    try:
        while True: time.sleep(1)
    except KeyboardInterrupt: pass

if __name__ == "__main__":
    main()