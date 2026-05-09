"""
admin/renderer.py
Funções de renderização do dashboard no terminal.
Recebe apenas dicts com dados — não sabe nada sobre sockets.
"""

from datetime import datetime
from .colors import C, status_fmt, bar, lat_fmt, uptime_fmt, ts_ago

WIDTH = 90   # largura total do painel


def render_dashboard(summary: dict, services: dict) -> None:
    """Limpa o terminal e redesenha o painel completo."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(C.CLEAR, end="")
    _border_top()
    _title_row(now)
    _summary_row(summary)
    _table_header()

    if not services:
        _empty_row()
    else:
        for sid, svc in sorted(services.items()):
            _service_row(svc)

    _border_bottom()
    print(f"\n{C.DIM}  Pressione Ctrl+C para encerrar  |  modo: WATCH{C.RESET}")


def render_history(service_id: str, samples: list) -> None:
    """Imprime tabela com histórico de amostras de um serviço."""
    print(f"\n  {C.BOLD}Últimas {len(samples)} amostras de '{service_id}':{C.RESET}")
    print(f"  {C.BOLD}{'TIMESTAMP':<22} {'STATUS':<10} {'LATÊNCIA':>8}  {'CPU':>6}  {'MEM':>6}{C.RESET}")
    print(f"  {'─' * 60}")
    for s in samples:
        st  = s.get("status", "?")
        col = C.__dict__.get(st, C.WHITE)
        ts  = s.get("ts", "?")[:19]
        print(
            f"  {C.DIM}{ts}{C.RESET}  "
            f"{status_fmt(st)}"
            f"{lat_fmt(s.get('latency_ms')):>8}  "
            f"{str(s.get('cpu_pct', '?')) + '%':>6}  "
            f"{str(s.get('mem_pct', '?')) + '%':>6}"
        )


def render_service_detail(svc: dict) -> None:
    """Imprime detalhes de um único serviço."""
    print(f"\n  {C.BOLD}{svc.get('name', '?')}{C.RESET}  ({C.DIM}{svc.get('id', '?')}{C.RESET})")
    print(f"  {'─' * 40}")
    print(f"  Status:      {status_fmt(svc.get('status', '?'))}")
    print(f"  Host:        {C.DIM}{svc.get('host', '?')}{C.RESET}")
    print(f"  Latência:    {lat_fmt(svc.get('latency_ms'))}")
    print(f"  Uptime:      {uptime_fmt(svc.get('uptime_pct'))}")
    print(f"  OK / Falhas: {C.GREEN}{svc.get('total_ok', 0)}{C.RESET} / {C.RED}{svc.get('total_fail', 0)}{C.RESET}")
    print(f"  Tags:        {C.DIM}{', '.join(svc.get('tags', []))}{C.RESET}")
    print(f"  Registrado:  {C.DIM}{svc.get('registered', '?')[:19]}{C.RESET}")
    print(f"  Visto:       {ts_ago(svc.get('last_seen'))}")


def render_summary(data: dict) -> None:
    """Imprime resumo global."""
    health = data.get("health_score")
    color  = C.GREEN if (health or 0) >= 90 else C.YELLOW if (health or 0) >= 70 else C.RED

    print(f"\n  {C.BOLD}Resumo global{C.RESET}")
    print(f"  {'─' * 40}")
    print(f"  Total de serviços: {data.get('total', 0)}")
    print(f"  {C.GREEN}UP:{C.RESET}       {data.get('up', 0)}")
    print(f"  {C.RED}DOWN:{C.RESET}     {data.get('down', 0)}")
    print(f"  {C.YELLOW}DEGRADED:{C.RESET} {data.get('degraded', 0)}")
    print(f"  {C.MAGENTA}OFFLINE:{C.RESET}  {data.get('offline', 0)}")
    print(f"  Lat. média: {lat_fmt(data.get('avg_latency_ms'))}")
    print(f"  Health:     {bar(health, 20, color)}")


# ── Helpers internos ──────────────────────────────────────────────────────────

def _border_top() -> None:
    print(f"{C.BOLD}{C.BLUE}╔{'═' * (WIDTH - 2)}╗{C.RESET}")


def _border_bottom() -> None:
    print(f"{C.BOLD}{C.BLUE}╚{'═' * (WIDTH - 2)}╝{C.RESET}")


def _divider() -> None:
    print(f"{C.BOLD}{C.BLUE}╠{'─' * (WIDTH - 2)}╣{C.RESET}")


def _row(content: str) -> None:
    print(f"{C.BOLD}{C.BLUE}║{C.RESET}{content}{C.BOLD}{C.BLUE}║{C.RESET}")


def _title_row(now: str) -> None:
    title = "  📡  DASHBOARD DE SAÚDE DE MICROSSERVIÇOS"
    _row(f"{C.BOLD}{C.WHITE}{title:<{WIDTH - 2}}{C.RESET}")
    _row(f"{C.DIM}  Atualizado: {now}{' ' * (WIDTH - 16 - len(now))}{C.RESET}")
    print(f"{C.BOLD}{C.BLUE}╠{'═' * (WIDTH - 2)}╣{C.RESET}")


def _summary_row(summary: dict) -> None:
    health = summary.get("health_score")
    color  = C.GREEN if (health or 0) >= 90 else C.YELLOW if (health or 0) >= 70 else C.RED
    health_bar = bar(health, 20, color)
    line1 = (
        f"  {C.BOLD}RESUMO{C.RESET}  "
        f"{C.GREEN}UP:{summary.get('up', 0)}{C.RESET}  "
        f"{C.RED}DOWN:{summary.get('down', 0)}{C.RESET}  "
        f"{C.YELLOW}DEGRADED:{summary.get('degraded', 0)}{C.RESET}  "
        f"{C.MAGENTA}OFFLINE:{summary.get('offline', 0)}{C.RESET}  "
        f"Total:{summary.get('total', 0)}"
    )
    _row(f"{line1:<{WIDTH + 20}}")
    _row(f"  {health_bar:<{WIDTH + 20}}")
    print(f"{C.BOLD}{C.BLUE}╠{'═' * (WIDTH - 2)}╣{C.RESET}")


def _table_header() -> None:
    hdr = (
        f"  {C.BOLD}{'STATUS':<13} {'SERVIÇO':<22} {'HOST':<22}"
        f" {'LATÊNCIA':>8}  {'UPTIME':>7}  {'VISTO':>10}{C.RESET}"
    )
    _row(f"{hdr:<{WIDTH + 20}}")
    _divider()


def _service_row(svc: dict) -> None:
    row = (
        f"  {status_fmt(svc.get('status', '?'))}"
        f"  {C.BOLD}{svc.get('name', '')[:20]:<22}{C.RESET}"
        f"{C.DIM}{svc.get('host', '')[:20]:<22}{C.RESET}"
        f"{lat_fmt(svc.get('latency_ms')):>8}  "
        f"{uptime_fmt(svc.get('uptime_pct')):>7}  "
        f"{C.DIM}{ts_ago(svc.get('last_seen')):>10}{C.RESET}"
    )
    _row(f"{row}")


def _empty_row() -> None:
    _row(f"  {C.DIM}Nenhum probe conectado ainda...{' ' * (WIDTH - 34)}{C.RESET}")