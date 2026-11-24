# Histórico de versões

Versão atual: **v1.35**. Cada versão traz mudanças visíveis ao usuário; o backend só foi reconstruído visualmente em v1.17 (CustomTkinter), sem alterar protocolo nem regras.

## v1.0 / v1.1 — base P2P estilo clássico
- Descoberta UDP, chat TCP direto, arquivos com sha256, presença, histórico local SQLite, instaladores.

## v1.2 — descoberta imediata
- Sonda ping ao abrir; firewall em todos os perfis; instalador idempotente (remove regras antes de criar).

## v1.3 — grupos e massa
- Ping no contato; massa com checkboxes por grupo; menu de grupo (mensagem para o grupo, conversa em grupo, renomear, novo, apagar, mover); grupo padrão Geral; arrastar/soltar arquivos; progresso com Cancelar e "Abrir pasta" no recebimento.

## v1.4 — AnyDesk/RustDesk
- Lembrança de posição/tamanho das janelas; Ping abre CMD com 5 disparos; IDs AnyDesk/RustDesk + conectar pelo menu; instalador fecha versão aberta; conversa sempre à frente em nova mensagem.

## v1.5 — update seguro
- Fechamento forçado no update (taskkill); massa fiel via botão direito no grupo; auto-detecção dos IDs; "Abrir pasta" no log; contato do suporte no Sobre.

## v1.6 / v1.7 — usabilidade
- Grupo não recolhe sozinho; "Abrir pasta" clicável; conversas 650x620 (mínimo 620x560); sons WAV; janelas com tamanho mínimo; massa responsiva (mínimo 760x460).

## v1.8 — bandeja
- Ícone no tray com a janela aberta; botões de status no rodapé e no menu do tray (manual não volta sozinho).

## v1.9 / v1.10 — informações do contato
- Hardware (CPU/RAM/disco); cores de status na lista; Ctrl+V envia print; janelas centralizadas; atalhos AnyDesk/RustDesk/Info na conversa; marcadores compatíveis com Win7; SO com build/versão nas Informações.

## v1.11 — presença estável
- Beacon 4s, timeout 60s, aviso de saída, "sinal fraco", "Visto há", lista sem piscar, trava anti-offline; Minhas Informações com OK sempre visível; Ajuda completa.

## v1.12 — histórico e status
- Histórico na conversa; status com regressiva (10s); versículo no Sobre; versão embutida no exe (Propriedades > Detalhes).

## v1.13 — identidade visual de status
- Botões de status coloridos (verde/vermelho/amarelo); setups com versão no nome.

## v1.14 — presença via TCP
- Lista volta sozinha após queda da VPN (sem reiniciar): confirmação TCP a cada ~10s; cache de colegas (`peers_cache.json`) para recuperação rápida.

## v1.15 — conversa em balões
- Recebidas à esquerda, enviadas à direita, data/hora embaixo; fonte acompanha Config > Mensagens.

## v1.16 — balões WhatsApp + cartões
- Enviadas em verde, recebidas em branco, hora dentro do balão, tique de entrega, separadores de data, anexos em cartão com "Abrir pasta".

## v1.17 — CustomTkinter
- Visual reconstruído em CustomTkinter (balões arredondados reais, botões e diálogos modernos); backend inalterado.

## v1.18 — temas
- Centralização e fim do histórico corrigidos; cores de status na lista; botão da pasta no chat; barra responsiva; temas Light/Dark/System em Config > Geral.

## v1.19 — refinamentos
- Centralização pós-layout; status com botões fixos no rodapé; grupos brancos no Dark; versão do colega nas Informações.

## v1.20 — status e relógio
- Status em linha própria (não espreme botões); status em português em tudo; HH:MM:SS nos balões; "Visto há" nunca negativo; tray sem duplicata.

## v1.21 — carimbo sempre visível
- Balões mostram HH:MM:SS sempre; opção de data oculta só as pílulas de data.

## v1.22 — cartão e histórico de arquivos
- Cartão de anexo tamanho de balão (largura fixa); arquivos enviados/recebidos entram no histórico com nome completo.

## v1.23 — menus e inbox
- Menu de botão direito na principal (Atualizar, Novo Grupo, Massa, Ocultar offline); recebidos em `inbox/<Remetente>/`.

## v1.35 — tamanho da fonte aplicado à conversa
- Configurações > Mensagens > Tamanho da Fonte agora altera corpo das mensagens, links, autor, citações, horários, datas, avisos do sistema e cartões de anexo.
- A troca aplica imediatamente aos balões já abertos e também às novas mensagens, em conversas 1-1 e em grupo.
- Escala mantida: Normal 9 px, Grande 11 px e Extra grande 13 px; elementos auxiliares acompanham proporcionalmente.
- Testes responsivos cobrem largura mínima de 620 px, notebook 1366 px, Full HD 1920 px e 4K 3840 px.

## v1.34 — proporção completa e histórico sempre visível
- Balões de texto passam de 75% com teto de 1200 px para 94% da largura disponível, sem teto fixo; janela maximizada aproveita quase toda a conversa.
- Citação não depende mais da propagação de tamanho do `CTkFrame` (que mantinha 200 px): altura calculada de 48–80 px para 1–3 linhas, recalculada ao redimensionar.
- Ao abrir ou maximizar, o canvas recalcula o `scrollregion` em duas fases e restaura o fundo ou a posição anterior. Isso evita a conversa em branco.
- `<Configure>` ignora eventos dos widgets filhos, reduzindo reprocessamento e instabilidade de layout.

## v1.33 — correção definitiva da recursão ao abrir conversas
- Removidas todas as chamadas `update_idletasks()` dos callbacks de centralização e rolagem. Elas podiam reexecutar o próprio `after` ativo antes de a trava anterior entrar.
- `center_soon` não usa mais `<Map>` nem `after_idle`: agenda uma única centralização após 80 ms.
- `scroll_end` agenda uma única rolagem após 60 ms e cancela pedido anterior, evitando centenas de callbacks ao carregar histórico.
- Teste de regressão garante que `center_window` não chama `update_idletasks`, e que `center_soon` não registra `<Map>`.

## v1.32 — texto proporcional à janela
- Quebra do balão calculada pela largura real da janela (75%, entre 300 e 1200 px) em vez dos 380 px fixos: janela pequena acompanha a tela; maximizada usa quase toda a linha.
- Ao redimensionar, os balões já abertos requebram sozinhos (debounce de 200 ms, sem laço: só reajusta quando a largura muda).
- Citação da resposta acompanha a mesma proporção (60% da largura do balão).

## v1.31 — ajustes da resposta + correção de travamento
- Duplo-clique na mensagem também abre a resposta (atalho ao lado do botão direito).
- Citação no balão com largura/altura ajustadas: trecho limitado a 140 caracteres com "…", quebra em 220 px, nome até 40 caracteres — balão volta a ficar proporcional ao texto.
- Correção: crash `RecursionError` ao centralizar janelas (`center_window`/`center_soon`): `update_idletasks` reexecutava o callback do `<Map>`; agora há trava de reentrada. `log_crash` também ganhou trava contra recursão.

## v1.30 — responder mensagem específica
- Botão direito em qualquer balão da conversa 1-1 → "Responder": prévia "Respondendo a <nome>" + trecho acima do campo de texto, ✕ cancela.
- O balão enviado ganha citação no topo (barra verde, autor e trecho, estilo WhatsApp); quem recebe vê a mesma citação e o histórico mantém ao reabrir.
- Campo novo `reply` opcional em `protocol.make_msg`/`chat.send_message` (retro-compatível: versões antigas ignoram); citação gravada na tabela `replies` do SQLite.
- Fila offline (v1.29) mantém a citação no reenvio. Grupo fora do escopo desta versão.
- Teste `test_reply.py`.

## v1.29 — fila para contato offline
- Enviar para quem está offline não abre mais aviso de falha: a mensagem é gravada no SQLite (tabela `outbox`) e aparece no balão como `HH:MM:SS (pendente)`.
- Um worker tenta entregar a cada 10s e também logo após o envio; ao receber o ACK, `drop_pending()` limpa a fila e o balão troca `(pendente)` pelo tique ✓ (rodapé avisa).
- Falha de TCP também entra na fila: a mensagem não se perde, fica pendente até o contato responder.
- `chat.send_message(..., msg_id=...)` mantém o id da fila de ponta a ponta; `store.messages_with_ids()` marca o histórico pendente ao reabrir a conversa.
- Limite honesto: o remetente precisa estar com o app aberto quando o destinatário voltar. Sem servidor, não há entrega com os dois desligados.
- Teste `test_outbox.py`.

## v1.28 — log de erros
- Falhas internas passam a ser gravadas em `%APPDATA%\LANMessenger\logs\crash.log` com data, hora, contexto e traceback completo (`log_crash()` em `app_gui.py`).
- O diálogo modal "Application Error" do Tk é substituído por aviso curto na barra de status (`App._install_crash_reporter()`); callbacks `after` (centralização, rolagem, filas de UI/tray/arquivos, anúncio de mensagens) ganharam guarda ampla que registra e segue.
- `__main__.py` instala `sys.excepthook` e `threading.excepthook` para capturar exceções fora da UI (rede, arquivos, descoberta).
- Config > Log > "Abrir pasta do log de erros" abre a pasta no Explorer. Nenhum protocolo, socket, banco ou regra de negócio foi alterado.

## v1.27 — links clicáveis
- Links `http://`/`https://`/`www.` nas mensagens aparecem em azul sublinhado e abrem no navegador ao clicar; pontuação final da frase não entra no link. Balões sem link seguem com um único label (visual inalterado).
- `split_url_segments()`/`open_url()`/`clean_url()` em `app_gui.py`; teste `test_links.py`.

## v1.26 — toast e menções
- Notificações do sistema (toast) no Windows 10/11 para mensagens recebidas — clique na notificação traz o app para frente; Win7/8.1 segue com o balão da bandeja. Opção "Notificações do sistema" em Config > Mensagens.
- Menções na conversa em grupo: `@nome` (aceita nome de exibição ou usuário; comparação sem acento/caixa) destaca o balão de quem é mencionado ("— mencionou você") e gera toast "Você foi mencionado" quando a janela do grupo está em segundo plano.
- Link do projeto no Ajuda (seção 9. PROJETO) e na tela Sobre (clicável).
- `toaster.py` novo; `windows-toasts` só entra no build Win10/11 (excluído do build Win7/py3.8).

## v1.25 - limpeza de terceiros
- Remoção de toda menção a marca de terceiros de mensagens ao usuário e de comentários/docstrings; nenhum comportamento, protocolo, visual ou regra de negócio alterado.

## v1.24 — emojis e eu na lista
- Botão 😊 nas conversas (1-1 e grupo); você aparece na lista como "(você)" e a conversa própria funciona como anotações (loopback real, vai para o histórico); chamadas de worker para a UI via fila thread-safe.
