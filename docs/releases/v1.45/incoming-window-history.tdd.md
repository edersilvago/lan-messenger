# Evidência TDD — conversa recebida e histórico diário v1.45

## Jornadas

- Como destinatário, quero ver a conversa recebida no monitor e identificá-la na barra de tarefas.
- Como usuário, quero carregar apenas mensagens de hoje na conversa sem apagar o histórico anterior.

## Garantias

| Garantia | Teste | Resultado |
|---|---|---|
| Preferência antiga `minimize` não impede abrir a conversa | `python -m lan_messenger.test_production_fixes` | PASS |
| Recebimento ativa a conversa e solicita piscar na barra | `python -m lan_messenger.test_production_fixes` | PASS |
| Janela carrega somente mensagens do dia local atual | `python -m lan_messenger.test_history` | PASS |
| Mensagem antiga continua no banco e no histórico | `python -m lan_messenger.test_history` | PASS |

## Evidência RED/GREEN

- RED: `messages_today_with_ids` inexistente e fluxo `minimize` tentou usar somente a barra de status.
- GREEN: 30 suites passaram no Python 3.13.

## Commits

- RED: `3a801f2 test: reproduzir conversa oculta e histórico diário`
- GREEN: `6195f18 fix: exibir conversa recebida e limitar janela ao dia atual`
