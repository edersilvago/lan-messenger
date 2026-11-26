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
- **Links clicáveis**: URLs `http(s)://` e `www.` nas mensagens abrem no navegador (v1.27).
- **Responder mensagem**: botão direito no balão ou duplo-clique na mensagem → citação dentro do enviado (barra verde, autor + trecho), estilo WhatsApp (v1.30/v1.31).
- **Texto proporcional à janela**: a quebra do balão segue 75% da largura da conversa (300–1200 px) e se reajusta ao redimensionar (v1.32).
- **Conversa estável**: correção definitiva da recursão Tk ao abrir ou rolar mensagens antigas (v1.33).
- **Layout da conversa**: texto usa 94% da largura, citação fica compacta e abrir/maximizar não deixa o histórico em branco (v1.34).
- **Fonte responsiva**: Normal/Grande/Extra grande alteram imediatamente todo o texto das conversas 1-1 e em grupo, inclusive balões abertos (v1.35).
- **Fonte em px**: digite qualquer tamanho entre 8 e 32 px, com prévia e aplicação imediatas; configurações antigas são migradas (v1.36).
- **Envio sem trava**: ENTER não espera a rede; a mensagem entra na fila e o envio ocorre em segundo plano, com status no rodapé (v1.37).
- **Foco ao clicar**: clique em área livre da conversa leva o cursor ao campo de texto (v1.37).
- **Nova versão**: ao abrir, o app consulta o GitHub silenciosamente e avisa se houver release mais nova (v1.37).
- **Foco real**: abrir conversa ou receber mensagem traz janela e cursor ao campo de texto (v1.38).
- **Quebra automática**: palavras longas sem espaço quebram automaticamente nos balões (v1.39).
- **Emoticons**: atalhos como `:)`, `<3`, `:D` viram emoji após envio (v1.39).
- **Ajuda com atualização**: tela Ajuda indica quando há nova versão e oferece download (v1.40).
- **Exportar/importar grupos**: Configurações dos Grupos exporta e importa organização em JSON (v1.40).
- **Renomear grupo por F2**: clicar no grupo seleciona e F2 renomeia (v1.40).
- **Sobre com atualização**: tela Sobre verifica nova versão, baixa e instala silenciosamente (estilo Firefox) (v1.41).
- **Exportar/importar grupos com contatos**: a exportação também salva os dados dos contatos para organizar ao importar em outro cliente (v1.42).
- **Reabrir após atualização**: o instalador reabre o LAN Messenger ao terminar a atualização silenciosa (v1.43).
- **Estabilidade em produção**: lista não pisca a cada mudança de presença; histórico recente permanece visível e mensagens repetidas não duplicam (v1.44).
- **Conversas mais rápidas**: histórico renderiza em lotes e a janela abre centralizada no monitor da janela principal (v1.44).
- **Mensagem recebida visível**: a conversa sempre abre no centro do monitor e pisca na barra de tarefas, além do toast (v1.45).
- **Histórico diário na conversa**: a janela mostra somente mensagens do dia atual; dias anteriores permanecem no Histórico (v1.45).
- **Modo foco**: escolha “Somente piscar na barra de tarefas” para receber mensagens sem abrir conversa ou toast (v1.46).
- **Atualização direta**: o aviso de nova versão pergunta se deseja atualizar e inicia a instalação após confirmação (v1.46).
- **Mensagem para contato offline**: a mensagem fica na fila local e sai sozinha quando o colega aparece online (marca `(pendente)` vira tique) - o remetente precisa estar com o app aberto (v1.29).
- **Log de erros**: falhas internas vão para `%APPDATA%\LANMessenger\logs\crash.log` com data, hora e traceback; aviso no rodapé e botão para abrir a pasta (v1.28).
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

- **Sem entrega garantida**: a fila local guarda mensagens para contatos offline, mas só entrega se o remetente estiver com o app aberto quando o destinatário voltar. Sem servidor, nada é entregue com os dois desligados.
- **Beacons em claro**: presença, nome e departamento circulam sem criptografia; texto do chat e blocos de arquivo usam AES-256-GCM quando há chave. Detalhes em [`docs/PRIVACIDADE.md`](docs/PRIVACIDADE.md).

## Licença

[MIT](LICENSE)
