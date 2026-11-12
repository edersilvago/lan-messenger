# LAN Messenger — P2P para rede local e VPN, sem servidor

Mensageiro instantâneo para Windows no estilo clássico LAN Messenger: descoberta de usuários por UDP, conversa e arquivos por TCP direto entre os PCs, criptografia opcional AES-256-GCM e histórico local em SQLite. Não usa servidor de mensagem — tudo é ponto a ponto.

Compatível com Windows 7 SP1 / 8 / 8.1 / 10 / 11 (64 bits), com instaladores dedicados por família de sistema.

## Destaques

- **Lista de usuários viva**: beacon UDP a cada 4s + presença de reforço via TCP a cada ~10s (sobrevive a quedas de VPN sem reiniciar) + cache da última sessão.
- **Conversa em balões**: estilo WhatsApp (enviadas em verde à direita, recebidas em branco à esquerda), carimbo `HH:MM:SS`, separadores de data, tique de entrega e emojis.
- **Arquivos por cartão**: selo da extensão, nome, hora e "Abrir pasta"; recebidos organizados em `inbox/<Remetente>/`.
- **Grupos por departamento**: agregação automática + grupos manuais, mensagem em massa com checkboxes por grupo.
- **Criptografia PSK**: AES-256-GCM no texto do chat e nos blocos de arquivo (64 KB) quando a chave é distribuída entre os PCs.
- **Tray, status e autostart**: minimiza para a bandeja, status Disponível/Ocupado/Ausente que viaja no beacon, iniciar com o Windows.
- **Notificações toast + menções**: aviso nativo do Windows 10/11 (clique traz o app à frente; Win7 usa o balão da bandeja) e `@nome` na conversa em grupo destaca quem foi mencionado.
- **Instaladores versionados**: Inno Setup gera `Setup_LANMessenger_win10_11_vX.Y.exe` e `Setup_LANMessenger_win7_81_vX.Y.exe` com firewall e desinstalação completos.

## Início rápido (desenvolvedor)

```bash
git clone https://github.com/edersilvago/lan-messenger.git
cd lan-messenger
pip install -r lan_messenger/requirements.txt
python -m lan_messenger.app_gui
```

Em outro PC da mesma rede (ou outra instância com `--add-peer`), o colega aparece na lista em ~5s. Guia de teste em 2 PCs, VPN e criptografia: [`docs/INSTALACAO.md`](docs/INSTALACAO.md).

## Documentação

| Documento | Conteúdo |
|---|---|
| [Instalação e uso](docs/INSTALACAO.md) | Instaladores, portas/firewall, VPN entre redes, chave de criptografia |
| [Arquitetura](docs/ARQUITETURA.md) | Protocolo, descoberta, presença TCP, criptografia, threading da UI |
| [Build e release](docs/BUILD-E-RELEASE.md) | PyInstaller (3.13 e 3.8), Inno Setup, checklist de versão |
| [Solução de problemas](docs/SOLUCAO-DE-PROBLEMAS.md) | Lista vazia, UDP bloqueado, VPN sem rota, portas em uso |
| [Histórico de versões](docs/HISTORICO-DE-VERSOES.md) | Changelog completo v1.0 → atual |
| [Privacidade na rede](docs/PRIVACIDADE.md) | O que circula em claro e o que é selado |

## Portas

| Serviço | Proto | Porta |
|---|---|---|
| Descoberta (beacon) | UDP | 50000 |
| Chat | TCP | 50001 |
| Arquivos | TCP | 50002 |
| Instância única (lock) | TCP | 50009 (localhost) |

## Limites do P2P puro (por arquitetura)

- **Sem mensagem offline**: destino precisa estar ligado e alcançável; sem servidor não há fila — o app avisa em vez de fingir que enviou.
- **Beacons em claro**: presença, nome e departamento circulam sem criptografia; texto do chat e blocos de arquivo usam AES-256-GCM quando há chave. Detalhes em [`docs/PRIVACIDADE.md`](docs/PRIVACIDADE.md).

## Licença

[MIT](LICENSE)
