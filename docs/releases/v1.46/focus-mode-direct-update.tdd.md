# Evidência TDD — modo foco e atualização direta v1.46

## Jornadas

- Como usuário, quero receber mensagens sem interromper meu trabalho.
- Como usuário, quero confirmar a atualização sem abrir o site.

## Garantias

| Garantia | Teste | Resultado |
|---|---|---|
| Modo foco cria nova conversa minimizada | `python -m lan_messenger.test_production_fixes` | PASS |
| Modo foco não restaura conversa existente | `python -m lan_messenger.test_production_fixes` | PASS |
| Modo foco solicita piscar sem anunciar ou roubar foco | `python -m lan_messenger.test_production_fixes` | PASS |
| Aviso usa “Quer atualizar a sua versão agora?” | `python -m lan_messenger.test_updates` | PASS |
| Confirmação chama o instalador automático | `python -m lan_messenger.test_updates` | PASS |

## Evidência RED/GREEN

- RED: aviso ainda abria Releases e preferência `minimize` abria conversa em primeiro plano.
- GREEN: 30 suites passaram no Python 3.13 e no Python 3.8.

## Commits

- RED: `dd39f17 test: reproduzir atualização indireta e modo somente piscar`
- GREEN: `cdfb96d fix: instalar atualização e oferecer modo somente piscar`
