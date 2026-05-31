"""
admin/colors.py
Constantes de cor ANSI e funções de formatação visual.
Nada aqui sabe sobre sockets ou dados de serviços.
"""


class C:
    RESET   = "\033[0m";  BOLD    = "\033[1m";  DIM     = "\033[2m"
    RED     = "\033[91m"; GREEN   = "\033[92m"; YELLOW  = "\033[93m"
    BLUE    = "\033[94m"; CYAN    = "\033[96m"; WHITE   = "\033[97m"
    MAGENTA = "\033[95m"; CLEAR   = "\033[2J\033[H"


STATUS_COLOR = {
    "UP":         C.GREEN,
    "DOWN":       C.RED,
    "DEGRADED":   C.YELLOW,
    "OFFLINE":    C.MAGENTA,
    "CONNECTING": C.CYAN,
}

STATUS_ICON = {
    "UP":         "●",
    "DOWN":       "✘",
    "DEGRADED":   "⚠",
    "OFFLINE":    "○",
    "CONNECTING": "◌",
}


def status_fmt(s: str) -> str:
    col  = STATUS_COLOR.get(s, C.WHITE)
    icon = STATUS_ICON.get(s, "?")
    return f"{col}{icon} {s:<10}{C.RESET}"


def bar(pct: float | None, width: int = 12, color: str = C.GREEN) -> str:
    """Barra de progresso ASCII colorida."""
    if pct is None:
        return f"{C.DIM}{'─' * width}{C.RESET}"
    filled = int(pct / 100 * width)
    return f"{color}{'█' * filled}{C.DIM}{'░' * (width - filled)}{C.RESET} {pct:5.1f}%"


def lat_fmt(ms: float | None) -> str:
    if ms is None:
        return f"{C.DIM}{'n/a':>8}{C.RESET}"
    if ms > 500:
        return f"{C.RED}{ms:>6.1f}ms{C.RESET}"
    if ms > 200:
        return f"{C.YELLOW}{ms:>6.1f}ms{C.RESET}"
    return f"{C.GREEN}{ms:>6.1f}ms{C.RESET}"


def uptime_fmt(pct: float | None) -> str:
    if pct is None:
        return f"{C.DIM}{'n/a':>7}{C.RESET}"
    color = C.GREEN if pct >= 99 else C.YELLOW if pct >= 95 else C.RED
    return f"{color}{pct:6.2f}%{C.RESET}"


def ts_ago(ts_iso: str | None) -> str:
    """Converte ISO timestamp para '5s atrás', '3m atrás', etc."""
    if not ts_iso:
        return "—"
    from datetime import datetime
    try:
        secs = int((datetime.now() - datetime.fromisoformat(ts_iso)).total_seconds())
        if secs < 60:
            return f"{secs}s atrás"
        if secs < 3600:
            return f"{secs // 60}m atrás"
        return f"{secs // 3600}h atrás"
    except ValueError:
        return ts_iso[:19]


def prompt(msg: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value  = input(f"  {C.YELLOW}▶{C.RESET} {msg}{suffix}: ").strip()
    return value if value else default