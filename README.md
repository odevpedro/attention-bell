# Sino de Atencao

> Aplicacao desktop local (Linux, macOS, Windows) que interrompe o usuario periodicamente para retomar a intencao escolhida durante uma sessao de trabalho.

---

## Sobre o Projeto

O Sino de Atencao e um aplicativo desktop leve para treino de atencao consciente. Ao iniciar, o usuario informa o que pretende fazer; depois, em intervalos configuraveis, a aplicacao pode emitir um tiktak opcional, exibe um alerta centralizado perguntando se ele ainda esta alinhado com essa intencao e, ao encerrar a sessao, mostra uma pergunta final de fechamento.

O projeto nao monitora atividade do computador, nao captura tela, nao registra teclado, nao analisa janelas abertas e nao usa internet. O unico historico persistido e um arquivo local `history.jsonl`, usado para dar perspectiva de progresso ao usuario.

---

## Stack & Arquitetura

| Camada | Tecnologia |
|--------|------------|
| Runtime | Python 3.10+ |
| Interface | Tkinter |
| Persistencia | Arquivos locais `config.json` e `history.jsonl` |
| Dependencias externas | Nenhuma na versao Tkinter puro |
| Plataformas | Linux (primario), macOS, Windows |
| Testes | Validacao de sintaxe com `python3 -m py_compile main.py` |

> Padrao arquitetural: aplicacao desktop monolitica simples, orientada a eventos Tkinter, com timer nao-bloqueante via `root.after()`.

---

## Estrutura de Pastas

```text
attention-bell/
├── main.py
├── config.json
├── tick.wav
├── app-icon.svg
├── app-icon.xbm
├── sino-de-atencao.desktop
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

Linux / macOS:
```bash
cd attention-bell
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
| Sinal sonoro em loop | Tiktak opcional tocando durante toda a sessao a partir dos dois primeiros segundos de `tick.wav`, com `play` do SoX (Linux), `afplay` (macOS) ou `winsound` (Windows) |
| Alerta modal | Janela centralizada always-on-top com perguntas de reflexao |
| Tremor do alerta | Movimento curto da janela para chamar atencao |
| Grid de janelas | Ao iniciar sessao, tenta abrir/posicionar gerenciador de arquivos na metade esquerda, Chrome no quadrante superior direito e terminal no quadrante inferior direito |
| Fechamento de sessao | Ao encerrar, o app mostra uma pergunta final antes de voltar para a tela inicial |
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
  "overlay_pulses": 3,
  "window_grid_enabled": true,
  "tiktak_enabled": true
}
```

A intencao atual nao e salva em `config.json`.

`window_grid_enabled` e experimental e funciona apenas em Linux (KDE Wayland via KWin D-Bus, ou Linux/X11 via `wmctrl`). Em macOS e Windows, esse recurso e ignorado silenciosamente. Se o gerenciador de janelas bloquear a operacao, o app apenas segue sem reorganizar janelas.

`tiktak_enabled` controla o som de fundo da sessao. Se estiver desativado, o app inicia normalmente sem emitir o som. Quando ativo, o app gera um recorte de 2 segundos a partir do primeiro trecho audivel de `tick.wav` e tenta tocar esse trecho em loop continuo durante toda a sessao usando o player nativo do sistema (`play` do SoX no Linux, `afplay` no macOS, `winsound` no Windows) e encerra esse som ao finalizar. Em cada plataforma, caso o player padrao nao esteja disponivel, o app tenta fallbacks (Linux: `aplay`; macOS: `afplay`; Windows: `winsound`) e, como ultimo recurso, usa o bell do Tkinter.

---

## Historico Local

O historico fica em `history.jsonl`, no formato JSON Lines. Cada linha contem data/hora local, tipo de evento, intencao e, quando aplicavel, as respostas digitadas nas tres perguntas do alerta ou a observacao de encerramento da sessao.

Eventos registrados:

- `session_start`: inicio de sessao com a intencao escolhida.
- `check_in`: alerta periodico, com respostas escritas ou sem resposta.
- `snoozed`: alerta adiado pelo usuario.
- `intention_adjusted`: mudanca da intencao atual.
- `session_ended`: encerramento da sessao, com pergunta final opcional salva em `response`.

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
[x] 0.5.0 - Grid experimental para abrir/organizar gerenciador de arquivos, Chrome e terminal ao iniciar sessao
[x] 0.6.0 - Tiktak opcional ao iniciar sessao, pergunta final de encerramento e icone local da aplicacao
[x] 0.7.0 - Som local em loop durante a sessao usando `tick.wav`
[x] 0.8.0 - Suporte multiplataforma (Linux, macOS, Windows) com `afplay` no macOS e deteccao automatica de apps
```

---

## Licenca

Licenca ainda nao definida.
