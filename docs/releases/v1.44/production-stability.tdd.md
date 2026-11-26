# Evidência TDD — estabilidade em produção v1.44

## Origem

Jornadas derivadas dos relatos da implantação em toda a empresa.

## Jornadas

- Como usuário, quero que mudanças de presença não façam a janela principal piscar.
- Como usuário, quero ver as mensagens mais recentes sem perda ou duplicação.
- Como usuário, quero que conversas apareçam rápido e no monitor em uso.

## Evidência RED/GREEN

| Garantia | Teste | Tipo | Resultado |
|---|---|---|---|
| O limite do histórico seleciona as mensagens mais recentes | `python -m lan_messenger.test_history` | integração SQLite | PASS |
| Reentrega com o mesmo ID não duplica mensagem | `python -m lan_messenger.test_history` | integração SQLite | PASS |
| Mudança apenas de status não reconstrói a lista | `python -m lan_messenger.test_production_fixes` | unidade | PASS |
| Primeira mensagem não aparece duas vezes ao abrir a conversa | `python -m lan_messenger.test_production_fixes` | unidade | PASS |
| Histórico pode ser renderizado em lotes | `python -m lan_messenger.test_production_fixes` | unidade | PASS |
| Centralização respeita a área do monitor da janela principal | `python -m lan_messenger.test_production_fixes` | unidade | PASS |

RED observado antes da correção:

- `messages_with_ids(..., limit=10)` retornou `bulk-000` até `bulk-009`.
- `roster_layout_signature` não existia.
- `Store.add_message_once` não existia.

GREEN observado após a correção:

- 30 suites do projeto passaram no Python 3.13.

## Commits de checkpoint

- RED: `df369e1 test: reproduzir falhas de histórico e interface em produção`
- GREEN: `f877ea3 fix: estabilizar lista e preservar histórico das conversas`

## Lacunas

O teste automatizado valida a lógica de centralização e atualização incremental.
A confirmação visual final ocorre no smoke test dos executáveis Windows.
