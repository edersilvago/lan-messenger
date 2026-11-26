# Evidência TDD — atualização e alerta da barra v1.47

## Jornadas

- Como usuário, quero atualizar sem erro de aplicativo ainda aberto.
- Como destinatário, quero que a conversa pisque até eu abrir a janela.

## Garantias

| Garantia | Teste | Resultado |
|---|---|---|
| Instalador usa processo separado e autolimpável | `python -m lan_messenger.test_updates` | PASS |
| Instalador não abre diálogo do Restart Manager | `python -m lan_messenger.test_updates` | PASS |
| Processo residual é encerrado com toda sua árvore | `python -m lan_messenger.test_updates` | PASS |
| Flash usa o identificador da janela raiz | `python -m lan_messenger.test_production_fixes` | PASS |
| Flash continua até a conversa receber foco | `python -m lan_messenger.test_production_fixes` | PASS |

## Evidência RED/GREEN

- RED: atualizador aguardava o instalador, enquanto ele tentava fechar o próprio aplicativo.
- RED: alerta usava HWND intermediário e parava após cinco pulsos.
- GREEN: 30 suites passaram no Python 3.13 e no Python 3.8.

## Commits

- RED: `61c3253 test: reproduzir bloqueio do atualizador e falha ao piscar`
- GREEN: `02e3dcf fix: encerrar antes de atualizar e manter alerta piscando`
