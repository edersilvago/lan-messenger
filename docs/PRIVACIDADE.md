# Privacidade na rede

O que circula em claro e o que é selado quando a chave AES-256-GCM está ativa.

## Sem chave configurada (estado inicial)

Todo o tráfego vai **em claro** na rede local/VPN:

- Presença e perfil (beacon UDP)
- Texto das mensagens (TCP 50001)
- Conteúdo dos arquivos (TCP 50002)
- Header de arquivo (nome/tamanho)

A statusbar avisa quando a criptografia está desligada.

## Com chave distribuída (PSK AES-256-GCM)

| Tráfego | Estado | Detalhe |
|---|---|---|
| Texto do chat | 🔒 Selado | nonce aleatório por mensagem |
| Blocos de arquivo (64 KB) | 🔒 Selados | nonce = `sha256(file_id)[:8]` + contador |
| Header de arquivo | ⚠ Em claro | nome e tamanho visíveis na rede |
| Beacons de descoberta | ⚠ Em claro | presença, nome, departamento, função, IDs AnyDesk/RustDesk, CPU/RAM/disco/OS, versão do app, mensagem de status |

## O que isso significa na prática

- **Visível para quem escuta a rede**: quando vocês estão online, nomes e departamentos, quando arquivos transitam e seus nomes/tamanhos.
- **Protegido**: conteúdo das conversas e dos arquivos — ilegível sem a chave.
- **Metadados de presença** não são criptografados **por design**: a descoberta precisa acontecer antes de os PCs negociarem qualquer coisa, e a chave é idêntica em todos os PCs (não há troca de chave por túnel).

## Recomendações para ambientes sensíveis

1. Distribua a chave por canal de admin (GPO/pendrive/contato direto), nunca por e-mail aberto.
2. Se nomes/AnyDesk nos beacons forem sensíveis, use o app em rede confiável ou segmente a VPN.
3. Rotação de chave: gere nova na tela Rede e redistribua a todos — chaves divergentes não se entendem (falha limpa, sem travar).

## Dados locais

Tudo fica no próprio PC: `%APPDATA%\LANMessenger` (histórico SQLite, cache de colegas, inbox por remetente, logs opcionais). Nada é enviado para serviço externo — o app não fala com nenhum servidor.
