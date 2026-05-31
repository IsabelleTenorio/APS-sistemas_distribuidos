# Estrutura de dados em memória para o estado de todos os serviços monitorados.

import threading
from datetime import datetime
from collections import deque

MAX_HISTORY = 60  # últimas N amostras por serviço


class ServiceRegistry:
   
   # Cada serviço armazena:
     # - Metadados (nome, host, tags)
     # - Status atual (UP / DOWN / DEGRADED / OFFLINE / CONNECTING)
     # - Última latência e uptime calculado
     # - Histórico circular das últimas MAX_HISTORY amostras

    def __init__(self):
        self._lock = threading.RLock()
        self._services: dict[str, dict] = {}

    # ── Registro de probe ─────────────────────────────────────────────────
    def register(self, service_id: str, meta: dict) -> None:
        with self._lock:
            if service_id not in self._services:
                self._services[service_id] = _new_service(service_id, meta)
            else:
                _update_meta(self._services[service_id], meta)

    # ── Gravação de amostra ───────────────────────────────────────────────
    def record_sample(self, service_id: str, sample: dict) -> bool:
        with self._lock:
            svc = self._services.get(service_id)
            if svc is None:
                return False
            _apply_sample(svc, sample)
            return True

    # ── Marcação de offline ───────────────────────────────────────────────
    def mark_offline(self, service_id: str) -> None:
        with self._lock:
            svc = self._services.get(service_id)
            if svc:
                svc["status"] = "OFFLINE"
                svc["total_fail"] += 1
                _recalc_uptime(svc)

    # ── Consultas (retornam cópias, nunca referências internas) ───────────
    def snapshot(self, service_id: str | None = None) -> dict:
        """Estado atual de um ou todos os serviços (sem histórico)."""
        with self._lock:
            if service_id:
                svc = self._services.get(service_id)
                return _public_view(svc) if svc else {}
            return {sid: _public_view(s) for sid, s in self._services.items()}

    def history(self, service_id: str, last_n: int = 20) -> list:
        """Últimas N amostras de um serviço."""
        with self._lock:
            svc = self._services.get(service_id)
            if svc is None:
                return []
            return list(svc["history"])[-last_n:]

    def summary(self) -> dict:
        """Contadores globais e health score."""
        with self._lock:
            svcs = list(self._services.values())
        return _build_summary(svcs)

    def service_ids(self) -> list[str]:
        with self._lock:
            return list(self._services.keys())


# ── Funções auxiliares (módulo-privadas) ──────────────────────────────────────

def _new_service(service_id: str, meta: dict) -> dict:
    return {
        "id":         service_id,
        "name":       meta.get("name", service_id),
        "host":       meta.get("host", "unknown"),
        "tags":       meta.get("tags", []),
        "registered": datetime.now().isoformat(),
        "last_seen":  None,
        "status":     "CONNECTING",
        "uptime_pct": None,
        "latency_ms": None,
        "history":    deque(maxlen=MAX_HISTORY),
        "total_ok":   0,
        "total_fail": 0,
    }


def _update_meta(svc: dict, meta: dict) -> None:
    svc["name"]   = meta.get("name", svc["name"])
    svc["host"]   = meta.get("host", svc["host"])
    svc["tags"]   = meta.get("tags", svc["tags"])
    svc["status"] = "CONNECTING"


def _apply_sample(svc: dict, sample: dict) -> None:
    status = sample.get("status", "UP").upper()
    svc["last_seen"]  = datetime.now().isoformat()
    svc["status"]     = status
    svc["latency_ms"] = sample.get("latency_ms")

    if status == "UP":
        svc["total_ok"] += 1
    else:
        svc["total_fail"] += 1

    _recalc_uptime(svc)

    svc["history"].append({
        "ts":         svc["last_seen"],
        "status":     status,
        "latency_ms": sample.get("latency_ms"),
        "cpu_pct":    sample.get("cpu_pct"),
        "mem_pct":    sample.get("mem_pct"),
        "custom":     sample.get("custom", {}),
    })


def _recalc_uptime(svc: dict) -> None:
    total = svc["total_ok"] + svc["total_fail"]
    svc["uptime_pct"] = round(svc["total_ok"] / total * 100, 2) if total else None


def _public_view(svc: dict) -> dict:
    """Retorna apenas os campos públicos (exclui o deque interno)."""
    return {k: v for k, v in svc.items() if k != "history"}


def _build_summary(svcs: list) -> dict:
    total = len(svcs)
    lats  = [s["latency_ms"] for s in svcs if s["latency_ms"] is not None]
    up    = sum(1 for s in svcs if s["status"] == "UP")
    return {
        "total":          total,
        "up":             up,
        "down":           sum(1 for s in svcs if s["status"] == "DOWN"),
        "degraded":       sum(1 for s in svcs if s["status"] == "DEGRADED"),
        "offline":        sum(1 for s in svcs if s["status"] == "OFFLINE"),
        "avg_latency_ms": round(sum(lats) / len(lats), 2) if lats else None,
        "health_score":   round(up / total * 100, 1) if total else None,
    }