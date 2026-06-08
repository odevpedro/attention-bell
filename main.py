import array
import json
import math
import shutil
import subprocess
import tempfile
import wave
import tkinter as tk
from pathlib import Path
from tkinter import messagebox
from datetime import datetime

try:
    import winsound
except ImportError:  # pragma: no cover - not available on non-Windows platforms
    winsound = None


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
    "window_grid_enabled": True,
    "tiktak_enabled": True,
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
    data["window_grid_enabled"] = bool(data["window_grid_enabled"])
    data["tiktak_enabled"] = bool(data["tiktak_enabled"])
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
        self.session_sound_path = self.resolve_session_sound()
        self.session_sound_process = None
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
        self.configure_window_icon()
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
        self.stop_tiktak()
        self.running = False
        self.paused = False
        self.clear()
        self.label("O que voce vai fazer agora?", font=("TkDefaultFont", 16, "bold"))
        self.label(
            "Defina uma intencao curta para esta sessao. Ela fica somente em memoria.",
            wraplength=460,
        ).pack(pady=(8, 14))
        self.intent_entry = tk.Entry(self.frame, font=("TkDefaultFont", 12), takefocus=1)
        self.intent_entry.pack(fill="x")
        self.intent_entry.focus_set()
        self.intent_entry.bind("<Return>", lambda _event: self.start_session())
        self.intent_entry.bind("<Tab>", self.focus_next_widget)

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
        self.stop_tiktak()
        save_history(self.current_intention, event_type="session_start")
        self.prepare_workspace()
        self.show_session()
        self.play_tiktak()
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
            field = tk.Text(frame, height=3, wrap="word", takefocus=1)
            field.pack(fill="x")
            field.bind("<Tab>", self.focus_next_widget)
            field.bind("<ISO_Left_Tab>", self.focus_previous_widget)
            field.bind("<Shift-Tab>", self.focus_previous_widget)
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
                    response = record.get("response")
                    if isinstance(response, dict):
                        text.insert("end", self.format_response(response))
                        text.insert("end", "\n")
                    elif response:
                        text.insert("end", f"Fechamento: {response}\n\n")
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

    def ask_text(self, title, prompt, initial="", allow_empty=False):
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
            if value or allow_empty:
                result["value"] = value
                dialog.destroy()
            else:
                messagebox.showinfo(APP_NAME, "Digite uma intencao.")

        tk.Button(frame, text="Salvar", command=confirm).pack(side="left", pady=(16, 0))
        tk.Button(frame, text="Cancelar", command=dialog.destroy).pack(side="left", padx=(8, 0), pady=(16, 0))
        dialog.bind("<Return>", lambda _event: confirm())
        self.root.wait_window(dialog)
        return result["value"]

    def play_tiktak(self):
        if not self.config["tiktak_enabled"] or not self.running:
            return
        if self.session_sound_process and hasattr(self.session_sound_process, "poll") and self.session_sound_process.poll() is None:
            return
        if not self.session_sound_path or not self.session_sound_path.exists():
            return
        if winsound and self.session_sound_path.suffix.lower() == ".wav":
            try:
                winsound.PlaySound(
                    str(self.session_sound_path),
                    winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP,
                )
                self.session_sound_process = object()
                return
            except RuntimeError:
                pass

        commands = (
            ("play", ["-q", str(self.session_sound_path), "repeat", "999999"]),
            ("aplay", ["-q", str(self.session_sound_path)]),
            ("afplay", [str(self.session_sound_path)]),
        )
        for command, args in commands:
            executable = shutil.which(command)
            if not executable:
                continue
            try:
                if command == "afplay":
                    self.session_sound_process = subprocess.Popen(
                        ["bash", "-c", f'while true; do afplay "{self.session_sound_path}"; done'],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                else:
                    self.session_sound_process = subprocess.Popen(
                        [executable, *args],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                return
            except OSError:
                self.session_sound_process = None
                continue

        self.root.after(0, self.root.bell)

    def stop_tiktak(self):
        if winsound:
            try:
                winsound.PlaySound(None, winsound.SND_PURGE)
            except RuntimeError:
                pass
        process = self.session_sound_process
        self.session_sound_process = None
        if process and hasattr(process, "poll") and process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=1)
            except (OSError, subprocess.SubprocessError, TimeoutError):
                try:
                    process.kill()
                except OSError:
                    pass

    def focus_next_widget(self, event):
        next_widget = event.widget.tk_focusNext()
        if next_widget:
            next_widget.focus_set()
        return "break"

    def focus_previous_widget(self, event):
        previous_widget = event.widget.tk_focusPrev()
        if previous_widget:
            previous_widget.focus_set()
        return "break"

    def resolve_session_sound(self):
        loop_sound = Path(__file__).with_name("tick2.wav")
        source_sound = Path(__file__).with_name("tick.wav")
        if source_sound.exists():
            try:
                looped = self.build_loop_audio(source_sound, loop_sound)
                if looped:
                    return loop_sound
            except OSError:
                pass
        for filename in ("tick.wav", "tick.mp3"):
            local_sound = Path(__file__).with_name(filename)
            if local_sound.exists():
                return local_sound
        return self.build_tiktak_audio()

    def build_loop_audio(self, source_path, output_path):
        try:
            with wave.open(str(source_path), "rb") as source_file:
                params = source_file.getparams()
                if params.sampwidth != 2:
                    return None
                raw_frames = source_file.readframes(source_file.getnframes())
            samples = array.array("h")
            samples.frombytes(raw_frames)
            if samples.itemsize != 2:
                return None
            frame_count = len(samples) // max(1, params.nchannels)
            threshold = 256
            start_frame = 0
            for frame_index in range(frame_count):
                frame_offset = frame_index * params.nchannels
                frame = samples[frame_offset : frame_offset + params.nchannels]
                if any(abs(sample) >= threshold for sample in frame):
                    start_frame = frame_index
                    break
            frames_to_copy = min(int(params.framerate * 2), frame_count - start_frame)
            start_sample = start_frame * params.nchannels
            end_sample = start_sample + frames_to_copy * params.nchannels
            frames = samples[start_sample:end_sample].tobytes()
            with wave.open(str(output_path), "wb") as output_file:
                output_file.setnchannels(params.nchannels)
                output_file.setsampwidth(params.sampwidth)
                output_file.setframerate(params.framerate)
                output_file.setcomptype(params.comptype, params.compname)
                output_file.writeframes(frames)
            return output_path
        except (OSError, wave.Error, ValueError):
            return None

    def build_tiktak_audio(self):
        path = Path(tempfile.gettempdir()) / "attention-bell-tiktak.wav"
        try:
            sample_rate = 44100
            segments = (
                (1200.0, 0.12),
                (0.0, 0.05),
                (820.0, 0.12),
                (0.0, 0.05),
                (1200.0, 0.12),
                (0.0, 0.05),
                (820.0, 0.12),
                (0.0, 0.05),
            )
            amplitude = 0.9
            frames = bytearray()
            for frequency, duration in segments:
                sample_count = int(sample_rate * duration)
                for index in range(sample_count):
                    if frequency:
                        sample = math.sin(2 * math.pi * frequency * (index / sample_rate))
                    else:
                        sample = 0.0
                    value = int(32767 * amplitude * sample)
                    frames.extend(value.to_bytes(2, byteorder="little", signed=True))
            with wave.open(str(path), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(bytes(frames))
            return path
        except (OSError, wave.Error, ValueError):
            return None

    def configure_window_icon(self):
        icon_path = Path(__file__).with_name("app-icon.xbm")
        if icon_path.exists():
            try:
                self.root.iconbitmap(f"@{icon_path}")
                return
            except tk.TclError:
                pass
        try:
            img = tk.PhotoImage(file=str(Path(__file__).with_name("app-icon.png")))
            self.root.tk.call("wm", "iconphoto", self.root._w, img)
        except (tk.TclError, Exception):
            pass

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
        dialog = self.dialog("Configuracao", 430, 380)
        frame = tk.Frame(dialog, padx=18, pady=18)
        frame.pack(fill="both", expand=True)
        timer = tk.StringVar(value=str(self.config["timer_interval_minutes"]))
        snooze = tk.StringVar(value=str(self.config["snooze_interval_minutes"]))
        overlay = tk.BooleanVar(value=self.config["overlay_enabled"])
        tiktak = tk.BooleanVar(value=self.config["tiktak_enabled"])
        window_grid = tk.BooleanVar(value=self.config["window_grid_enabled"])

        for text, var in (("Intervalo principal em minutos", timer), ("Adiamento em minutos", snooze)):
            tk.Label(frame, text=text, anchor="w").pack(fill="x")
            tk.Entry(frame, textvariable=var).pack(fill="x", pady=(4, 12))
        tk.Checkbutton(frame, text="Usar overlay visual suave", variable=overlay).pack(anchor="w")
        tk.Checkbutton(frame, text="Tiktak ao iniciar sessao", variable=tiktak).pack(anchor="w")
        tk.Checkbutton(frame, text="Organizar Chrome e terminal ao iniciar sessao", variable=window_grid).pack(
            anchor="w"
        )
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
                    "tiktak_enabled": tiktak.get(),
                    "window_grid_enabled": window_grid.get(),
                }
            )
            save_config(self.config)
            dialog.destroy()
            self.session_sound_path = self.resolve_session_sound()
            if self.running:
                self.stop_tiktak()
                if self.config["tiktak_enabled"]:
                    self.play_tiktak()
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
        self.cancel_timer()
        self.stop_tiktak()
        if self.current_intention:
            closing_note = self.ask_text(
                "Encerrar sessao",
                f"O que voce quer registrar ao encerrar a sessao de \"{self.current_intention}\"?",
                allow_empty=True,
            )
            if closing_note is None:
                closing_note = ""
            save_history(self.current_intention, response=closing_note, event_type="session_ended")
        self.current_intention = ""
        self.running = False
        self.paused = False
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

    def prepare_workspace(self):
        if not self.config["window_grid_enabled"]:
            return
        self.ensure_workspace_apps()
        self.root.after(1200, self.arrange_workspace)

    def ensure_workspace_apps(self):
        if not self.process_running(("chrome", "chromium", "Google Chrome")):
            self.launch_first_available(("google-chrome-stable", "google-chrome", "chromium", "chromium-browser", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"))
        if not self.process_running(("konsole", "gnome-terminal", "kitty", "alacritty", "xfce4-terminal", "xterm", "Terminal", "iTerm2")):
            self.launch_first_available(("konsole", "gnome-terminal", "kitty", "alacritty", "xfce4-terminal", "xterm", "Terminal", "iTerm"))
        if not self.process_running(("dolphin", "nautilus", "thunar", "nemo", "pcmanfm", "Finder")):
            self.launch_first_available(("dolphin", "nautilus", "thunar", "nemo", "pcmanfm", "open"))

    def process_running(self, patterns):
        try:
            output = subprocess.run(
                ["pgrep", "-af", "|".join(patterns)],
                capture_output=True,
                check=False,
                text=True,
                timeout=2,
            ).stdout.lower()
        except (OSError, subprocess.SubprocessError):
            return False
        return any(pattern in output for pattern in patterns)

    def launch_first_available(self, commands):
        for command in commands:
            path = shutil.which(command)
            if not path:
                continue
            try:
                subprocess.Popen([path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            except OSError:
                continue
        return False

    def arrange_workspace(self):
        if self.arrange_workspace_kwin():
            return
        if not shutil.which("wmctrl"):
            return
        try:
            windows = subprocess.run(
                ["wmctrl", "-lx"],
                capture_output=True,
                check=True,
                text=True,
                timeout=2,
            ).stdout.splitlines()
        except (OSError, subprocess.SubprocessError):
            return

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        right_x = screen_w // 2
        right_w = screen_w - right_x
        left_w = right_x
        top_h = screen_h // 2
        bottom_h = screen_h - top_h
        placements = (
            (("dolphin", "nautilus", "thunar", "nemo", "pcmanfm"), (0, 0, left_w, screen_h)),
            (("google-chrome", "chromium", "chrome"), (right_x, 0, right_w, top_h)),
            (
                (
                    "gnome-terminal",
                    "konsole",
                    "org.gnome.terminal",
                    "kitty",
                    "alacritty",
                    "xfce4-terminal",
                    "xterm",
                    "tilix",
                    "terminator",
                ),
                (right_x, top_h, right_w, bottom_h),
            ),
        )

        for patterns, geometry in placements:
            window_id = self.find_window_id(windows, patterns)
            if window_id:
                self.place_window(window_id, geometry)

    def find_window_id(self, windows, patterns):
        for line in windows:
            parts = line.split(None, 4)
            if len(parts) < 5:
                continue
            window_id, _desktop, _pid, wm_class, title = parts
            haystack = f"{wm_class} {title}".lower()
            if any(pattern in haystack for pattern in patterns):
                return window_id
        return None

    def place_window(self, window_id, geometry):
        x, y, width, height = geometry
        try:
            subprocess.run(
                ["wmctrl", "-ir", window_id, "-b", "remove,maximized_vert,maximized_horz"],
                check=False,
                timeout=2,
            )
            subprocess.run(
                ["wmctrl", "-ir", window_id, "-e", f"0,{x},{y},{width},{height}"],
                check=False,
                timeout=2,
            )
        except (OSError, subprocess.SubprocessError):
            return

    def arrange_workspace_kwin(self):
        if not shutil.which("qdbus"):
            return False
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        script = self.kwin_grid_script(screen_w, screen_h)
        try:
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as script_file:
                script_file.write(script)
                script_path = script_file.name
            plugin_name = "attention-bell-grid"
            subprocess.run(
                ["qdbus", "org.kde.KWin", "/Scripting", "org.kde.kwin.Scripting.unloadScript", plugin_name],
                check=False,
                timeout=2,
            )
            subprocess.run(
                ["qdbus", "org.kde.KWin", "/Scripting", "org.kde.kwin.Scripting.loadScript", script_path, plugin_name],
                check=True,
                timeout=2,
            )
            subprocess.run(
                ["qdbus", "org.kde.KWin", "/Scripting", "org.kde.kwin.Scripting.start"],
                check=True,
                timeout=2,
            )
            return True
        except (OSError, subprocess.SubprocessError):
            return False

    def kwin_grid_script(self, screen_w, screen_h):
        right_x = screen_w // 2
        right_w = screen_w - right_x
        left_w = right_x
        top_h = screen_h // 2
        bottom_h = screen_h - top_h
        return f"""
const rightX = {right_x};
const rightW = {right_w};
const leftW = {left_w};
const topH = {top_h};
const bottomH = {bottom_h};
const screenH = {screen_h};

function textOf(window) {{
    return [
        window.resourceClass || "",
        window.resourceName || "",
        window.caption || ""
    ].join(" ").toLowerCase();
}}

function findWindow(patterns) {{
    const windows = workspace.windowList();
    for (let i = windows.length - 1; i >= 0; i--) {{
        const haystack = textOf(windows[i]);
        for (let j = 0; j < patterns.length; j++) {{
            if (haystack.indexOf(patterns[j]) >= 0) {{
                return windows[i];
            }}
        }}
    }}
    return null;
}}

function place(window, x, y, width, height) {{
    if (!window) {{
        return;
    }}
    try {{ window.fullScreen = false; }} catch (error) {{}}
    try {{ window.minimized = false; }} catch (error) {{}}
    try {{ window.maximized = false; }} catch (error) {{}}
    try {{ window.frameGeometry = {{x: x, y: y, width: width, height: height}}; }} catch (error) {{}}
    try {{ workspace.activeWindow = window; }} catch (error) {{}}
}}

const chrome = findWindow(["google-chrome", "chromium", "chrome"]);
const terminal = findWindow(["konsole", "gnome-terminal", "kitty", "alacritty", "xfce4-terminal", "xterm", "tilix", "terminator"]);
const fileManager = findWindow(["dolphin", "nautilus", "thunar", "nemo", "pcmanfm"]);

place(fileManager, 0, 0, leftW, screenH);
place(chrome, rightX, 0, rightW, topH);
place(terminal, rightX, topH, rightW, bottomH);
"""


if __name__ == "__main__":
    root = tk.Tk()
    AttentionBell(root)
    root.mainloop()
