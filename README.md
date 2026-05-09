# 📡 Dashboard de Saúde de Microsserviços

Sistema **distribuído cliente-servidor via Socket TCP** para monitoramento contínuo de status (Uptime, Latência, CPU, Memória) de múltiplos microsserviços.  
Desenvolvido como parte de uma APS da disciplina **CIN0143 – Introdução aos Sistemas Distribuídos e Redes de Computadores** pela **Equipe 6**, composta por: **Eduarda Rodrigues, Elinaldo Emanoel, Gabriel Sousa, Isabelle Tenório**.

---

## 📁 Estrutura do Projeto
 
```
APS-sistemas_distribuidos/
├── main.py              # Ponto de entrada único — roda tudo em 1 terminal
├── server/
│   ├── registry.py      # Estrutura de dados em memória (sem rede)
│   ├── handlers.py      # Lógica das conexões TCP (probe e admin)
│   └── server.py        # Aceita conexões e despacha
│
├── probe/
│   └── demo_probes.py   # Probes simulados em threads
│
├── admin/
│   ├── colors.py        # Constantes ANSI e helpers de formatação
│   ├── renderer.py      # Desenho do dashboard no terminal (sem rede)
│   ├── client.py        # Conexão TCP com o servidor (sem UI)
│   └── admin.py         # Menu de administração
│
└── docs/
    └── protocol.md      # Documentação do protocolo TCP
```
 
Cada arquivo tem **menos de 200 linhas** e **uma única responsabilidade**.
 
---
 
## ✨ Funcionalidades
 
- **Probes simulados** — múltiplos probes em threads, cada um com métricas geradas com variação realista
- **Agregação em memória** — histórico circular das últimas 60 amostras por serviço (`deque`)
- **Cliente administrador** — dashboard ao vivo (modo `WATCH`) e consultas pontuais
- **Múltiplas conexões simultâneas** — thread daemon por conexão, despacho por `role`
- **Mesma porta para probes e admins** — o primeiro pacote JSON define o papel
---
 
## 🚀 Como Rodar
 
### Pré-requisitos
 
- Python **3.10+** — sem dependências externas, apenas biblioteca padrão
> ⚠️ Todos os comandos abaixo devem ser executados a partir da pasta raiz `APS-sistemas_distribuidos/`.  
> O prefixo `-m` é necessário porque os módulos usam importações relativas.
 
---
 
### Terminal único
 
```bash
cd APS-sistemas_distribuidos
python main.py
```
 
O `main.py` sobe o servidor e os probes simulados automaticamente em background e abre o menu de administração no mesmo terminal.
 
---
 
### Alternativa: 3 terminais separados
 
Útil se quiser ver os logs de cada componente individualmente.
 
```bash
# Terminal 1 — servidor
cd APS-sistemas_distribuidos
python -m server.server
```
 
```bash
# Terminal 2 — probes simulados
cd APS-sistemas_distribuidos
python -m probe.demo_probes --count 8 --interval 4
```
 
```bash
# Terminal 3 — cliente administrador
cd APS-sistemas_distribuidos
python -m admin.admin
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
| `HISTORY\|id[n]` | Últimas N amostras |
| `LIST` | IDs de todos os probes |
| `WATCH[segundos]` | Push automático periódico |
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
cd APS-sistemas_distribuidos
python main.py
```
 
---
