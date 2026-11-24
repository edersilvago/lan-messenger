# LAN Messenger (MVP P2P) - Windows, sem servidor

Esqueleto funcional estilo clássico LAN Messenger: discovery via UDP broadcast,
chat via TCP direto e arquivos via TCP separado. Histórico local em SQLite.

## Estrutura

```
lan_messenger/
  config.py         portas, beacon, IPs locais
  protocol.py       framing JSON (4 bytes len + payload)
  networks.py       faixas de transmissão p/ VPN (igual tela Rede)
  networks.json     faixas salvas (ex 10.0.0.1-10.0.0.254)
  profile.py        Meus Dados + Geral (profile.json/settings.json)
  roster.py         agrupamento por departamento + presença
  test_roster.py       teste grupos + perfil
  discovery.py      beacon UDP 50000 + unicast dirigido p/ VPN + lista de peers
  chat.py           servidor TCP 50001 + send_message/broadcast
  files.py          servidor TCP 50002 + send_file chunked + sha256
  store.py          SQLite (lan_history.db) + busca
  logger.py         Log em TXT (single/per_user, telas Log)
  sfx.py            Sons via winsound + parse de hotkey (telas Sons/Atalhos)
  test_transfer_log.py teste aceite/recusa + log
  test_sounds_shortcuts.py teste sons + atalhos
  mass.py           Enviar Mensagem em Massa (checkboxes por grupo)
  history_view.py   Visualizador do Histórico (busca + exportar TXT)
  test_history.py      teste peers + busca
  app_cli.py        CLI p/ teste rápido
  app_gui.py        GUI CustomTkinter (janelas, balões, diálogos)
  test_two_instances.py  teste 2 peers no mesmo PC
  test_vpn_ranges.py     teste faixas + discovery unicast (VPN)
firewall.cmd        libera portas no Firewall do Windows
```

## Rodar (2 PCs na mesma LAN)

1. Executar `firewall.cmd` como Administrador em cada PC.
2. PC-A e PC-B:
```
python -m lan_messenger.app_gui
```
ou via terminal:
```
python -m lan_messenger.app_cli --name PC-JEAN
```
3. Se o broadcast UDP for bloqueado pelo switch/VLAN, use IP manual:
```
python -m lan_messenger.app_cli --name PC-JEAN --add-peer 192.168.1.20
```
(botão "+ IP manual" na GUI faz o mesmo)

## Teste local (1 PC, 2 instâncias simuladas)

```
python -m lan_messenger.test_two_instances
python -m lan_messenger.test_vpn_ranges
```
Esperado: `OK msg`, `OK file`, `PASSOU` em ambos.

## VPN unindo 2 redes (ex 10.0.0.x + 192.168.30.x) - igual tela Rede

O broadcast limitado NÃO atravessa roteador/VPN. Por isso o Discovery envia
beacon UDP **unicast para cada IP das faixas** + broadcast dirigido (.255).
O chat/arquivo (TCP direto) já cruza a VPN se houver rota.

1. Confira que há ping entre as redes: `ping 192.168.30.10` a partir da 10.0.0.x.
2. Em cada PC, cadastre as duas faixas (GUI: botão **Rede (VPN)...**):
   - `10.0.0.1-10.0.0.254`
   - `192.168.30.1-192.168.30.254`
   (já vêm prontas em `lan_messenger/networks.json`; via CLI: `/addrange 10.0.0.1-10.0.0.254`)
3. Execute `firewall.cmd` como Admin **nos dois lados**. Se a VPN aparecer como
   rede Pública no Windows, libere também no perfil público ou reclassifique a
   VPN como Privada/Domínio. Portas: UDP 50000 entrando nos dois lados + TCP
   50001/50002.
4. Se o firewall da VPN/roteador filtrar UDP, o plano B continua funcionando:
   botão **+ IP manual** (ou `--add-peer`) + TCP direto.

Checklist de falha típica: sem rota entre sub-redes / UDP 50000 bloqueado no
túnel / firewall com perfil Público / faixas digitadas erradas (`/ranges` mostra).

## Portas

| Serviço   | Proto | Porta |
|-----------|-------|-------|
| Discovery | UDP   | 50000 |
| Chat      | TCP   | 50001 |
| Arquivos  | TCP   | 50002 |

## Segurança (PSK AES-256-GCM)

1. Em um PC: 🌐 Rede → `Gerar` → `Salvar` (cadeado 🔒 aparece na statusbar).
2. Distribua o **mesmo valor** aos demais PCs (cole no campo e Salvar).
3. Cobertura: texto do chat + blocos de arquivo. **Em claro:** beacons
   (presença/nome/departamento) e header de arquivo (nome/tamanho).
4. Sem chave ou com chave divergente, o par não se entende (falha limpa,
   sem travar). CLI: `python -m lan_messenger.app_cli --key <base64>`.
5. Requer `pip install -r lan_messenger/requirements.txt` (cryptography).

## Bandeja, autostart e .exe

- Fechar a janela minimiza p/ bandeja (balão + ponto vermelho em não lidas;
  menu: Abrir, Online/Ausente, Sair). Requer pystray+Pillow (ver acima).
- Segunda cópia não abre: avisa "já está em execução" e sai (trava 127.0.0.1:50009).
- ⚙ Geral → `Iniciar com o Windows` grava HKCU `...\Run\LANMessenger`.
- Build: `lan_messenger\build_exe.cmd` (PyInstaller onefile, sem console)
  gera `dist\LANMessenger.exe`. Entrada: `python -m lan_messenger`.

## Instaladores v1.24 (2 PCs)

- `installer\Setup_LANMessenger_win10_11.exe` (~24MB): Windows 10/11,
  build moderno (Python 3.13). Requer Win10+.
- `installer\Setup_LANMessenger_win7_81.exe` (~17MB): Windows 7 SP1 / 8 / 8.1,
  build dedicado (Python 3.8). Tudo embutido, sem Python na máquina.
- Ambos instalam em `Program Files\LANMessenger` (exe + `app.ico` +
  `assets\*.png` + guia), criam atalhos com o ícone de balões, liberam o
  firewall (UDP 50000, TCP 50001/50002) e removem tudo no uninstall.
  Scripts: `lan_messenger\installer_win10_11.iss` e `installer_win7_81.iss`.
- Barra principal = atalhos com ícones e balão de dica: Conversa, Massa,
  📁 Recebidos, 📜 Histórico, Meus Dados, Rede, ⚙ Config, ❓ Ajuda e Sobre.
  Conversas usam o ícone Conversa, botões Enviar/Fechar padronizados e
  piscam na barra ao chegar mensagem sem foco (FlashWindowEx).
  Lista: ícone User nos usuários, User Group nos grupos; clique abre a
  conversa; botão direito tem os menus clássicos (mover de grupo,
  ver informações, atualizar, novo grupo, ocultar offline).
- Tray usa o `app.ico` oficial (ponto vermelho = não lida); duplo-clique
  abre a principal. Tray fica visível mesmo com a janela aberta, com menu
  de status (Disponível/Ocupado/Ausente).
- Rodapé da principal: botões de status (manual não volta sozinho).
- Roteiro de teste nos 2 PCs: `lan_messenger\LEIA-ME-TESTE.txt`
  (acompanha os instaladores).

## Presença e fidelidade da lista (v1.11)

- Beacon UDP a cada 4s (unicast por faixa p/ cruzar a VPN + broadcast
  local); timeout de 60s (tolera perda de UDP no túnel); aviso de saída
  imediato (fechar o app marca offline nos colegas na hora).
- "Sinal fraco" = online sem beacon há +20s (lista mostra ao lado do nome
  e na barra); não some da lista, só avisa.
- Lista só redesenha quando muda (sem piscar a cada 3s); sonda UDP
  automática a cada ~12s + "Atualizar Lista de Usuários" força na hora.
- Ver Informações mostra "Visto há" (idade do último beacon).
- Envio 1-1 com trava anti-offline: destino offline pede confirmação
  (P2P não tem fila); par "sinal fraco" é checado no TCP antes; falha de
  envio marca o contato offline na hora e avisa (ninguém espera resposta
  à toa). Diagnóstico na tela Rede (escuta UDP, último recebido, Testar
  IP) + `+ IP manual` como plano B se a VPN filtrar UDP.

## Histórico, status e Sobre (v1.12)

- Botão de histórico no topo da conversa abre o Visualizador já filtrado
  naquele contato.
- Rodapé Disponível aplica direto; Ocupado/Ausente abrem a Mensagem de
  status com contagem de 10s ("Definir Status [10]" confirma sozinho).
  A mensagem viaja no beacon e aparece para os colegas.
- Sobre traz o versículo de Mateus 7, 24.
- Exe com versão embutida: botão direito > Propriedades > Detalhes mostra
  a mesma versão da tela Sobre (gerada do `config.APP_VERSION` no build).

## Status colorido e setups versionados (v1.13)

- Botões do rodapé cada um na cor do seu status (verde/vermelho/amarelo).
- Nomes dos instaladores com a versão:
  `Setup_LANMessenger_win10_11_v1.13.exe` e
  `Setup_LANMessenger_win7_81_v1.13.exe`.

## Presença via TCP (v1.14)

- Queda da VPN não exige mais reiniciar: a cada ~10s o app confirma por
  TCP (porta do chat) os colegas "sinal fraco" e os conhecidos offline;
  quem responde volta para a lista sozinho, com dados frescos.
- Cache de colegas em `%APPDATA%\LANMessenger\peers_cache.json`: ao abrir,
  os colegas da última sessão são procurados na hora (UDP + TCP).
- "Sinal fraco" agora só aparece quando nem UDP nem TCP alcançam o colega
  — se o TCP passa, a lista fica limpa como esperado.

## Conversa em balões (v1.15)

- Recebidas à esquerda (cinza), enviadas à direita (azul), com carimbo
  de data/hora embaixo de cada mensagem e nome do remetente no grupo.
- Vale para conversa 1-1, grupo e histórico recente; tamanho da fonte
  acompanha Config > Mensagens.

## Balões WhatsApp + anexos em cartão (v1.16)

- Enviadas em verde `#D9FDD3` à direita, recebidas em branco à esquerda,
  texto `#202124`, horário discreto `#667085` dentro do balão.
- Tique único cinza nas enviadas = entregue no app do colega (há ACK por
  mensagem; sem tique azul: o sistema não informa leitura).
- Separadores de data ("14 de outubro de 2026") agrupando o histórico.
- Anexos em cartão: selo da extensão, nome, pasta/tamanho, hora e botão
  "Abrir pasta" (mesma ação de antes; caminho não vira link).

## Temas e ajustes CTk (v1.18)

- Conversas abrem centralizadas e no fim do histórico (última mensagem).
- Contatos com a cor do status de volta; botão da pasta de recebidos na
  conversa; barra do chat compacta (nada oculta ao redimensionar).
- Tema Light/Dark/System em Config > Geral (aplica na hora, vale para
  balões, lista e diálogos).

## Centralização, status e versão do colega (v1.19)

- Conversas centralizam também ao aparecer (tamanho real pós-layout);
  Histórico centralizado pela geometria.
- Diálogo Ocupado/Ausente com botões fixos no rodapé e texto em negrito.
- Grupos em branco no modo Dark; Informações mostra a versão do LAN
  Messenger do contato.

## Linha de status e relógio (v1.20)

- Mensagem de status em linha própria em negrito (não espreme os botões);
  branca no Dark.
- Status em português em tudo ([ocupado], [ausente], Informações);
  "Visto há" nunca negativo (relógio do colega adiantado).
- Balões com HH:MM:SS; tray sem o item duplicado Online/Ausente.

## Carimbo sempre visível (v1.21)

- Balões mostram HH:MM:SS sempre (antes sumia com a opção de data);
  a opção passa a ocultar só as pílulas de data.

## Cartão de anexo e histórico de arquivos (v1.22)

- Cartão tamanho de balão de texto (largura fixa, sem texto vertical):
  selo da extensão + nome com extensão + hora + "Abrir pasta".
- Arquivos enviados/recebidos entram no histórico da conversa com nome
  completo e extensão.

## Menu principal e inbox por remetente (v1.23)

- Botão direito na principal volta a abrir o menu (Atualizar, Novo
  Grupo, Massa, Ocultar offline); nos grupos abre o menu do grupo.
- Recebidos em `inbox/<Nome do remetente>/` (organizado por contato).

## Emojis e eu na lista (v1.24)

- Botão 😊 nas conversas (1-1 e grupo) abre a grade de emojis (vale
  Win+. também).
- Você aparece na lista como contato ("(você)"); a conversa própria
  funciona como anotações (loopback real, vai p/ o histórico).
- Chamadas de worker p/ UI via fila thread-safe (sem travar).

## Responder mensagem específica (v1.30)

- Botão direito em qualquer balão → "Responder" (1-1).
- Prévia acima do campo de texto: "Respondendo a <nome>" + trecho; ✕
  cancela. Enter envia normalmente.
- O balão enviado mostra a citação no topo: barra verde, nome do autor
  e trecho (estilo WhatsApp). Quem recebe vê a mesma citação; ao reabrir
  a conversa, o histórico mantém.
- Campo novo `reply` na mensagem: versões antigas ignoram (retro-
  compatível). Grupo ainda não usa.

## Fila para contato offline (v1.29)

- Enviar para quem está offline não abre mais aviso: a mensagem entra na
  fila local (SQLite, tabela `outbox`) e aparece no balão como
  `HH:MM:SS (pendente)`.
- O app tenta entregar a cada 10s e ao voltar o contato para a lista; ao
  receber o ACK, a marca vira `HH:MM:SS ✓` e o rodapé avisa.
- Vale também para falha de envio (TCP sem resposta): a mensagem não é
  perdida, fica pendente.
- Limite honesto: o remetente precisa estar com o app aberto quando o
  destinatário voltar. Sem servidor, não há entrega com os dois desligados.

## Log de erros do aplicativo (v1.28)

- Falhas internas (callbacks da interface, threads de rede/arquivos e
  exceções não tratadas) são gravadas em
  `%APPDATA%\LANMessenger\logs\crash.log`, com data, hora, contexto e
  traceback completo.
- O diálogo "Application Error" do Tk foi substituído por um aviso curto
  na barra de status; o app continua funcionando.
- Config > Log > "Abrir pasta do log de erros" abre a pasta no Explorer
  para enviar o arquivo ao suporte.
- Nenhuma regra de negócio, protocolo, socket ou banco foi alterada.

## Links clicáveis nas mensagens (v1.27)

- Links `http://`, `https://` e `www.` dentro das mensagens aparecem em
  azul sublinhado e abrem no navegador ao clicar; pontuação final da
  frase não entra no link. Balões sem link seguem idênticos.

## Toast e menções (v1.26)

- **Notificações do sistema (toast)** — mensagens recebidas avisam por
  toast do Windows (Win10/11), com clique que traz o app para frente;
  no Win7/8.1 segue o balão da bandeja. Opção em Config > Mensagens
  ("Notificações do sistema").
- **Menções @nome na conversa em grupo** — escreva `@NomeDoColega` (sem
  acento/caixa exatos, aceita nome de exibição ou usuário); quem é
  mencionado vê o balão destacado ("— mencionou você") e recebe toast
  "Você foi mencionado" quando a janela do grupo está em segundo plano.
- **Link do projeto** — Ajuda (seção 9. PROJETO) e tela Sobre agora
  mostram o repositório do projeto (clicável no Sobre).

## Limpeza de referências de terceiros (v1.25)

- Remoção de toda menção a marca de terceiros de mensagens
  exibidas ao usuário e de comentários/docstrings; nenhum comportamento,
  protocolo, visual ou regra de negócio foi alterado.

## Histórico de versões

- v1.0/v1.1: base P2P estilo clássico — descoberta UDP, chat TCP direto,
  arquivos com sha256, presença, histórico local SQLite, instaladores.
- v1.2: descoberta imediata (sonda ping ao abrir), firewall em todos os
  perfis, instalador idempotente (remove regras antes de criar).
- v1.3: Ping no contato; massa com checkboxes por grupo; menu de grupo
  (mensagem p/ o grupo, conversa em grupo, renomear, novo, apagar, mover);
  grupo padrão Geral; arrastar/soltar arquivos; progresso com Cancelar e
  "Abrir pasta" no recebimento.
- v1.4: lembra posição/tamanho das janelas; Ping abre CMD com 5 disparos;
  IDs AnyDesk/RustDesk + conectar pelo menu; instalador fecha versão
  aberta; conversa sempre vem à frente em nova mensagem.
- v1.5: fechamento forçado no update (taskkill); massa fiel via botão
  direito no grupo; auto-detecção dos IDs; "Abrir pasta" no log; contato
  do suporte no Sobre.
- v1.6: grupo não recolhe sozinho; "Abrir pasta" clicável; conversas
  abrem em 650x620 (mínimo 620x560).
- v1.7: "Abrir pasta" abre a inbox; massa responsiva (mínimo 760x460);
  sons WAV de notificação; janelas com tamanho mínimo.
- v1.8: ícone no tray com a janela aberta; botões de status no rodapé e
  no menu do tray (manual não volta sozinho).
- v1.9: hardware do contato (CPU/RAM/disco); cores de status na lista;
  Ctrl+V envia print; janelas centralizadas; atalhos AnyDesk/RustDesk/Info
  na conversa.
- v1.10: centralização no desktop; marcadores compatíveis com Win7;
  Sistema Operacional com build/versão nas Informações.
- v1.11: presença estável (beacon 4s, timeout 60s, aviso de saída, "sinal
  fraco", "Visto há", lista sem piscar, trava anti-offline); Minhas
  Informações com OK sempre visível; Ajuda completa.
- v1.12: histórico na conversa; status com regressiva; versículo no
  Sobre; versão embutida no exe.
- v1.13: botões de status coloridos; setups com versão no nome.
- v1.14: presença via TCP (lista volta sozinha após queda da VPN, sem
  reiniciar; cache de colegas para recuperação rápida).
- v1.15: conversa em balões (recebidas à esquerda, enviadas à direita,
  com data/hora embaixo).
- v1.16: balões WhatsApp (verde/branco, hora dentro, tique de entregue),
  separadores de data e anexos em cartão.
- v1.17: visual reconstruído em CustomTkinter (balões arredondados de
  verdade, botões e diálogos modernos; backend inalterado).
- v1.18: centralização e fim do histórico corrigidos, cores de status na
  lista, botão da pasta no chat, barra responsiva e temas Light/Dark.
- v1.19: centralização pós-layout, status com botões fixos, grupos
  brancos no Dark e versão do colega nas Informações.
- v1.20: status em linha própria, tudo em português, HH:MM:SS nos
  balões e tray sem duplicata.
- v1.21: carimbo HH:MM:SS sempre visível no balão.
- v1.22: cartão de anexo tamanho de balão + arquivos no histórico.
- v1.23: menu de botão direito na principal + inbox por remetente.
- v1.24: emojis nas conversas + eu na lista (anotações).
- v1.25: limpeza de referências a marca de terceiros (mensagens e
  comentários internos); sem mudança de comportamento.
- v1.26: toast (Win10/11), menções @nome no grupo e link do projeto no
  Ajuda/Sobre.
- v1.27: links http(s)/www. nas mensagens viram clicáveis no balão.
- v1.28: log de erros em `logs\crash.log` (data, hora e traceback), aviso
  no rodapé em vez de diálogo e botão para abrir a pasta do log.
- v1.29: mensagem para contato offline fica na fila local e é entregue
  sozinha quando ele aparece online (marca "(pendente)" vira tique).
- v1.30: responder mensagem específica — citação no balão (barra verde,
  autor + trecho) e prévia acima do campo de texto.

## Limites do P2P puro (por arquitetura, não por falta)

- Sem entrega garantida: a fila local guarda mensagens para contatos
  offline, mas só entrega se o remetente estiver com o app aberto quando
  o destinatário voltar (sem servidor, nada chega com os dois desligados).
- Beacons (presença/nome/departamento) e nomes de arquivo seguem visíveis;
  texto do chat e blocos de arquivo usam PSK AES-256-GCM quando há chave.

## Próximos passos sugeridos

1. AES-PSK nas mensagens + TLS nos arquivos.
2. Grupos + menções + notificações toast Windows (`win10toast` ou PySide6).
3. Build `PyInstaller --onefile --windowed` + autostart em `HKCU\...\Run`.
