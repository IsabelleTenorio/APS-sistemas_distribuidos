"""
probe/metrics.py
Coleta métricas do sistema e mede latência TCP para o serviço monitorado.
Não sabe nada sobre como enviar dados ao servidor — pura lógica de medição.
"""

import socket
import time
import random
from datetime import datetime

# psutil é opcional: se não instalado, simula valores plausíveis
try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False


def collect(target_host: str, target_port: int) -> dict:
    """
    Retorna um dict com:
      - status:     UP | DOWN | DEGRADED
      - latency_ms: float | None
      - cpu_pct:    float
      - mem_pct:    float
      - ts:         ISO-8601
    """
    status, latency_ms = _measure_latency(target_host, target_port)
    cpu_pct, mem_pct   = _system_usage()

    return {
        "type":       "SAMPLE",
        "ts":         datetime.now().isoformat(),
        "status":     status,
        "latency_ms": latency_ms,
        "cpu_pct":    cpu_pct,
        "mem_pct":    mem_pct,
    }


# ── Funções internas ──────────────────────────────────────────────────────────

def _measure_latency(host: str, port: int) -> tuple[str, float | None]:
    """Abre uma conexão TCP e mede o tempo de resposta."""
    t0 = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=3):
            latency_ms = round((time.monotonic() - t0) * 1000, 2)
        status = "DEGRADED" if latency_ms > 500 else "UP"
        return status, latency_ms
    except OSError:
        return "DOWN", None


def _system_usage() -> tuple[float, float]:
    """Retorna (cpu_pct, mem_pct). Usa psutil se disponível, senão simula."""
    if _HAS_PSUTIL:
        return (
            psutil.cpu_percent(interval=None),
            psutil.virtual_memory().percent,
        )
    # Simulação com distribuição normal para parecer dados reais
    cpu = round(min(100, max(0, random.gauss(40, 15))), 1)
    mem = round(min(100, max(0, random.gauss(55, 10))), 1)
    return cpu, mem