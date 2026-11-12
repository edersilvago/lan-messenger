# Arquitetura

LAN Messenger é um sistema **P2P puro para Windows**: nenhuma mensagem passa por servidor. Cada instância é ao mesmo tempo cliente e servidor (descoberta, chat, arquivos e presença), e tudo se resolve por TCP/UDP direto entre os PCs — na mesma LAN ou atravessando uma VPN que una duas redes.

```
┌────────────────────────────── PC A ─────────────────────────────┐
│  app_gui.py (CustomTkinter)                                     │
│    ├─ fila thread-safe (_ui_call/_pump_ui, 100 ms)              │
│    ├─ roster.py  (grupos por departamento + presença)           │
│    ├─ chatview.py (balões, cartões de anexo, separadores)       │
│    └─ history_view.py / mass.py / profile.py / settings         │
│                                                                 │
│  backend (sem GUI):                                             │
│    ├─ discovery.py  → UDP 50000 (beacon 4s + unicast por faixa) │
│    ├─ chat.py       → TCP 50001 (frames JSON, ACK por mensagem) │
│    ├─ files.py      → TCP 50002 (chunks 64KB + sha256)          │
│    ├─ crypto.py     → AES-256-GCM (PSK)                         │
│    └─ store.py      → SQLite lan_history.db                     │
└──────────────────────────── TCP / UDP ─────────────────────────┘
                             │
┌────────────────────────────── PC B ─────────────────────────────┐
│  mesmos módulos, papéis invertidos                              │
└─────────────────────────────────────────────────────────────────┘
```

## Portas

| Serviço | Proto | Porta | Observação |
|---|---|---|---|
| Descoberta | UDP | 50000 | beacon + resposta; nunca criptografado |
| Chat | TCP | 50001 | frames JSON; texto selado quando há PSK |
| Arquivos | TCP | 50002 | header em claro, blocos selados |
| Lock de instância | TCP | 50009 | só localhost; garante 1 cópia por PC |

## Descoberta e presença (`discovery.py`)

1. **Beacon UDP a cada 4s** — JSON `{"type":"beacon", name, user, status, display, dept, role, anydesk, rustdesk, cpu, ram, disk, os, status_msg, app_version, ts}`. Também serve de "estou vivo".
2. **Unicast por faixa + broadcast dirigido** — broadcast limitado não atravessa roteador/VPN. Para VPN (ex.: `10.0.0.x` + `192.168.30.x`), o beacon vai em unicast para cada IP de cada faixa cadastrada (tela Rede) e em broadcast dirigido `x.y.z.255`.
3. **Timeout 60s** — tolera perda de UDP no túnel; "sinal fraco" quem está +20s sem beacon.
4. **Reforço via TCP (v1.14)** — a cada ~10s o app pergunta por TCP 50001 os colegas "sinal fraco" e os conhecidos offline (`hello`); quem responde volta à lista com dados frescos. É o plano B quando a VPN filtra UDP.
5. **Cache de colegas** — `peers_cache.json` em `%APPDATA%\LANMessenger`: ao abrir, procura a última sessão na hora (UDP + TCP).
6. **Saída imediata** — fechar o app marca o contato offline nos colegas na hora.

## Protocolo de chat (`protocol.py`)

- **Framing length-prefixed**: 4 bytes big-endian com o tamanho + payload JSON (UTF-8). Limite de 50 MB por frame (proteção contra frame malformado).
- **ACK por mensagem**: o receptor confirma entrega — origem do tique cinza único nos balões. O sistema **não** informa leitura (não há tique azul).
- **Sem fila de offline**: destino inalcançável → trava anti-offline pede confirmação antes de enviar; falha marca o contato offline e avisa.

## Arquivos (`files.py`)

- Transferência por TCP 50002 em blocos de 64 KB, com **sha256** de verificação e progresso cancelável.
- **Header em claro** (nome/tamanho visíveis na rede); blocos selados quando há PSK.
- Recebidos em `%APPDATA%\LANMessenger\inbox\<Remetente>\`.

## Criptografia (`crypto.py`)

Modelo PSK (pre-shared key): a mesma chave de 32 bytes (base64, AES-256-GCM) cadastrada na tela Rede de **todos** os PCs.

| Tráfego | Proteção |
|---|---|
| Texto do chat | selado — nonce aleatório por mensagem |
| Blocos de arquivo (64 KB) | selados — nonce = `sha256(file_id)[:8]` + contador |
| Header de arquivo | **em claro** (nome/tamanho) |
| Beacons de descoberta | **em claro** (presença/nome/departamento) |

- Chave gerada em `Gerar` (32 bytes de `os.urandom`) e distribuída por export/import de `lan-chave.key` ou colagem manual.
- Sem chave (ou chave divergente): tráfego em claro ou falha limpa de decodificação — sem travar; statusbar mostra cadeado 🔒 quando ativa.
- Requer `cryptography` (`requirements.txt`).

## Persistência (`store.py`) e dados locais

- Histórico em **SQLite** (`lan_history.db`): mensagens 1-1, grupo, arquivos enviados/recebidos; busca + export TXT no Visualizador.
- Tudo em `%APPDATA%\LANMessenger` quando empacotado (`config.app_data_dir()`); em dev, na própria pasta do pacote.

## Interface (`app_gui.py`, CustomTkinter)

- Reconstruída em **CustomTkinter** sobre Tkinter (v1.17); backend inalterado desde então.
- **Fila thread-safe para UI**: workers (chat, arquivos, discovery, som) nunca chamam Tk direto — passam por `_ui_call()` para uma fila consumida por `_pump_ui()` a cada 100 ms, evitando `root.after` fora da thread principal.
- Balões: CTkFrame com cantos arredondados; horário dentro do balão `HH:MM:SS`; separadores de data; cartão de anexo com largura fixa (`CARD_WIDTH = 360`) e wrap manual (o `wraplength` do CTkLabel é instável).
- Temas Light/Dark/System via cores `(light, dark)` do CustomTkinter.
- Janelas centralizadas no desktop, dimensionamento responsivo, botões nunca ocultos.

## Instância única e tray

- **Lock**: segunda cópia escuta `127.0.0.1:50009` e sai com aviso.
- **Tray** (`tray.py`, pystray + Pillow): fechar a janela minimiza; ponto vermelho = não lidas; menu Disponível/Ocupado/Ausente + Sair.
- **Autostart** (`autostart.py`): grava `HKCU\...\Run\LANMessenger`.

## Módulos auxiliares

| Módulo | Papel |
|---|---|
| `roster.py` | agrupamento por departamento + grupos manuais + presença agregada |
| `mass.py` | mensagem em massa com checkboxes por grupo |
| `history_view.py` | visualizador do histórico com busca e export TXT |
| `logger.py` | log TXT single/per-user |
| `sfx.py` | sons via winsound + parse de hotkey |
| `sysinfo.py` | CPU/RAM/disco/OS do contato (vai no beacon) |
| `remote.py` | AnyDesk/RustDesk: auto-detecção de IDs e conexão pelo menu |
| `networks.py` | faixas de transmissão da VPN (parse `a.b.c.1-a.b.c.254`) |
| `app_cli.py` | CLI para teste rápido (`--name`, `--add-peer`, `--key`) |
