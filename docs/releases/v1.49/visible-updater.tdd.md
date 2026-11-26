# Evidência TDD — instalador visível v1.49

## Jornada

Como usuário, quero acompanhar a instalação e recuperar o aplicativo caso a
atualização não consiga concluir.

## Garantias

| Garantia | Teste | Resultado |
|---|---|---|
| Instalador usa `/SILENT`, não `/VERYSILENT` | `python -m lan_messenger.test_updates` | PASS |
| Auxiliar confirma início antes do encerramento | `python -m lan_messenger.test_updates` | PASS |
| Caminho com espaços executa corretamente | `python -m lan_messenger.test_updates` | PASS |
| Aplicativo é reaberto após o instalador | `python -m lan_messenger.test_updates` | PASS |
| Temporários só são apagados após sucesso | `python -m lan_messenger.test_updates` | PASS |

## Evidência RED/GREEN

- RED: aplicativo fechava sem confirmar que o auxiliar realmente começou.
- RED: `/VERYSILENT` ocultava progresso e qualquer sinal de falha.
- GREEN: 30 suites passaram no Python 3.13 e no Python 3.8.

## Commits

- RED: `4b3673a test: reproduzir auxiliar oculto sem confirmação`
- GREEN: `b1dafaf fix: mostrar instalador e confirmar auxiliar de atualização`
