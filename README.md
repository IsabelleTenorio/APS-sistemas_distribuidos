# 📡 Dashboard de Saúde de Microsserviços

Sistema **distribuído cliente-servidor via Socket TCP** para monitoramento contínuo de status (Uptime, Latência, CPU, Memória) de múltiplos microsserviços.  
Desenvolvido como parte de uma APS da disciplina **CIN0143 – Introdução aos Sistemas Distribuídos e Redes de Computadores** pela **Equipe 6**, composta por: **Eduarda Rodrigues, Elinaldo Emanoel, Gabriel Sousa, Isabelle Tenório**.

---

## 📁 Estrutura do Projeto

```
APS-sistemas_distribuidos/
├── server/
│   ├── registry.py      # Estrutura de dados em memória (sem rede)
│   ├── handlers.py      # Lógica das conexões TCP (probe e admin)
│   └── server.py        # Ponto de entrada: aceita conexões e despacha
│
├── probe/
│   ├── metrics.py       # Coleta latência TCP, CPU e memória (sem rede)
│   ├── agent.py         # Loop TCP persistente com reconexão automática
│   ├── probe.py         # Ponto de entrada: CLI → ProbeAgent
│   └── demo_probes.py   # Demo: N probes simulados em threads
│
├── admin/
│   ├── colors.py        # Constantes ANSI e helpers de formatação
│   ├── renderer.py      # Desenho do dashboard no terminal (sem rede)
│   ├── client.py        # Conexão TCP com o servidor (sem UI)
│   └── admin.py         # Ponto de entrada: menu → client + renderer
│
└── docs/
    └── protocol.md      # Documentação do protocolo TCP
```

Cada arquivo tem **menos de 150 linhas** e **uma única responsabilidade**.

---

## ✨ Funcionalidades

- **Probes persistentes** — conexão TCP aberta, envio a cada N segundos, reconexão automática
- **Agregação em memória** — histórico circular das últimas 60 amostras por serviço (`deque`)
- **Cliente administrador** — dashboard ao vivo (modo `WATCH`) e consultas pontuais
- **Múltiplas conexões simultâneas** — thread daemon por conexão, despacho por `role`
- **Mesma porta para probes e admins** — o primeiro pacote JSON define o papel

---

## 🚀 Como Rodar

### Pré-requisitos

- Python **3.10+** — sem dependências externas
- `psutil` opcional (métricas reais de CPU/RAM):
  ```bash
  pip install psutil
  ```

> ⚠️ Todos os comandos abaixo devem ser executados a partir da pasta raiz `APS-sistemas_distribuidos/`.  
> O prefixo `-m` é necessário porque os módulos usam importações relativas.

---

### Terminal 1 — Servidor

```bash
cd APS-sistemas_distribuidos
python -m server.server
```

---

### Terminal 2 — Probes simulados (demo)

```bash
cd APS-sistemas_distribuidos
python -m probe.demo_probes --count 8 --interval 4
```

Ou um probe real monitorando um serviço específico:

```bash
cd APS-sistemas_distribuidos
python -m probe.probe --id api-gateway --name "API Gateway" \
    --target 127.0.0.1 --target-port 80 --interval 5 --tags prod,backend
```

---

### Terminal 3 — Cliente administrador

```bash
cd APS-sistemas_distribuidos

# Menu interativo
python -m admin.admin

# Dashboard ao vivo direto
python -m admin.admin --watch --interval 3
```

---

## 📡 Protocolo de Comunicação

Todos os agentes conectam na **mesma porta 9999**. O papel é definido pelo **primeiro pacote JSON**.

### Identificação de role

**Probe:**
```json
{ "role": "probe", "service_id": "api-gw", "name": "API Gateway", "host": "10.0.0.1:80", "tags": ["prod"] }
```

**Admin:**
```json
{ "role": "admin" }
```

### Amostras do Probe

```json
{ "type": "SAMPLE", "status": "UP", "latency_ms": 42.3, "cpu_pct": 35.2, "mem_pct": 61.5 }
```

### Comandos Admin

| Comando | Descrição |
|---|---|
| `STATUS` | Estado de todos os serviços |
| `STATUS\|id` | Estado de um serviço |
| `SUMMARY` | Contadores globais + health score |
| `HISTORY\|id[|n]` | Últimas N amostras |
| `LIST` | IDs de todos os probes |
| `WATCH[|segundos]` | Push automático periódico |
| `PING` | Verificação de conectividade |

---

## 🔒 Concorrência

O `ServiceRegistry` usa `threading.RLock` (re-entrante) em todas as operações.  
Cada conexão TCP roda em uma **thread daemon** independente.

```
Thread-1  (Probe: api-gateway)  →  registry.record_sample()  →  RLock
Thread-2  (Probe: auth-service) →  registry.record_sample()  →  RLock
Thread-3  (Admin: watch)        →  registry.snapshot()        →  RLock
```

---

## 🧪 Teste rápido

```bash
# Terminal 1
cd APS-sistemas_distribuidos
python -m server.server

# Terminal 2
cd APS-sistemas_distribuidos
python -m probe.demo_probes --count 8

# Terminal 3
cd APS-sistemas_distribuidos
python -m admin.admin --watch --interval 3
```

---
