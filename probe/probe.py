"""
probe/probe.py
Ponto de entrada do probe.
Analisa argumentos CLI e inicia o ProbeAgent.
"""

import argparse
import logging
import sys

from .agent import ProbeAgent

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Agente probe de monitoramento")
    p.add_argument("--id",          required=True,         help="ID único (ex: api-gateway)")
    p.add_argument("--name",        default=None,          help="Nome legível (padrão: --id)")
    p.add_argument("--server",      default="127.0.0.1",   help="Host do servidor central")
    p.add_argument("--server-port", default=9999, type=int,help="Porta do servidor")
    p.add_argument("--target",      default="127.0.0.1",   help="Host do serviço monitorado")
    p.add_argument("--target-port", default=80,   type=int,help="Porta do serviço monitorado")
    p.add_argument("--interval",    default=5,    type=int,help="Intervalo de coleta (segundos)")
    p.add_argument("--tags",        default="",            help="Tags separadas por vírgula")
    return p.parse_args()


def main() -> None:
    args  = _parse_args()
    agent = ProbeAgent(
        service_id=  args.id,
        name=        args.name or args.id,
        server_host= args.server,
        server_port= args.server_port,
        target_host= args.target,
        target_port= args.target_port,
        interval=    args.interval,
        tags=        [t.strip() for t in args.tags.split(",") if t.strip()],
    )
    try:
        agent.run()
    except KeyboardInterrupt:
        print()
    finally:
        agent.stop()


if __name__ == "__main__":
    main()