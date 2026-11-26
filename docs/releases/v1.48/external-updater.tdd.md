# Evidência TDD — atualizador externo v1.48

## Jornada

Como usuário, quero confirmar uma atualização em qualquer tela e ter o
aplicativo encerrado, atualizado e reaberto automaticamente.

## Garantias

| Garantia | Teste | Resultado |
|---|---|---|
| Auxiliar executa `taskkill /F /IM LANMessenger.exe` | `python -m lan_messenger.test_updates` | PASS |
| Instalador roda silenciosamente e o auxiliar aguarda | `python -m lan_messenger.test_updates` | PASS |
| Aplicativo é reaberto se necessário | `python -m lan_messenger.test_updates` | PASS |
| Instalador temporário é removido | `python -m lan_messenger.test_updates` | PASS |
| Auxiliar inicia em processo separado | `python -m lan_messenger.test_updates` | PASS |

## Evidência RED/GREEN

- RED: fluxo automático dependia diretamente do instalador e Ajuda ainda abria a página web.
- GREEN: 30 suites passaram no Python 3.13 e no Python 3.8.

## Commits

- RED: `c113cfe test: reproduzir fluxo incompleto de atualização`
- GREEN: `a62af5a fix: coordenar atualização por processo externo`
