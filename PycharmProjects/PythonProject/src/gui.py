
import os
import re
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk

from .data_pipeline import FEATURES, RANGES
from .fuzzy_systems import MamdaniSystem, SugenoSystem

VAR_LABELS = {
    "utilization":        ("Загрузка оборудования", "%", "на сколько процентов загружены станки и линии"),
    "defect_rate":        ("Уровень брака", "%", "какая доля произведенной продукции оказалась браком"),
    "downtime_pct":       ("Простои", "% времени", "сколько рабочего времени оборудование стоит"),
    "overdue_orders":     ("Просроченные заказы", "шт.", "сколько заказов не сдано в срок"),
    "staff_availability": ("Доступность персонала", "%", "сколько сотрудников реально вышло на смену"),
    "energy_overrun":     ("Перерасход энергии", "%", "на сколько энергии израсходовано больше нормы"),
}

VAR_TERMS_RU = {
    "utilization":        {"low": "загрузка низкая",   "normal": "загрузка нормальная", "high": "загрузка высокая"},
    "defect_rate":        {"low": "брак низкий",       "medium": "брак средний",       "high": "брак высокий"},
    "downtime_pct":       {"low": "простоев мало",     "medium": "простоев средне",    "high": "простоев много"},
    "overdue_orders":     {"low": "заказов в срок",    "medium": "заказов просрочено средне", "high": "просрочек много"},
    "staff_availability": {"low": "персонала мало",    "medium": "персонала хватает",  "high": "персонала в достатке"},
    "energy_overrun":     {"low": "энергия в норме",   "medium": "энергия расходуется сверх нормы", "high": "сильный перерасход энергии"},
}

RISK_RU = {
    "low":      ("Низкий",      "#2e9e5b", "Работа в штатном режиме. Существенных угроз нет."),
    "moderate": ("Умеренный",   "#e8a13a", "Есть отдельные проблемные места. Стоит держать их под контролем."),
    "high":     ("Высокий",     "#e05d38", "Риск серьезный. Рекомендуется план мероприятий на ближайшую неделю."),
    "critical": ("Критический", "#c0392b", "Ситуация опасная. Нужны немедленные действия руководства."),
}

ADVICE = {
    "low":      "• продолжать работать в текущем режиме\n• пересматривать оценку раз в месяц",
    "moderate": "• разобраться с самым слабым показателем из списка выше\n• усилить контроль качества и сроков\n• повторить оценку через неделю",
    "high":     "• составить план корректирующих мероприятий\n• сократить простои и просроченные заказы\n• доложить руководству и повторить оценку через 2–3 дня",
    "critical": "• немедленно доложить руководству\n• остановить или ограничить самые опасные участки\n• ввести ежедневный контроль всех показателей",
}

PRESETS = {
    "Спокойная работа": {
        "utilization": 82, "defect_rate": 2, "downtime_pct": 4,
        "overdue_orders": 3, "staff_availability": 95, "energy_overrun": 2,
    },
    "Напряженный режим": {
        "utilization": 100, "defect_rate": 6, "downtime_pct": 12,
        "overdue_orders": 15, "staff_availability": 80, "energy_overrun": 10,
    },
    "Аварийная ситуация": {
        "utilization": 115, "defect_rate": 11, "downtime_pct": 24,
        "overdue_orders": 30, "staff_availability": 65, "energy_overrun": 20,
    },
}

BG = "#f4f6fa"
CARD = "#ffffff"
ACCENT = "#2f6fed"
TEXT = "#1f2733"


def clean_report_text(text: str) -> str:
    """Убирает из отчета служебные знаки = и - (разделители pytest)."""
    lines = []
    for line in text.replace("\r", "").split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if re.fullmatch(r"[=\-\s]+", stripped):
            continue
        line = line.replace("=", " ").replace("-", " ")
        line = re.sub(r" {2,}", " ", line).rstrip()
        lines.append(line)
    return "\n".join(lines)


class RiskApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Калькулятор производственного риска цеха")
        self.geometry("1080x800")
        self.configure(bg=BG)

        self.mamdani = MamdaniSystem()
        self.sugeno = SugenoSystem()
        self.entries = {}

        self._setup_styles()

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=14, pady=14)

        self.tab_calc = ttk.Frame(self.notebook)
        self.tab_graphs = ttk.Frame(self.notebook)
        self.tab_info = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_calc, text="  Калькулятор риска  ")
        self.notebook.add(self.tab_graphs, text="  Графики и анализ  ")
        self.notebook.add(self.tab_info, text="  Отчет и тесты  ")

        self._build_calc_tab()
        self._build_graphs_tab()
        self._build_info_tab()

    def _setup_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=CARD)
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", font=("Segoe UI", 11), padding=(14, 8))
        style.configure("TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Card.TLabel", background=CARD, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Hint.TLabel", background=CARD, foreground="#6b7684", font=("Segoe UI", 9))
        style.configure("Title.TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 16, "bold"))
        style.configure("Subtitle.TLabel", background=BG, foreground="#6b7684", font=("Segoe UI", 10))
        style.configure("TEntry", font=("Segoe UI", 11), padding=4)
        style.configure("TButton", font=("Segoe UI", 10), padding=(12, 7))
        style.configure("Accent.TButton", font=("Segoe UI", 11, "bold"),
                        foreground="#ffffff", background=ACCENT, borderwidth=0)
        style.map("Accent.TButton", background=[("active", "#255bcc")])
        style.configure("TLabelframe", background=BG)
        style.configure("TLabelframe.Label", background=BG, foreground=TEXT,
                        font=("Segoe UI", 10, "bold"))

    def _build_calc_tab(self):
        ttk.Label(self.tab_calc, text="Оценка производственного риска",
                  style="Title.TLabel").pack(anchor="w", padx=10, pady=(10, 0))
        ttk.Label(self.tab_calc,
                  text="Введите 6 показателей работы цеха — программа оценит риск по двум методам нечеткой логики.",
                  style="Subtitle.TLabel").pack(anchor="w", padx=10, pady=(0, 8))

        body = ttk.Frame(self.tab_calc)
        body.pack(fill="both", expand=True, padx=6, pady=6)

        left = ttk.Frame(body)
        left.pack(side="left", fill="y", padx=6)

        card_in = ttk.Frame(left, style="Card.TFrame", padding=14)
        card_in.pack(fill="both", expand=True)

        ttk.Label(card_in, text="Показатели за период", style="Card.TLabel",
                  font=("Segoe UI", 12, "bold")).grid(row=0, column=0, columnspan=3,
                                                      sticky="w", pady=(0, 10))

        for i, var in enumerate(FEATURES, start=1):
            label, unit, hint = VAR_LABELS[var]
            lo, hi = RANGES[var]
            ttk.Label(card_in, text=label, style="Card.TLabel",
                      font=("Segoe UI", 10, "bold")).grid(row=i, column=0, sticky="w", pady=5)
            ttk.Label(card_in, text=f"{unit}, допустимо от {lo:g} до {hi:g}",
                      style="Hint.TLabel").grid(row=i, column=1, sticky="w", padx=(10, 4))
            e = ttk.Entry(card_in, width=9)
            e.grid(row=i, column=2, padx=(6, 0), pady=5)
            self.entries[var] = e

        r0 = len(FEATURES) + 1
        ttk.Label(card_in,
                  text="Подсказка: данные берутся из сменного отчета или системы учета.",
                  style="Hint.TLabel").grid(row=r0, column=0, columnspan=3, sticky="w", pady=(10, 0))

        presets_frame = ttk.Frame(left)
        presets_frame.pack(fill="x", pady=10)
        ttk.Label(presets_frame, text="Быстрый пример:").pack(side="left", padx=(0, 6))
        for name, values in PRESETS.items():
            ttk.Button(presets_frame, text=name,
                       command=lambda v=values: self._fill_preset(v)).pack(side="left", padx=4)

        calc_btn = ttk.Button(left, text="Рассчитать риск", style="Accent.TButton",
                              command=self.on_calculate)
        calc_btn.pack(fill="x", pady=(0, 4))

        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True, padx=6)

        self.result_card = tk.Frame(right, bg=CARD, highlightbackground="#d8dee9",
                                    highlightthickness=1)
        self.result_card.pack(fill="both", expand=True)

        self.result_title = tk.Label(self.result_card,
                                     text="Здесь появится результат расчета",
                                     bg=CARD, fg=TEXT, font=("Segoe UI", 13, "bold"),
                                     anchor="w", justify="left", wraplength=440)
        self.result_title.pack(fill="x", padx=16, pady=(14, 4))

        self.result_badge = tk.Label(self.result_card, text="", bg=CARD,
                                     font=("Segoe UI", 15, "bold"))
        self.result_badge.pack(fill="x", padx=16)

        self.result_text = tk.Text(self.result_card, wrap="word", bg=CARD, fg=TEXT,
                                   font=("Segoe UI", 10), relief="flat", padx=16, pady=8)
        self.result_text.pack(fill="both", expand=True)

    def _fill_preset(self, values):
        for var, val in values.items():
            self.entries[var].delete(0, tk.END)
            self.entries[var].insert(0, str(val))

    def _read_inputs(self):
        inputs = {}
        for var, entry in self.entries.items():
            label = VAR_LABELS[var][0]
            raw = entry.get().strip().replace(",", ".")
            if not raw:
                raise ValueError(f"Заполните поле «{label}»")
            try:
                value = float(raw)
            except ValueError:
                raise ValueError(f"Поле «{label}»: нужно ввести число, например 85")
            lo, hi = RANGES[var]
            if not (lo <= value <= hi):
                raise ValueError(f"Поле «{label}»: значение должно быть от {lo:g} до {hi:g}")
            inputs[var] = value
        return inputs

    def _explain_rule(self, item):
        m = re.match(r"ЕСЛИ (.+) ТО риск = (\w+)", item["text"])
        if not m:
            return item["text"]
        cond_raw, risk_key = m.group(1), m.group(2)
        parts = []
        for part in cond_raw.split(" И "):
            pm = re.match(r"(\w+) = (НЕ )?(\w+)", part.strip())
            if pm:
                var, neg, term = pm.groups()
                ru = VAR_TERMS_RU.get(var, {}).get(term, term)
                parts.append(("нет: " if neg else "") + ru)
        risk_name = RISK_RU.get(risk_key, (risk_key,))[0].lower()
        strength = item["strength"]
        return ("Если " + ", ".join(parts) + f" — то риск {risk_name} "
                f"(влияние правила: {strength * 100:.0f}%)")

    def on_calculate(self):
        try:
            inputs = self._read_inputs()
        except ValueError as e:
            messagebox.showerror("Проверьте ввод", str(e))
            return

        try:
            m = self.mamdani.predict_with_details(inputs)
            s = self.sugeno.predict_with_details(inputs)
            diff = abs(m["score"] - s["score"])
        except Exception as e:
            messagebox.showerror("Ошибка расчета", f"Не удалось выполнить расчет.\n\n{e}")
            return

        category = m["category"]
        name, color, verdict = RISK_RU.get(category, (category, TEXT, ""))

        self.result_badge.config(text=f"Общая оценка: {name}  (индекс риска {m['score']:.0f} из 100)",
                                 fg=color)
        self.result_title.config(text=verdict)

        lines = [
            "Подробности расчета",
            "",
            f"Метод Мамдани:   индекс {m['score']:.1f} из 100, категория «{RISK_RU.get(m['category'], (m['category'],))[0]}»",
            f"Метод Сугено:    индекс {s['score']:.1f} из 100, категория «{RISK_RU.get(s['category'], (s['category'],))[0]}»",
            f"Разница методов: {diff:.1f} балла (чем меньше, тем увереннее оценка)",
            "",
            "Что влияет на риск больше всего (три главных сработавших правила):",
        ]
        for i, item in enumerate(m["explanation"], start=1):
            lines.append(f"{i}. {self._explain_rule(item)}")
        lines += ["", "Рекомендации:", ADVICE.get(category, "")]

        self.result_text.delete("1.0", tk.END)
        self.result_text.insert("1.0", "\n".join(lines))
        self.result_text.tag_config("head", font=("Segoe UI", 11, "bold"))
        self.result_text.tag_add("head", "1.0", "1.end")
        self.result_text.tag_add("head", "7.0", "7.end")

    def _build_graphs_tab(self):
        ttk.Label(self.tab_graphs, text="Результаты анализа данных (папка reports)",
                  style="Title.TLabel").pack(anchor="w", padx=10, pady=(10, 4))
        ttk.Label(self.tab_graphs,
                  text="Графики строятся автоматически при запуске программы. Выберите нужный из списка.",
                  style="Subtitle.TLabel").pack(anchor="w", padx=10)

        top = ttk.Frame(self.tab_graphs)
        top.pack(fill="x", padx=10, pady=8)

        self.graph_selector = ttk.Combobox(top, state="readonly", width=45, font=("Segoe UI", 10))
        self.graph_selector.pack(side="left")
        self.graph_selector.bind("<<ComboboxSelected>>", self._on_graph_select)

        ttk.Button(top, text="Обновить список", command=self._update_graph_list).pack(side="left", padx=8)
        ttk.Button(top, text="Открыть папку с результатами",
                   command=self._open_reports_folder).pack(side="left", padx=4)

        card = ttk.Frame(self.tab_graphs, style="Card.TFrame", padding=8)
        card.pack(fill="both", expand=True, padx=10, pady=8)

        self.img_label = ttk.Label(card, style="Card.TLabel")
        self.img_label.pack(fill="both", expand=True)

        self._update_graph_list()

    def _update_graph_list(self):
        if not os.path.exists("reports"):
            self.graph_selector["values"] = ["Папка reports еще не создана, идет расчет..."]
            return
        files = sorted(f for f in os.listdir("reports") if f.endswith(".png"))
        if not files:
            self.graph_selector["values"] = ["Графики еще строятся, подождите..."]
        else:
            self.graph_selector["values"] = files
            self.graph_selector.current(0)
            self._on_graph_select()

    def _on_graph_select(self, event=None):
        filename = self.graph_selector.get()
        path = os.path.join("reports", filename)
        if not filename or not os.path.exists(path):
            return
        img = Image.open(path)
        img.thumbnail((920, 560))
        self.photo = ImageTk.PhotoImage(img)
        self.img_label.config(image=self.photo)

    def _open_reports_folder(self):
        folder_path = os.path.abspath("reports")
        if not os.path.exists(folder_path):
            messagebox.showinfo("Информация", "Папка reports еще не создана. Дождитесь окончания расчетов.")
            return
        try:
            if sys.platform == "win32":
                os.startfile(folder_path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder_path])
            else:
                subprocess.Popen(["xdg-open", folder_path])
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть папку:\n{e}")

    def _build_info_tab(self):
        ttk.Label(self.tab_info, text="Проверка работы программы (тесты)",
                  style="Title.TLabel").pack(anchor="w", padx=10, pady=(10, 4))
        ttk.Label(self.tab_info,
                  text="Тесты проверяют расчет риска на контрольных сценариях. Отчет показывается без служебных разделителей.",
                  style="Subtitle.TLabel").pack(anchor="w", padx=10)

        btn_frame = ttk.Frame(self.tab_info)
        btn_frame.pack(fill="x", padx=10, pady=10)

        ttk.Button(btn_frame, text="Запустить тесты", style="Accent.TButton",
                   command=self._run_tests).pack(side="left", padx=(0, 8))
        ttk.Button(btn_frame, text="Сохранить отчет в файл",
                   command=self._save_report).pack(side="left", padx=4)

        card = ttk.Frame(self.tab_info, style="Card.TFrame", padding=8)
        card.pack(fill="both", expand=True, padx=10, pady=8)

        self.test_output = tk.Text(card, wrap="word", font=("Consolas", 10),
                                   bg=CARD, fg=TEXT, relief="flat", padx=8, pady=8)
        self.test_output.pack(fill="both", expand=True)
        self.test_output.insert("1.0", "Нажмите «Запустить тесты», чтобы проверить работу программы.")
        self._last_report = ""

    def _run_tests(self):
        self.test_output.delete("1.0", tk.END)
        self.test_output.insert("1.0", "Идет проверка, подождите...\n")
        self.update()

        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", "tests/"],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", cwd=project_dir, timeout=180,
            )
            raw = result.stdout + "\n" + result.stderr
        except FileNotFoundError:
            self._show_report_error("Не найден интерпретатор Python. Переустановите зависимости: pip install pytest")
            return
        except subprocess.TimeoutExpired:
            self._show_report_error("Тесты выполнялись слишком долго (более 3 минут) и были остановлены.")
            return
        except Exception as e:
            self._show_report_error(f"Не удалось запустить тесты:\n{e}")
            return

        cleaned = clean_report_text(raw)
        if not cleaned:
            cleaned = "Тесты запустились, но не вернули данных."

        summary = "Итог проверки: "
        passed = raw.count(" passed")
        failed = raw.count(" failed")
        errors = raw.count(" error")
        if failed or errors:
            summary += f"обнаружено проблем: {failed + errors}"
        elif passed:
            summary += "все тесты пройдены успешно"
        else:
            summary += "см. подробности ниже"

        self._last_report = summary + "\n\n" + cleaned
        self.test_output.delete("1.0", tk.END)
        self.test_output.insert("1.0", self._last_report)

    def _show_report_error(self, message):
        self._last_report = ""
        self.test_output.delete("1.0", tk.END)
        self.test_output.insert("1.0",
            "Проверка не запустилась.\n\n"
            + message
            + "\n\nЧто делать:\n"
              "1. Откройте терминал в папке проекта.\n"
              "2. Выполните команду: pip install pytest\n"
              "3. Запустите программу заново.")

    def _save_report(self):
        if not self._last_report.strip():
            messagebox.showinfo("Информация", "Сначала запустите тесты, затем сохраняйте отчет.")
            return
        os.makedirs("reports", exist_ok=True)
        path = os.path.join("reports", "otchet.txt")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("ОТЧЕТ О ПРОВЕРКЕ РАБОТЫ ПРОГРАММЫ\n")
                f.write(f"Дата и время: {__import__('datetime').datetime.now():%d.%m.%Y %H:%M}\n\n")
                f.write(self._last_report)
            messagebox.showinfo("Готово", f"Отчет сохранен:\n{os.path.abspath(path)}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить отчет:\n{e}")