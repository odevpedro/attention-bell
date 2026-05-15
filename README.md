# Sino de Atencao

> Aplicacao desktop local que interrompe o usuario periodicamente para retomar a intencao escolhida durante uma sessao de trabalho.

---

## Sobre o Projeto

O Sino de Atencao e um aplicativo desktop leve para treino de atencao consciente. Ao iniciar, o usuario informa o que pretende fazer; depois, em intervalos configuraveis, a aplicacao exibe um alerta centralizado perguntando se ele ainda esta alinhado com essa intencao.

O projeto nao monitora atividade do computador, nao captura tela, nao registra teclado, nao analisa janelas abertas e nao usa internet. O unico historico persistido e um arquivo local `history.jsonl`, usado para dar perspectiva de progresso ao usuario.

---

## Stack & Arquitetura

| Camada | Tecnologia |
|--------|------------|
| Runtime | Python 3.10+ |
| Interface | Tkinter |
| Persistencia | Arquivos locais `config.json` e `history.jsonl` |
| Dependencias externas | Nenhuma na versao Tkinter puro |
| Testes | Validacao de sintaxe com `python3 -m py_compile main.py` |

> Padrao arquitetural: aplicacao desktop monolitica simples, orientada a eventos Tkinter, com timer nao-bloqueante via `root.after()`.

---

## Estrutura de Pastas

```text
attention-bell/
├── main.py
├── config.json
├── requirements.txt
├── README.md
├── CLAUDE.md
├── backlog.md
└── docs/
    ├── system-feature-flows.md
    └── data-model.md
```

O arquivo `history.jsonl` e criado automaticamente apos o primeiro evento registrado.

---

## Como Rodar Localmente

### Pre-requisitos

- Python 3.10 ou superior.
- Tkinter instalado.

No Windows e no macOS, Tkinter normalmente acompanha a instalacao oficial do Python.

No Linux, se Tkinter nao estiver disponivel, instale o pacote correspondente da distribuicao. Em sistemas baseados em Debian/Ubuntu:

```bash
sudo apt install python3-tk
```

### Setup

```bash
cd /home/peter/Imagens/attention-bell
python3 main.py
```

No Windows, dependendo da instalacao:

```bash
python main.py
```

---

## Testes

```bash
python3 -m py_compile main.py
```

Esse comando valida a sintaxe do arquivo principal. Ainda nao ha suite automatizada de testes unitarios ou funcionais.

---

## Funcionalidades Principais

| Funcionalidade | Descricao |
|----------------|-----------|
| Intencao inicial | Ao abrir, o app pede a intencao da sessao antes de iniciar o timer |
| Timer configuravel | Intervalo principal e adiamento configuraveis em minutos inteiros |
| Overlay visual | Pulso vermelho fullscreen com baixa opacidade, se habilitado |
| Alerta modal | Janela centralizada always-on-top com perguntas de reflexao |
| Tremor do alerta | Movimento curto da janela para chamar atencao |
| Pausar/retomar | Pausa durante sessao ativa; retomada reinicia o intervalo inteiro |
| Historico local | Registra eventos em `history.jsonl`, mais recentes primeiro na visualizacao |
| Limpar historico | Remove o arquivo local de historico pela interface |

---

## Configuracao

O arquivo `config.json` controla preferencias gerais:

```json
{
  "timer_interval_minutes": 15,
  "snooze_interval_minutes": 5,
  "overlay_enabled": true,
  "overlay_color": "#FF0000",
  "overlay_opacity": 0.15,
  "overlay_pulses": 3
}
```

A intencao atual nao e salva em `config.json`.

---

## Historico Local

O historico fica em `history.jsonl`, no formato JSON Lines. Cada linha contem data/hora local, tipo de evento, intencao e, quando aplicavel, as respostas digitadas nas tres perguntas do alerta.

Eventos registrados:

- `session_start`: inicio de sessao com a intencao escolhida.
- `check_in`: alerta periodico, com respostas escritas ou sem resposta.
- `snoozed`: alerta adiado pelo usuario.
- `intention_adjusted`: mudanca da intencao atual.
- `session_ended`: encerramento da sessao.

Use `Ver historico` para revisar os registros e `Limpar historico` para apagar o arquivo local.

---

## Privacidade

Esta aplicacao:

- nao monitora atividade;
- nao captura tela;
- nao registra teclado;
- nao analisa janelas abertas;
- nao envia dados;
- nao usa internet;
- nao possui login, analytics, telemetria, banco de dados remoto ou sincronizacao.

O historico pode conter reflexoes pessoais digitadas pelo usuario. Ele fica somente no arquivo local `history.jsonl`.

---

## Acessibilidade e Seguranca Visual

O overlay usa baixa opacidade, transicoes graduais e poucas pulsacoes. Ele evita flashes rapidos, tela branca, contraste extremo e efeito estroboscopico.

Se houver sensibilidade visual, desative o overlay pela janela de configuracao ou defina `"overlay_enabled": false` no `config.json`.

---

## Documentacao Tecnica

| Documento | Descricao |
|-----------|-----------|
| [Fluxos de Funcionalidades](./docs/system-feature-flows.md) | Fluxos internos das features implementadas |
| [Modelo de Dados](./docs/data-model.md) | Estrutura de `config.json` e `history.jsonl` |
| [Backlog](./backlog.md) | Status de desenvolvimento e proximas melhorias |
| [Regras para agentes](./CLAUDE.md) | Regras de manutencao documental do projeto |

---

## Status do Projeto

```text
[x] 0.1.0 - MVP desktop Tkinter puro
[x] 0.2.0 - Historico local persistente
[x] 0.3.0 - Alerta com foco forcado e tremor
[x] 0.4.0 - Respostas separadas por pergunta e overlay vermelho
[ ] 0.5.0 - Testes automatizados e empacotamento
```

---

## Licenca

Licenca ainda nao definida.
