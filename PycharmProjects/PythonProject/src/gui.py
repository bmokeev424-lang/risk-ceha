import tkinter as tk
from tkinter import messagebox, ttk
import os
import subprocess
import sys
from PIL import Image, ImageTk

from .data_pipeline import FEATURES, RANGES
from .fuzzy_systems import MamdaniSystem, SugenoSystem


class RiskApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Нечёткая оценка производственного риска")
        self.geometry("1000x750")
        self.configure(padx=10, pady=10)

        self.mamdani = MamdaniSystem()
        self.sugeno = SugenoSystem()
        self.entries = {}

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        self.tab_calc = ttk.Frame(self.notebook)
        self.tab_graphs = ttk.Frame(self.notebook)
        self.tab_info = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_calc, text="Калькулятор риска")
        self.notebook.add(self.tab_graphs, text="Графики и анализ")
        self.notebook.add(self.tab_info, text="Отчет и Тесты")

        self._build_calc_tab()
        self._build_graphs_tab()
        self._build_info_tab()

    def _build_calc_tab(self):
        frame_input = ttk.LabelFrame(self.tab_calc, text="Входные показатели")
        frame_input.pack(fill="x", padx=10, pady=10)

        for i, var in enumerate(FEATURES):
            lo, hi = RANGES[var]
            ttk.Label(frame_input, text=f"{var} [{lo}..{hi}]").grid(row=i, column=0, sticky="w", padx=5, pady=3)
            e = ttk.Entry(frame_input, width=15)
            e.grid(row=i, column=1, padx=5, pady=3)
            self.entries[var] = e

        btn = ttk.Button(frame_input, text="Рассчитать риск", command=self.on_calculate)
        btn.grid(row=len(FEATURES), column=0, columnspan=2, pady=10)

        frame_out = ttk.LabelFrame(self.tab_calc, text="Результаты")
        frame_out.pack(fill="both", expand=True, padx=10, pady=5)

        self.txt = tk.Text(frame_out, wrap="word", font=("Consolas", 11), padx=10, pady=10)
        self.txt.pack(fill="both", expand=True, padx=5, pady=5)

    def _read_inputs(self):
        inputs = {}
        for var, entry in self.entries.items():
            raw = entry.get().strip().replace(",", ".")
            if not raw:
                raise ValueError(f"Поле «{var}» не заполнено")
            try:
                value = float(raw)
            except ValueError:
                raise ValueError(f"Поле «{var}»: ожидается число")
            lo, hi = RANGES[var]
            if not (lo <= value <= hi):
                raise ValueError(f"Поле «{var}» вне диапазона [{lo}..{hi}]")
            inputs[var] = value
        return inputs

    def on_calculate(self):
        try:
            inputs = self._read_inputs()
        except ValueError as e:
            messagebox.showerror("Ошибка ввода", str(e))
            return

        try:
            m = self.mamdani.predict_with_details(inputs)
            s = self.sugeno.predict_with_details(inputs)
            diff = abs(m["score"] - s["score"])

            lines = []
            lines.append("РЕЗУЛЬТАТЫ РАСЧЕТА")
            lines.append("─" * 50)
            lines.append(f" • Метод Мамдани: Индекс {m['score']:.2f} | Категория: {m['category']}")
            lines.append(f" • Метод Сугено:  Индекс {s['score']:.2f} | Категория: {s['category']}")
            lines.append(f" • Абсолютное расхождение: {diff:.2f}")
            lines.append("")
            lines.append("НАИБОЛЕЕ АКТИВНЫЕ ПРАВИЛА (МАМДАНИ):")
            lines.append("─" * 50)

            for item in m["explanation"]:
                lines.append(f" [{item['rule']}] Сила срабатывания: {item['strength']:.3f}")
                lines.append(f" {item['text']}")
                lines.append("")

            self.txt.delete("1.0", tk.END)
            self.txt.insert("1.0", "\n".join(lines))
        except Exception as e:
            messagebox.showerror("Ошибка расчёта", f"Ошибка: {str(e)}")

    def _build_graphs_tab(self):
        ttk.Label(self.tab_graphs, text="Результаты анализа (папка reports):", font=("", 12, "bold")).pack(pady=5)

        self.graph_selector = ttk.Combobox(self.tab_graphs, state="readonly", width=40)
        self.graph_selector.pack(pady=5)
        self.graph_selector.bind("<<ComboboxSelected>>", self._on_graph_select)

        self.img_label = ttk.Label(self.tab_graphs)
        self.img_label.pack(fill="both", expand=True, pady=10)

        btn_frame = ttk.Frame(self.tab_graphs)
        btn_frame.pack(pady=5)

        ttk.Button(btn_frame, text="Обновить список", command=self._update_graph_list).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Открыть папку с результатами", command=self._open_reports_folder).pack(side="left",
                                                                                                           padx=5)

        self._update_graph_list()

    def _update_graph_list(self):
        if not os.path.exists("reports"):
            self.graph_selector['values'] = ["Папка reports еще не создана."]
            return

        files = [f for f in os.listdir("reports") if f.endswith(".png")]
        if not files:
            self.graph_selector['values'] = ["Нет графиков. Подождите, идет расчет..."]
        else:
            self.graph_selector['values'] = files
            self.graph_selector.current(0)
            self._on_graph_select()

    def _on_graph_select(self, event=None):
        filename = self.graph_selector.get()
        path = os.path.join("reports", filename)
        if not os.path.exists(path):
            return

        img = Image.open(path)
        img.thumbnail((900, 500))
        self.photo = ImageTk.PhotoImage(img)
        self.img_label.config(image=self.photo)

    def _open_reports_folder(self):
        folder_path = os.path.abspath("reports")
        if not os.path.exists(folder_path):
            messagebox.showinfo("Информация", "Папка reports еще не создана. Подождите завершения расчетов.")
            return

        try:
            if sys.platform == "win32":
                os.startfile(folder_path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder_path])
            else:
                subprocess.Popen(["xdg-open", folder_path])
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть папку: {e}")

    def _build_info_tab(self):
        frame = ttk.LabelFrame(self.tab_info, text="Запуск тестов и проверка проекта")
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ttk.Label(frame, text="Здесь вы можете запустить pytest прямо из приложения.", font=("", 11)).pack(pady=10)

        self.test_btn = ttk.Button(frame, text="Запустить тесты (pytest)", command=self._run_tests)
        self.test_btn.pack(pady=10)

        self.test_output = tk.Text(frame, wrap="word", height=20, font=("Consolas", 10), bg="#f0f0f0")
        self.test_output.pack(fill="both", expand=True, padx=5, pady=5)

    def _run_tests(self):
        self.test_output.delete("1.0", tk.END)
        self.test_output.insert("1.0", "Запуск тестов, пожалуйста подождите...\n")
        self.update()

        try:
            result = subprocess.run(
                ["pytest", "-q", "tests/"],
                capture_output=True,
                text=True,
                encoding="utf-8"
            )
            output = result.stdout + "\n" + result.stderr
            self.test_output.delete("1.0", tk.END)
            self.test_output.insert("1.0", output)
        except Exception as e:
            self.test_output.delete("1.0", tk.END)
            self.test_output.insert("1.0", f"Ошибка при запуске тестов:\n{str(e)}")