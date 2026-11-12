# Build e release

Duas linhas de build independentes, cada uma gerando um instalador Inno Setup:

| Alvo | Python | Saída | Requisito |
|---|---|---|---|
| Windows 10/11 | 3.13 | `dist\LANMessenger.exe` + `Setup_LANMessenger_win10_11_vX.Y.exe` | Win10+ |
| Windows 7/8.1 | 3.8 | `dist-win7\LANMessenger.exe` + `Setup_LANMessenger_win7_81_vX.Y.exe` | Win7 SP1 atualizado (Universal C Runtime) |

O instalador escolhe sozinho o executável certo conforme o Windows detectado.

## Pré-requisitos

- Python 3.13 (novo) e Python 3.8 (legado, ex.: `C:\Python38`) com PyInstaller em ambos.
- Inno Setup 6 em `C:\tools\inno\ISCC.exe`.
- `pip install -r lan_messenger/requirements.txt` em cada Python.
- Arquivos locais não versionados (ver "Assets não versionados" abaixo).

## Comandos (na raiz do repositório)

```powershell
# Windows 10/11
pyinstaller --noconfirm lan_messenger/LANMessenger.spec

# Windows 7/8.1
C:\Python38\python.exe -m PyInstaller --noconfirm --distpath dist-win7 --workpath build-win7 lan_messenger/LANMessenger_win7.spec

# Instaladores
C:\tools\inno\ISCC.exe lan_messenger/installer_win10_11.iss
C:\tools\inno\ISCC.exe lan_messenger/installer_win7_81.iss
```

Saídas: `dist\`, `dist-win7\`, `build\`, `build-win7\` (temporários) e `installer\` (setups finais).

## O que os `.spec` fazem

- `ROOT = SPECPATH/..` — caminhos resolvidos da raiz.
- **Versão embutida no exe**: `version_info.txt` é gerado a partir de `config.APP_VERSION` antes do build — Propriedades > Detalhes do exe mostra a mesma versão da tela Sobre.
- `datas`: `assets/` (ícones, sons, imagens) + `networks.json` + `collect_data_files("customtkinter")`.
- Entrada: `python -m lan_messenger`; onefile, sem console; ícone `assets/app.ico`.

## O que os `.iss` fazem

- Instalam em `Program Files\LANMessenger` (exe + `app.ico` + `assets` + guia de teste).
- Criam atalhos com o ícone de balões.
- Liberam firewall: UDP 50000 + TCP 50001/50002 (idempotente: remove regras antes de criar).
- Encerram versão aberta no update (taskkill) e removem tudo no uninstall.
- Nome do arquivo com a versão: `Setup_LANMessenger_win10_11_v1.24.exe`.

## Checklist de bump de versão (X.Y)

Para **cada** mudança no app, antes de buildar:

1. `lan_messenger/config.py` → `APP_VERSION = "X.Y"`.
2. `lan_messenger/installer_win10_11.iss` → `AppVersion` e nome de saída.
3. `lan_messenger/installer_win7_81.iss` → idem.
4. `lan_messenger/README.md` → seção da versão + Histórico de versões.
5. `HELP_TEXT` em `app_gui.py` → histórico na Ajuda in-app.
6. Testes que referenciam versão.
7. Rodar a suíte completa nos dois Pythons.
8. Buildar 4 artefatos (2 exes + 2 setups) e validar E2E em 2 PCs.

## Assets não versionados

O repositório **não** inclui:

- `assets/sounds/*.wav` — sons de notificação de terceiros; fornecidos localmente para o build. Sem eles, o app funciona sem som.
- Dados de execução (`settings.json`, `profile.json`, `networks.json`, `peers_cache.json`, `lan_history.db`) — criados automaticamente com defaults na primeira execução.
- `LEIA-ME-TESTE.txt` — guia interno de teste.

## Testes

```powershell
# Python 3.13
python -m unittest discover -s lan_messenger -p "test_*.py" -v

# Python 3.8
C:\Python38\python.exe -m unittest discover -s lan_messenger -p "test_*.py" -v
```

16 suítes cobrindo: criptografia, presença UDP/TCP, faixas VPN, balões, emojis, grupos, histórico, sons/atalhos, instância dupla, tray/autostart, menus, temas e transferências.

## E2E em 2 PCs (resumo)

1. Feche instâncias abertas (`LANMessenger.exe`) antes dos testes.
2. Instale o setup certo em cada PC (Admin).
3. Confira ping entre as redes VPN.
4. Abra nos dois; cadastre faixas; distribua a chave de criptografia.
5. Valide: descoberta (~5s), mensagem, arquivo, massa, status, histórico, tray.
