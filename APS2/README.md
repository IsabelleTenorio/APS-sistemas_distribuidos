# 📡 Dashboard de Saúde de Microsserviços (Versão UDP)
 
Sistema **distribuído cliente-servidor via Sockets UDP** para monitoramento contínuo de status (Uptime, Latência, CPU, Memória) de múltiplos microsserviços.
 
Desenvolvido como parte da **Atividade 02** da disciplina **CIN0143 – Introdução aos Sistemas Distribuídos e Redes de Computadores** pela **Equipe 6**, composta por: Eduarda Rodrigues, Elinaldo Emanoel, Gabriel Sousa e Isabelle Tenório.
 
---
 
## 📁 Estrutura do Projeto
 
```text
APS2/
├── main.py              # Ponto de entrada único — roda tudo em 1 terminal
├── server/
│   ├── registry.py      # Estrutura de dados em memória e controle de concorrência
│   ├── server.py        # Loop de escuta de datagramas UDP e despachos
│   └── __init__.py
│
├── probe/
│   ├── demo_probes.py   # Probes simulados enviando datagramas em threads independentes
│   └── __init__.py
│
└── admin/
    ├── colors.py        # Constantes ANSI e helpers de formatação
    ├── renderer.py      # Desenho do dashboard no terminal
    ├── client.py        # Requisições UDP para o servidor (com Timeout)
    ├── admin.py         # Menu interativo de administração
    └── __init__.py
```
 
---
 
## ✨ Funcionalidades (Arquitetura UDP)
 
- **Ausência de Conexões (Connectionless)** — O servidor não mantém sockets abertos. Ele possui um único loop assíncrono aguardando pacotes (datagramas) na porta.
- **Probes simulados ("Fire and Forget")** — Múltiplos probes em threads atiram pacotes de amostra para o servidor sem bloquear aguardando respostas.
- **Timeout & Polling no Admin** — O dashboard ao vivo (modo WATCH) realiza polling a cada N segundos, com timeout de 2s para evitar travamento em caso de perda de pacotes UDP.
- **Cleanup Assíncrono** — Uma thread auxiliar marca os probes como `OFFLINE` caso fiquem mais de 12 segundos sem enviar um pacote UDP.
- **Agregação em memória** — Histórico circular das últimas 60 amostras por serviço (`deque`).
---
 
## 🚀 Como Rodar
 
### Pré-requisitos
 
- **Python 3.10+** — sem dependências externas, apenas biblioteca padrão.
> ⚠️ Todos os comandos abaixo devem ser executados a partir da pasta raiz da atividade (`APS2/`).
 
### Terminal único
 
```bash
cd APS2
python3 main.py
```
 
O `main.py` sobe o servidor UDP, os probes simulados automaticamente em background e abre o menu de administração no mesmo terminal.
 
### Alternativa: 3 terminais separados
 
Útil para ver os logs e comprovar o isolamento da rede via UDP.
 
```bash
# Terminal 1 — Servidor UDP
cd APS2
python3 -m server.server
```
 
```bash
# Terminal 2 — Probes disparando pacotes
cd APS2
python3 -m probe.demo_probes --count 8 --interval 4
```
 
```bash
# Terminal 3 — Dashboard / Cliente administrador
cd APS2
python3 -m admin.admin
```
 
---
 
## 📡 Protocolo de Comunicação (UDP)
 
Todos os pacotes são enviados em datagramas para a porta `9999`. Não há handshake. O papel e a ação são definidos diretamente no pacote JSON.
 
### Amostra de Telemetria (Probe)
 
Como não há conexão mantida, os metadados do serviço viajam junto com a amostra em todo datagrama:
 
```json
{
  "role": "probe",
  "service_id": "api-gw",
  "name": "API Gateway",
  "host": "10.0.0.1:80",
  "tags": ["prod"],
  "type": "SAMPLE",
  "status": "UP",
  "latency_ms": 42.3,
  "cpu_pct": 35.2,
  "mem_pct": 61.5
}
```
 
### Comandos de Administração
 
O admin envia datagramas com solicitações pontuais:
 
```json
{ "role": "admin", "cmd": "STATUS|api-gw" }
```
 
| Comando UDP       | Descrição                                      |
|-------------------|------------------------------------------------|
| `STATUS`          | Estado atual de todos os serviços na memória   |
| `STATUS\|id`      | Estado detalhado de um serviço                 |
| `SUMMARY`         | Contadores globais + health score              |
| `HISTORY\|id[n]`  | Últimas N amostras gravadas                    |
| `LIST`            | IDs de todos os probes conhecidos              |
| `PING`            | Verificação de disponibilidade da porta        |
 
---
 
## 🔒 Concorrência
 
Mesmo sem múltiplas threads de conexão TCP, o sistema utiliza controle de concorrência. O `ServiceRegistry` usa `threading.RLock` (re-entrante) para proteger a memória global contra colisões entre a thread que recebe os datagramas UDP e a thread daemon de limpeza (`cleanup_loop`) que verifica os timeouts.
 
---
 
## 🧪 Teste Rápido
 
```bash
cd APS2
python3 main.py
```