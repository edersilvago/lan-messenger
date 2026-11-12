# Histórico de versões

Versão atual: **v1.24**. Cada versão traz mudanças visíveis ao usuário; o backend só foi reconstruído visualmente em v1.17 (CustomTkinter), sem alterar protocolo nem regras.

## v1.0 / v1.1 — base P2P estilo Softros
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

## v1.24 — emojis e eu na lista
- Botão 😊 nas conversas (1-1 e grupo); você aparece na lista como "(você)" e a conversa própria funciona como anotações (loopback real, vai para o histórico); chamadas de worker para a UI via fila thread-safe.
