# Ponto de entrada do cliente administrador.

import argparse
import sys

from .client   import AdminClient
from .renderer import (
    render_dashboard,
    render_history,
    render_service_detail,
    render_summary,
)
from .colors import C, prompt


# ── Menu principal ────────────────────────────────────────────────────────────

def run_menu(client: AdminClient) -> None:
    while True:
        _print_menu()
        choice = prompt("Opção")

        if   choice == "1": _cmd_summary(client)
        elif choice == "2": _cmd_status_all(client)
        elif choice == "3": _cmd_status_one(client)
        elif choice == "4": _cmd_history(client)
        elif choice == "5": _cmd_list(client)
        elif choice == "6": _cmd_watch(client)
        elif choice == "0": break
        else:
            print(f"  {C.YELLOW}Opção inválida.{C.RESET}")


def run_watch(client: AdminClient, interval: int) -> None:
 
    # Modo watch: atualiza o dashboard em uma thread separada de N em N seg
  
    import threading

    stop = threading.Event()

    def _loop():
        try:
            for update in client.watch(interval):
                if stop.is_set():
                    break
                if update.get("type") == "WATCH_UPDATE":
                    render_dashboard(update.get("summary", {}), update.get("services", {}))
        except Exception:
            pass

    t = threading.Thread(target=_loop, daemon=True)
    t.start()

    input()   # aguarda Enter silenciosamente — o dashboard está na tela
    stop.set()


# ── Handlers de cada opção ────────────────────────────────────────────────────

def _cmd_summary(client: AdminClient) -> None:
    resp = client.summary()
    if resp.get("ok"):
        render_summary(resp["data"])
    else:
        _print_error(resp)


def _cmd_status_all(client: AdminClient) -> None:
    resp_status  = client.status()
    resp_summary = client.summary()
    if resp_status.get("ok") and resp_summary.get("ok"):
        render_dashboard(resp_summary["data"], resp_status["data"])
        input(f"\n  {C.DIM}[Enter para continuar]{C.RESET}")
    else:
        _print_error(resp_status if not resp_status.get("ok") else resp_summary)


def _cmd_status_one(client: AdminClient) -> None:
    sid  = prompt("ID do serviço")
    resp = client.status(sid)
    if resp.get("ok"):
        data = resp["data"]
        # STATUS|id retorna o dict do serviço diretamente
        svc  = data if "id" in data else data.get(sid, {})
        render_service_detail(svc)
    else:
        _print_error(resp)


def _cmd_history(client: AdminClient) -> None:
    sid  = prompt("ID do serviço")
    n    = int(prompt("Quantas amostras", "20"))
    resp = client.history(sid, n)
    if resp.get("ok"):
        render_history(sid, resp.get("samples", []))
    else:
        _print_error(resp)


def _cmd_list(client: AdminClient) -> None:
    resp = client.list_services()
    if resp.get("ok"):
        ids = resp.get("services", [])
        print(f"\n  {C.BOLD}Probes registrados ({len(ids)}):{C.RESET}")
        for sid in ids:
            print(f"    {C.DIM}•{C.RESET} {C.CYAN}{sid}{C.RESET}")
    else:
        _print_error(resp)


def _cmd_watch(client: AdminClient) -> None:
    interval = int(prompt("Intervalo em segundos", "5"))
    print(f"  {C.DIM}Iniciando watch... Pressione Enter para voltar ao menu.{C.RESET}")
    run_watch(client, interval)


# ── UI helpers ────────────────────────────────────────────────────────────────

def _print_menu() -> None:
    print(f"\n{C.BOLD}{C.BLUE}╔══════════════════════════════════════════╗{C.RESET}")
    print(f"{C.BOLD}{C.BLUE}║  📡 Dashboard de Microsserviços — Admin  ║{C.RESET}")
    print(f"{C.BOLD}{C.BLUE}╠══════════════════════════════════════════╣{C.RESET}")
    opts = [
        ("1", "Resumo global"),
        ("2", "Status de todos os serviços"),
        ("3", "Status de um serviço específico"),
        ("4", "Histórico de amostras"),
        ("5", "Listar IDs dos probes"),
        ("6", "Dashboard ao vivo (WATCH)"),
        ("0", "Sair"),
    ]
    for key, label in opts:
        print(f"{C.BOLD}{C.BLUE}║{C.RESET}  {C.YELLOW}{key}.{C.RESET} {label:<38}{C.BOLD}{C.BLUE}║{C.RESET}")
    print(f"{C.BOLD}{C.BLUE}╚══════════════════════════════════════════╝{C.RESET}")


def _print_error(resp: dict) -> None:
    print(f"  {C.RED}Erro: {resp.get('error', 'desconhecido')}{C.RESET}")


# ── Entry point ───────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Cliente administrador do dashboard")
    p.add_argument("--server",   default="127.0.0.1", help="Host do servidor")
    p.add_argument("--port",     default=9999, type=int)
    p.add_argument("--watch",    action="store_true",  help="Inicia direto no modo watch")
    p.add_argument("--interval", default=5,   type=int,help="Intervalo do watch (segundos)")
    return p.parse_args()


def main() -> None:
    args   = _parse_args()
    client = AdminClient(args.server, args.port)
    try:
        client.ping()
        print(f"  {C.GREEN}Conectado ao servidor {args.server}:{args.port}{C.RESET}")

        if args.watch:
            run_watch(client, args.interval)
        else:
            run_menu(client)

    except ConnectionRefusedError:
        print(f"\n  {C.RED}Erro:{C.RESET} Não foi possível conectar a {args.server}:{args.port}.")
        print("  Verifique se o servidor está rodando.")
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n  {C.DIM}Interrompido.{C.RESET}")
    finally:
        client.close()
        print(f"  {C.DIM}Conexão encerrada.{C.RESET}")


if __name__ == "__main__":
    main()