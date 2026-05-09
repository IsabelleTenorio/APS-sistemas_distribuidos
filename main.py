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


def main() -> None:
    # 1. Servidor em background
    print(f"  {C.CYAN}Iniciando servidor...{C.RESET}")
    start_background()
    time.sleep(0.5)   # aguarda o socket estar pronto

    # 2. Probes simulados em background
    print(f"  {C.CYAN}Iniciando {N_PROBES} probes simulados...{C.RESET}")
    start_probes_background(N_PROBES, INTERVAL)
    time.sleep(1.0)   # aguarda os probes conectarem e enviarem a 1ª amostra

    # 3. Abre o menu admin no terminal atual
    print(f"  {C.GREEN}Sistema pronto!{C.RESET}\n")
    client = AdminClient(HOST, PORT)
    try:
        client.ping()   # verifica conectividade
        print(f"  {C.GREEN}Admin conectado.{C.RESET}")
        run_menu(client)
    except ConnectionRefusedError:
        print(f"\n  {C.RED}Erro:{C.RESET} Não foi possível conectar ao servidor.")
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n  {C.DIM}Interrompido.{C.RESET}")
    finally:
        client.close()
        print(f"  {C.DIM}Encerrado.{C.RESET}")


if __name__ == "__main__":
    main()