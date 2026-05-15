import json
import tkinter as tk
from pathlib import Path
from tkinter import messagebox
from datetime import datetime


APP_NAME = "Sino de Atencao"
CONFIG_PATH = Path(__file__).with_name("config.json")
HISTORY_PATH = Path(__file__).with_name("history.jsonl")
DEFAULT_CONFIG = {
    "timer_interval_minutes": 15,
    "snooze_interval_minutes": 5,
    "overlay_enabled": True,
    "overlay_color": "#FF0000",
    "overlay_opacity": 0.15,
    "overlay_pulses": 3,
}


def normalize(config):
    data = DEFAULT_CONFIG | {k: config[k] for k in DEFAULT_CONFIG if k in config}
    for key, fallback in {
        "timer_interval_minutes": 15,
        "snooze_interval_minutes": 5,
        "overlay_pulses": 3,
    }.items():
        try:
            data[key] = max(1, int(data[key]))
        except (TypeError, ValueError):
            data[key] = fallback
    try:
        data["overlay_opacity"] = min(0.35, max(0.01, float(data["overlay_opacity"])))
    except (TypeError, ValueError):
        data["overlay_opacity"] = 0.15
    data["overlay_enabled"] = bool(data["overlay_enabled"])
    data["overlay_color"] = str(data["overlay_color"] or "#FF0000")
    return data


def save_config(config):
    CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def load_config():
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    try:
        return normalize(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError):
        messagebox.showwarning(APP_NAME, "config.json invalido. Usando valores padrao.")
        return DEFAULT_CONFIG.copy()


def save_history(intention, response="", event_type="check_in", previous_intention=""):
    saved_response = response.strip() if isinstance(response, str) else response
    record = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "event_type": event_type,
        "intention": intention,
        "response": saved_response,
    }
    if previous_intention:
        record["previous_intention"] = previous_intention
    with HISTORY_PATH.open("a", encoding="utf-8") as history_file:
        history_file.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_history():
    if not HISTORY_PATH.exists():
        return []
    records = []
    for line in HISTORY_PATH.read_text(encoding="utf-8").splitlines():
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


class AttentionBell:
    def __init__(self, root):
        self.root = root
        self.config = load_config()
        self.current_intention = ""
        self.timer_id = None
        self.paused = False
        self.running = False
        self.alert = None
        self.overlay = None

        root.title(APP_NAME)
        root.geometry("520x360")
        root.minsize(440, 320)
        root.protocol("WM_DELETE_WINDOW", root.iconify)
        self.frame = tk.Frame(root, padx=22, pady=22)
        self.frame.pack(fill="both", expand=True)
        self.show_start()

    def clear(self):
        for child in self.frame.winfo_children():
            child.destroy()

    def label(self, text, **options):
        widget = tk.Label(self.frame, text=text, anchor="w", justify="left", **options)
        widget.pack(fill="x", anchor="w")
        return widget

    def show_start(self):
        self.cancel_timer()
        self.running = False
        self.paused = False
        self.clear()
        self.label("O que voce vai fazer agora?", font=("TkDefaultFont", 16, "bold"))
        self.label(
            "Defina uma intencao curta para esta sessao. Ela fica somente em memoria.",
            wraplength=460,
        ).pack(pady=(8, 14))
        self.intent_entry = tk.Entry(self.frame, font=("TkDefaultFont", 12))
        self.intent_entry.pack(fill="x")
        self.intent_entry.focus_set()
        self.intent_entry.bind("<Return>", lambda _event: self.start_session())

        buttons = tk.Frame(self.frame)
        buttons.pack(fill="x", pady=(18, 0))
        tk.Button(buttons, text="Comecar", command=self.start_session).pack(side="left")
        tk.Button(buttons, text="Configurar intervalo", command=self.open_settings).pack(
            side="left", padx=(8, 0)
        )
        tk.Button(buttons, text="Ver historico", command=self.show_history).pack(side="left", padx=(8, 0))
        tk.Button(buttons, text="Sair", command=self.root.destroy).pack(side="left", padx=(8, 0))

        self.label(
            "Privacidade: este app nao monitora atividade, nao captura tela, nao registra "
            "teclado, nao analisa janelas e nao envia dados. O historico fica apenas em arquivo local.",
            wraplength=460,
        ).pack(side="bottom")

    def show_session(self):
        self.clear()
        self.label("Sessao em andamento", font=("TkDefaultFont", 16, "bold"))
        self.label(self.current_intention, font=("TkDefaultFont", 12, "bold"), wraplength=460).pack(
            pady=(10, 18)
        )
        self.status = self.label(self.status_text())
        buttons = tk.Frame(self.frame)
        buttons.pack(anchor="w", pady=(18, 0))
        self.pause_button = tk.Button(buttons, text="Pausar", command=self.toggle_pause)
        self.pause_button.pack(side="left")
        tk.Button(buttons, text="Ajustar intencao", command=self.adjust_intention).pack(
            side="left", padx=(8, 0)
        )
        tk.Button(buttons, text="Configurar intervalo", command=self.open_settings).pack(
            side="left", padx=(8, 0)
        )
        tk.Button(buttons, text="Ver historico", command=self.show_history).pack(side="left", padx=(8, 0))
        tk.Button(buttons, text="Encerrar sessao", command=self.end_session).pack(
            side="left", padx=(8, 0)
        )
        self.label("Ao fechar a janela, o app minimiza.", wraplength=460).pack(side="bottom")

    def start_session(self):
        intention = self.intent_entry.get().strip()
        if not intention:
            messagebox.showinfo(APP_NAME, "Digite uma intencao antes de iniciar.")
            return
        self.current_intention = intention
        self.running = True
        self.paused = False
        save_history(self.current_intention, event_type="session_start")
        self.show_session()
        self.schedule(self.config["timer_interval_minutes"])

    def schedule(self, minutes):
        self.cancel_timer()
        if self.running and not self.paused:
            self.timer_id = self.root.after(int(minutes * 60 * 1000), self.trigger_alert)
        self.update_status()

    def cancel_timer(self):
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None

    def trigger_alert(self):
        self.timer_id = None
        if not self.running or self.paused:
            return
        if self.config["overlay_enabled"]:
            self.show_overlay(lambda: self.root.after(150, self.show_alert))
        else:
            self.show_alert()

    def show_overlay(self, done):
        if self.overlay and self.overlay.winfo_exists():
            self.overlay.destroy()
        overlay = tk.Toplevel(self.root)
        self.overlay = overlay
        overlay.overrideredirect(True)
        overlay.attributes("-topmost", True)
        overlay.attributes("-alpha", 0.0)
        overlay.configure(bg=self.config["overlay_color"])
        overlay.geometry(f"{overlay.winfo_screenwidth()}x{overlay.winfo_screenheight()}+0+0")

        max_alpha = self.config["overlay_opacity"]
        steps = 10
        total = self.config["overlay_pulses"] * steps * 2

        def animate(step=0):
            if not overlay.winfo_exists():
                return
            if step >= total:
                overlay.destroy()
                self.overlay = None
                done()
                return
            phase = step % (steps * 2)
            ratio = (phase + 1) / steps if phase < steps else 1 - ((phase - steps + 1) / steps)
            overlay.attributes("-alpha", max(0, max_alpha * ratio))
            overlay.after(35, animate, step + 1)

        animate()

    def show_alert(self):
        if self.alert and self.alert.winfo_exists():
            self.alert.lift()
            self.alert.focus_force()
            return
        self.force_attention()
        alert = self.dialog(APP_NAME, 620, 620)
        self.alert = alert
        frame = tk.Frame(alert, padx=22, pady=22)
        frame.pack(fill="both", expand=True)
        tk.Label(
            frame,
            text="Voce ainda esta fazendo o que decidiu fazer?",
            font=("TkDefaultFont", 14, "bold"),
            anchor="w",
            justify="left",
        ).pack(fill="x")
        tk.Label(
            frame,
            text=f'"{self.current_intention}"',
            font=("TkDefaultFont", 12, "bold"),
            fg="#9B0000",
            anchor="w",
            justify="left",
            wraplength=500,
        ).pack(fill="x", pady=(10, 16))
        response_fields = {}
        questions = (
            ("current_mind", "O que esta ocupando sua mente agora?"),
            ("alignment", "Isso ajuda ou desvia da intencao?"),
            ("next_action", "Qual e a proxima acao minima?"),
        )
        for key, question in questions:
            tk.Label(frame, text=question, anchor="w", justify="left").pack(fill="x", pady=(8, 2))
            field = tk.Text(frame, height=3, wrap="word")
            field.pack(fill="x")
            response_fields[key] = field
        response_fields["current_mind"].focus_set()

        buttons = tk.Frame(frame)
        buttons.pack(fill="x", side="bottom", pady=(18, 0))
        tk.Button(buttons, text="Continuar", command=lambda: self.close_alert(alert, "continue", response_fields)).pack(
            side="left"
        )
        tk.Button(buttons, text="Ajustar intencao", command=lambda: self.close_alert(alert, "adjust", response_fields)).pack(
            side="left", padx=(8, 0)
        )
        tk.Button(buttons, text="Encerrar sessao", command=lambda: self.close_alert(alert, "end", response_fields)).pack(
            side="left", padx=(8, 0)
        )
        tk.Button(buttons, text="Adiar", command=lambda: self.close_alert(alert, "snooze", response_fields)).pack(
            side="right"
        )
        alert.bind("<Escape>", lambda _event: self.close_alert(alert, "continue", response_fields))
        alert.protocol("WM_DELETE_WINDOW", lambda: self.close_alert(alert, "continue", response_fields))
        self.root.bell()
        alert.after(120, lambda: self.shake(alert, 620, 620))

    def close_alert(self, alert, action, response_widgets):
        response = {}
        for key, widget in response_widgets.items():
            response[key] = widget.get("1.0", "end").strip() if widget.winfo_exists() else ""
        save_history(self.current_intention, response, "check_in")
        if alert.winfo_exists():
            alert.grab_release()
            alert.destroy()
        self.alert = None
        if action == "continue":
            self.schedule(self.config["timer_interval_minutes"])
        elif action == "snooze":
            save_history(self.current_intention, event_type="snoozed")
            self.schedule(self.config["snooze_interval_minutes"])
        elif action == "adjust":
            self.adjust_intention()
        elif action == "end":
            self.end_session()

    def show_history(self):
        records = load_history()
        dialog = self.dialog("Historico local", 680, 500)
        frame = tk.Frame(dialog, padx=18, pady=18)
        frame.pack(fill="both", expand=True)
        tk.Label(
            frame,
            text=f"Historico local: {HISTORY_PATH.name}",
            font=("TkDefaultFont", 13, "bold"),
            anchor="w",
        ).pack(fill="x")
        text = tk.Text(frame, wrap="word", height=20)
        text.pack(fill="both", expand=True, pady=(12, 12))
        if not records:
            text.insert("end", "Nenhum registro ainda.\n")
        else:
            for record in reversed(records):
                event_type = record.get("event_type", "check_in")
                text.insert("end", f"{record.get('created_at', '')}\n")
                if event_type == "session_start":
                    text.insert("end", "Evento: inicio de sessao\n")
                    text.insert("end", f"Intencao: {record.get('intention', '')}\n\n")
                elif event_type == "intention_adjusted":
                    text.insert("end", "Evento: ajuste de intencao\n")
                    text.insert("end", f"Antes: {record.get('previous_intention', '')}\n")
                    text.insert("end", f"Depois: {record.get('intention', '')}\n\n")
                elif event_type == "session_ended":
                    text.insert("end", "Evento: encerramento de sessao\n")
                    text.insert("end", f"Intencao: {record.get('intention', '')}\n\n")
                elif event_type == "snoozed":
                    text.insert("end", "Evento: adiamento\n")
                    text.insert("end", f"Intencao: {record.get('intention', '')}\n\n")
                else:
                    text.insert("end", "Evento: check-in\n")
                    text.insert("end", f"Intencao: {record.get('intention', '')}\n")
                    text.insert("end", self.format_response(record.get("response")))
                    text.insert("end", "\n")
        text.configure(state="disabled")

        def clear_history():
            if not messagebox.askyesno(APP_NAME, "Apagar todo o historico local?"):
                return
            HISTORY_PATH.unlink(missing_ok=True)
            dialog.destroy()

        tk.Button(frame, text="Limpar historico", command=clear_history).pack(side="left")
        tk.Button(frame, text="Fechar", command=dialog.destroy).pack(side="left", padx=(8, 0))

    def format_response(self, response):
        if isinstance(response, dict):
            current_mind = response.get("current_mind") or "(sem resposta escrita)"
            alignment = response.get("alignment") or "(sem resposta escrita)"
            next_action = response.get("next_action") or "(sem resposta escrita)"
            return (
                f"O que ocupa a mente: {current_mind}\n"
                f"Ajuda ou desvia: {alignment}\n"
                f"Proxima acao minima: {next_action}\n"
            )
        return f"Resposta: {response or '(sem resposta escrita)'}\n"

    def ask_text(self, title, prompt, initial=""):
        dialog = self.dialog(title, 480, 180)
        frame = tk.Frame(dialog, padx=18, pady=18)
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text=prompt, anchor="w").pack(fill="x")
        entry = tk.Entry(frame)
        entry.pack(fill="x", pady=(10, 0))
        entry.insert(0, initial)
        entry.select_range(0, "end")
        entry.focus_set()
        result = {"value": None}

        def confirm():
            value = entry.get().strip()
            if value:
                result["value"] = value
                dialog.destroy()
            else:
                messagebox.showinfo(APP_NAME, "Digite uma intencao.")

        tk.Button(frame, text="Salvar", command=confirm).pack(side="left", pady=(16, 0))
        tk.Button(frame, text="Cancelar", command=dialog.destroy).pack(side="left", padx=(8, 0), pady=(16, 0))
        dialog.bind("<Return>", lambda _event: confirm())
        self.root.wait_window(dialog)
        return result["value"]

    def adjust_intention(self):
        value = self.ask_text("Ajustar intencao", "Qual e a intencao agora?", self.current_intention)
        if value is None:
            if self.running and not self.paused and not self.timer_id:
                self.schedule(self.config["timer_interval_minutes"])
            return
        previous = self.current_intention
        self.current_intention = value
        self.running = True
        self.paused = False
        save_history(self.current_intention, event_type="intention_adjusted", previous_intention=previous)
        self.show_session()
        self.schedule(self.config["timer_interval_minutes"])

    def open_settings(self):
        dialog = self.dialog("Configuracao", 430, 300)
        frame = tk.Frame(dialog, padx=18, pady=18)
        frame.pack(fill="both", expand=True)
        timer = tk.StringVar(value=str(self.config["timer_interval_minutes"]))
        snooze = tk.StringVar(value=str(self.config["snooze_interval_minutes"]))
        overlay = tk.BooleanVar(value=self.config["overlay_enabled"])

        for text, var in (("Intervalo principal em minutos", timer), ("Adiamento em minutos", snooze)):
            tk.Label(frame, text=text, anchor="w").pack(fill="x")
            tk.Entry(frame, textvariable=var).pack(fill="x", pady=(4, 12))
        tk.Checkbutton(frame, text="Usar overlay visual suave", variable=overlay).pack(anchor="w")
        tk.Label(
            frame,
            text="Nota: desative o overlay se tiver sensibilidade visual.",
            anchor="w",
            justify="left",
            wraplength=380,
        ).pack(fill="x", pady=(12, 0))

        def save():
            self.config = normalize(
                self.config
                | {
                    "timer_interval_minutes": timer.get(),
                    "snooze_interval_minutes": snooze.get(),
                    "overlay_enabled": overlay.get(),
                }
            )
            save_config(self.config)
            dialog.destroy()
            if self.running and not self.paused:
                self.schedule(self.config["timer_interval_minutes"])
            self.update_status()

        tk.Button(frame, text="Salvar", command=save).pack(side="left", pady=(16, 0))
        tk.Button(frame, text="Cancelar", command=dialog.destroy).pack(side="left", padx=(8, 0), pady=(16, 0))

    def toggle_pause(self):
        self.paused = not self.paused
        if self.paused:
            self.cancel_timer()
        else:
            self.schedule(self.config["timer_interval_minutes"])
        self.pause_button.configure(text="Retomar" if self.paused else "Pausar")
        self.update_status()

    def end_session(self):
        if self.current_intention:
            save_history(self.current_intention, event_type="session_ended")
        self.current_intention = ""
        self.show_start()

    def status_text(self):
        return "Timer pausado." if self.paused else f"Proximo sino em {self.config['timer_interval_minutes']} minuto(s)."

    def update_status(self):
        if hasattr(self, "status") and self.status.winfo_exists():
            self.status.configure(text=self.status_text())

    def dialog(self, title, width, height):
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.geometry(f"{width}x{height}")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.attributes("-topmost", True)
        x = (dialog.winfo_screenwidth() - width) // 2
        y = (dialog.winfo_screenheight() - height) // 2
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        dialog.lift()
        dialog.focus_force()
        dialog.after(250, lambda: dialog.attributes("-topmost", False))
        return dialog

    def force_attention(self):
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.focus_force()
        self.root.after(500, lambda: self.root.attributes("-topmost", False))

    def shake(self, window, width, height):
        if not window.winfo_exists():
            return
        base_x = (window.winfo_screenwidth() - width) // 2
        base_y = (window.winfo_screenheight() - height) // 2
        offsets = [0, -18, 18, -14, 14, -9, 9, -4, 4, 0]

        def step(index=0):
            if not window.winfo_exists() or index >= len(offsets):
                return
            window.geometry(f"{width}x{height}+{base_x + offsets[index]}+{base_y}")
            window.lift()
            window.focus_force()
            window.after(35, step, index + 1)

        step()


if __name__ == "__main__":
    root = tk.Tk()
    AttentionBell(root)
    root.mainloop()
