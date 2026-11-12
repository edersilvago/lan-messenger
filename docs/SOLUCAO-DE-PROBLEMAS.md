# Solução de problemas

## Lista de usuários vazia (não encontro o colega)

1. **Tela Rede → Diagnóstico**: escuta UDP 50000 = OK? `ERRO (porta em uso)` → feche a outra cópia do app (ou o Softros, que usa as mesmas portas).
2. **Último recebido = "nunca"** mas *Testar IP* do colega alcança? → UDP está bloqueado (firewall ou VPN filtrando UDP). Libere o firewall **nos dois lados** e use **+ IP manual** — o app confirma presença por TCP a cada ~10s.
3. **Testar IP falhou?** → sem rota entre as redes: confira `ping` e a VPN.
4. Faixas digitadas erradas? `/ranges` (CLI) ou tela Rede mostram o cadastrado.
5. Firewall com perfil **Público**? Libere no perfil público ou reclassifique a VPN.

## "já está em execução"

Segunda cópia detecta a primeira pelo lock em `127.0.0.1:50009` e sai. Feche a instância aberta (ícone na bandeja → Sair) ou mate `LANMessenger.exe`.

## Colega online não recebe mensagem

- P2P **não tem fila de offline**: destino precisa estar ligado e alcançável. A trava anti-offline pede confirmação antes de enviar; falha marca o contato offline e avisa.
- Par "sinal fraco" é checado por TCP antes do envio.

## Mensagens chegam embaralhadas / falha de chave

Chave divergente entre os PCs: redistribute o mesmo valor da chave (Rede → colar/Salvar). Sem chave, o tráfego vai em claro; com chaves diferentes, a decodificação falha limpa (nada trava).

## Som não toca

- Sons desativados em Config → Sons.
- Sem `assets/sounds/*.wav` na instalação → sem som (os WAVs não são distribuídos no repositório; os instaladores oficiais os embutem).

## Win7: app não abre

- Win7 precisa de **SP1 + atualizações** (Universal C Runtime). Use o instalador `win7_81` (build dedicado em Python 3.8) — o `win10_11` não abre no Win7.

## VPN caiu e a lista não volta

v1.14+: sem reiniciar — o app confirma por TCP a cada ~10s os colegas fracos/offline e os reconecta sozinhos quando a rota volta. Cache (`peers_cache.json`) acelera a primeira busca ao abrir.

## Balões/dimensões estranhas (dev)

- Cartão de anexo tem largura fixa (`CARD_WIDTH = 360`) com wrap manual — o `wraplength` do CTkLabel é instável.
- Temas usam tuplas `(light, dark)` do CustomTkinter.

## Histórico onde fica

`%APPDATA%\LANMessenger\` (SQLite `lan_history.db`, `peers_cache.json`, `inbox\<Remetente>\`). Log em TXT conforme Config → Log (single/per-user).
