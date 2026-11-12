# Instalação e uso

## Instaladores

| Arquivo | Para | Tamanho aprox. |
|---|---|---|
| `Setup_LANMessenger_win10_11_vX.Y.exe` | Windows 10/11 | ~24 MB |
| `Setup_LANMessenger_win7_81_vX.Y.exe` | Windows 7 SP1 / 8 / 8.1 | ~17 MB |

- Instale **como Administrador**. O instalador detecta o Windows e usa o executável certo (Win7 recebe o build dedicado em Python 3.8).
- Sem SP1/atualizações no Win7 pode faltar o Universal C Runtime.
- Tudo embutido — não precisa de Python na máquina.
- O instalador: cria `Program Files\LANMessenger`, atalhos, libera firewall (UDP 50000, TCP 50001/50002) e fecha versão aberta no update.

## Portas e firewall

| Serviço | Proto | Porta |
|---|---|---|
| Descoberta | UDP | 50000 |
| Chat | TCP | 50001 |
| Arquivos | TCP | 50002 |

- Os setups liberam automaticamente. Para liberar manualmente, `firewall.cmd` como Admin em cada PC.
- Se a VPN aparecer como rede **Pública** no Windows, libere no perfil público ou reclassifique a VPN como Privada/Domínio.

## Mesma rede (LAN)

1. Instale nos PCs e execute.
2. Primeiro contato: botão **Meus Dados** — nome e departamento (grupos saem daí).
3. Colegas aparecem na lista em ~5s. Duplo-clique abre a conversa.

## Duas redes unidas por VPN

O broadcast limitado não atravessa roteador/VPN. O app resolve com **beacon unicast para cada IP das faixas** + broadcast dirigido; chat/arquivo (TCP direto) já cruzam a VPN se houver rota.

1. Confirme ping entre as redes: `ping 192.168.30.10` a partir da `10.0.0.x` (e vice-versa).
2. Em cada PC, tela **Rede (VPN)**: cadastre as duas faixas, ex.:
   - `10.0.0.1-10.0.0.254`
   - `192.168.30.1-192.168.30.254`
3. Firewall **nos dois lados** (ver acima).
4. UDP filtrado pelo túnel? Plano B: **+ IP manual** (ou `--add-peer`) + TCP direto — o app confirma presença por TCP a cada ~10s e a lista volta sozinha após queda de VPN.

## Criptografia (opcional, recomendada)

Modelo PSK: a mesma chave de 32 bytes em todos os PCs.

1. Em um PC: **Rede → Gerar → Salvar** (cadeado 🔒 aparece na statusbar).
2. Distribua: **Exportar** gera `lan-chave.key`; leve ao outro PC e **Importar → Salvar** (ou cole o valor no campo).
3. Cobertura: texto do chat + blocos de arquivo (AES-256-GCM). **Em claro:** beacons (presença/nome/departamento) e header de arquivo (nome/tamanho) — ver [PRIVACIDADE.md](PRIVACIDADE.md).
4. Sem chave (ou chave divergente): tráfego em claro ou falha limpa — nada trava.

## Uso diário

- **Conversa**: duplo-clique no contato; Enter envia (configurável); Ctrl+V cola print; arrastar/soltar anexa arquivo; botão 😊 abre emojis.
- **Arquivos**: botão de anexo ou arraste; recebidos em `%APPDATA%\LANMessenger\inbox\<Remetente>\` com botão "Abrir pasta" no cartão.
- **Grupos**: clicar no grupo envia para todos; botão direito no grupo → mensagem em massa, conversa em grupo, renomear, novo, apagar, mover.
- **Status**: botões no rodapé (Disponível/Ocupado/Ausente); Ocupado/Ausente pedem mensagem que viaja no beacon; manual não volta sozinho.
- **Histórico**: botão na conversa abre o Visualizador filtrado naquele contato; busca e export TXT.
- **Fechamento**: a janela minimiza para a bandeja (ponto vermelho = não lidas). Sair de verdade: botão direito no ícone → **Sair**.
- **Config**: temas Light/Dark/System, sons, atalhos, autostart ("Iniciar com o Windows" grava no registro do usuário).

## Desenvolvimento (sem instalador)

```bash
pip install -r lan_messenger/requirements.txt
python -m lan_messenger.app_gui
# ou CLI para teste rápido:
python -m lan_messenger.app_cli --name PC-TESTE
# peer manual:
python -m lan_messenger.app_cli --name PC-TESTE --add-peer 192.168.1.20
```

Instância única: a segunda cópia detecta a primeira (lock em `127.0.0.1:50009`) e sai com aviso.
