"""
main.py
Ponto de entrada único do sistema.
Sobe o servidor e os probes simulados em threads de fundo
e abre o menu de administração no terminal atual.
"""

import time
import sys

from server.server      import start_background
from probe.demo_probes  import start_probes_background
from admin.client       import AdminClient
from admin.admin        import run_menu
from admin.colors       import C

HOST     = "127.0.0.1"
PORT     = 9999
N_PROBES = 8
INTERVAL = 4   # segundos entre amostras dos probes


def _wait_for_server(client: AdminClient, retries: int = 10, delay: float = 0.5) -> bool:
    """Tenta conectar ao servidor repetidamente até ele estar pronto."""
    for _ in range(retries):
        try:
            client.ping()
            return True
        except (ConnectionRefusedError, ConnectionError, OSError):
            time.sleep(delay)
    return False


def main() -> None:
    # 1. Servidor em background
    print(f"  {C.CYAN}Iniciando servidor...{C.RESET}")
    start_background()

    # 2. Aguarda o servidor estar pronto (até 5s)
    client = AdminClient(HOST, PORT)
    if not _wait_for_server(client):
        print(f"  {C.RED}Erro: servidor não respondeu. Encerrando.{C.RESET}")
        sys.exit(1)

    # 3. Probes simulados em background
    print(f"  {C.CYAN}Iniciando {N_PROBES} probes simulados...{C.RESET}")
    start_probes_background(N_PROBES, INTERVAL)
    time.sleep(1.5)   # aguarda os probes enviarem a 1ª amostra

    # 4. Abre o menu admin no terminal atual
    print(f"  {C.GREEN}Sistema pronto!{C.RESET}\n")
    try:
        run_menu(client)
    except ConnectionRefusedError:
        print(f"\n  {C.RED}Erro:{C.RESET} Não foi possível conectar ao servidor.")
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n  {C.DIM}Interrompido.{C.RESET}")
    finally:
        print(f"  {C.DIM}Encerrado.{C.RESET}")


if __name__ == "__main__":
    main()