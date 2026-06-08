# Backlog — Sino de Atencao

> Registro vivo do progresso do projeto. Atualizado a cada mudanca de estado de uma funcionalidade.
> **Ultima atualizacao:** 2026-06-08

---

## Sobre o Projeto

Aplicacao desktop local que ajuda o usuario a retomar uma intencao de trabalho por meio de alertas periodicos conscientes.

**Versao atual:** `0.8.0`
**Repositorio:** projeto local em `/home/peter/Imagens/attention-bell`
**Stack principal:** Python 3.10+ com Tkinter

---

## Legenda

| Simbolo | Significado |
|---------|-------------|
| `[ ]` | Pendente |
| `[~]` | Em andamento |
| `[x]` | Concluido |
| `P0` | Critico — bloqueia outras features |
| `P1` | Alta prioridade |
| `P2` | Media prioridade |
| `P3` | Melhoria |
| `XS` `S` `M` `L` `XL` | Estimativa de complexidade |

---

## Em Andamento

Nao ha item em andamento no momento.

---

## Pendentes

- `[ ] P1 M` Adicionar testes automatizados para normalizacao de config, escrita/leitura de historico e fluxo de agendamento.
- `[ ] P2 M` Criar modo de teste com intervalo curto controlado sem aceitar decimais na configuracao de producao.
- `[ ] P2 M` Avaliar empacotamento para Windows, Linux e macOS (PyInstaller ou similar).
- `[ ] P2 M` Criar app bundle (.app) para macOS com launcher automatizado.
- `[ ] P2 S` Adicionar exportacao manual do historico local.
- `[ ] P2 S` Adicionar limpeza de historico por periodo.
- `[ ] P3 M` Avaliar bandeja do sistema com fallback funcional.
- `[ ] P3 S` Melhorar acessibilidade do alerta para usuarios com sensibilidade visual.

---

## Concluidas

- `[x] P0 M` 2026-05-15 — Criado MVP Tkinter puro com tela inicial de intencao, timer nao-bloqueante e modal de reflexao.
- `[x] P0 S` 2026-05-15 — Implementado `config.json` com intervalo principal, adiamento e preferencias do overlay.
- `[x] P1 M` 2026-05-15 — Implementado overlay vermelho fullscreen com baixa opacidade e pulsacoes suaves.
- `[x] P1 M` 2026-05-15 — Implementados botoes `Continuar`, `Ajustar intencao`, `Encerrar sessao` e `Adiar`.
- `[x] P1 M` 2026-05-15 — Implementado historico persistente local em `history.jsonl`.
- `[x] P1 S` 2026-05-15 — Implementada visualizacao do historico em ordem mais recente primeiro.
- `[x] P1 S` 2026-05-15 — Implementada limpeza manual do historico local.
- `[x] P1 S` 2026-05-15 — Registrados eventos `session_start`, `check_in`, `snoozed`, `intention_adjusted` e `session_ended`.
- `[x] P1 S` 2026-05-15 — Ajustado alerta para tentar desminimizar, ganhar foco, tocar bell e tremer no centro da tela.
- `[x] P2 S` 2026-05-15 — Documentado projeto com README, backlog, fluxos, modelo de dados e regras para agentes.
- `[x] P1 S` 2026-05-15 — Separadas as tres perguntas do alerta em campos de resposta independentes.
- `[x] P1 XS` 2026-05-15 — Alterada a cor do overlay padrao de ambar para vermelho.
- `[x] P2 M` 2026-05-15 — Adicionado grid experimental de janelas via KWin/Wayland e `wmctrl` fallback para Chrome e terminal.
- `[x] P2 S` 2026-05-15 — Adicionado gerenciador de arquivos ocupando a metade esquerda no grid experimental.
- `[x] P2 S` 2026-05-23 — Adicionado tiktak opcional ao iniciar sessao e pergunta de fechamento ao encerrar a sessao.
- `[x] P3 XS` 2026-05-23 — Adicionado icone local de sino para o launcher e tentativa de icone na janela do app.
- `[x] P2 S` 2026-05-23 — Adicionado som local em loop continuo durante a sessao usando 2 segundos do trecho audivel de `tick.wav`.
- `[x] P1 M` 2026-06-08 — Suporte multiplataforma (Linux, macOS, Windows) com `afplay` no macOS e icone via PhotoImage.

---

## Bugs Conhecidos

| ID | Descricao | Severidade | Reportado em |
|----|-----------|------------|--------------|
| BUG-001 | Alguns gerenciadores de janela podem limitar `focus_force()` e impedir foco absoluto do modal. | Media | 2026-05-15 |

---

## Notas & Decisoes Pendentes

- A primeira versao nao usa bandeja do sistema para manter o app Tkinter puro e simples.
- O botao `X` minimiza a janela; o encerramento real do app fica no botao `Sair` da tela inicial.
- Pausas e retomadas nao sao registradas no historico para evitar log operacional excessivo.
- O historico local pode conter texto pessoal; futuras versoes devem considerar exportacao, limpeza por periodo e possivel protecao local.
- Intervalos sao minutos inteiros, sem valores decimais.

---

## Historico de Versoes

| Versao | Data | Principais entregas |
|--------|------|---------------------|
| `0.1.0` | 2026-05-15 | MVP Tkinter puro com intencao, timer, overlay e modal |
| `0.2.0` | 2026-05-15 | Historico local persistente em JSONL e visualizacao pela interface |
| `0.3.0` | 2026-05-15 | Alerta com tentativa de foco forcado, bell e tremor |
| `0.4.0` | 2026-05-15 | Respostas separadas por pergunta e overlay vermelho |
| `0.5.0` | 2026-05-15 | Grid experimental para abrir/organizar gerenciador de arquivos, Chrome e terminal ao iniciar sessao |
| `0.6.0` | 2026-05-23 | Tiktak opcional no inicio da sessao, pergunta de fechamento e icone local |
| `0.7.0` | 2026-05-23 | Som local `tick.wav` em loop durante a sessao |
| `0.8.0` | 2026-06-08 | Suporte multiplataforma (Linux, macOS, Windows) com `afplay` e icone via PhotoImage |
