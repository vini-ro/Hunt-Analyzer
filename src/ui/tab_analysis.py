import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime, timedelta
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
import pandas as pd
import mplcursors

from src.application.interfaces.repository import HuntRepository

class AnalysisTab(ctk.CTkFrame):
    def __init__(self, parent, repo: HuntRepository, main_app):
        super().__init__(parent)
        self.repo = repo
        self.main_app = main_app
        self.period_mode = "mes"
        self._build()

    def _build(self):
        frm = self
        
        # Top Controls
        top = ctk.CTkFrame(frm)
        top.pack(fill="x", padx=8, pady=8)

        ctk.CTkLabel(top, text="Personagem").pack(side="left", padx=5)
        self.combo_personagem = ctk.CTkComboBox(top, width=200, state="readonly", command=lambda e: self.update_analysis())
        self.combo_personagem.pack(side="left", padx=6)

        # Period Buttons
        btns = ctk.CTkFrame(top, fg_color="transparent")
        btns.pack(side="left", padx=12)
        ctk.CTkButton(btns, text="Hoje", width=60, command=lambda: self.set_period("hoje")).pack(side="left", padx=3)
        ctk.CTkButton(btns, text="Esta semana", width=80, command=lambda: self.set_period("semana")).pack(side="left", padx=3)
        ctk.CTkButton(btns, text="Este mês", width=80, command=lambda: self.set_period("mes")).pack(side="left", padx=3)
        ctk.CTkButton(btns, text="Este ano", width=80, command=lambda: self.set_period("ano")).pack(side="left", padx=3)

        # Date Range
        dates_frm = ctk.CTkFrame(top, fg_color="transparent")
        dates_frm.pack(side="left", padx=12)
        ctk.CTkLabel(dates_frm, text="De:").pack(side="left")
        self.entry_dt_ini = ctk.CTkEntry(dates_frm, width=100)
        self.entry_dt_ini.pack(side="left", padx=2)
        ctk.CTkLabel(dates_frm, text="Até:").pack(side="left")
        self.entry_dt_fim = ctk.CTkEntry(dates_frm, width=100)
        self.entry_dt_fim.pack(side="left", padx=2)
        ctk.CTkButton(dates_frm, text="Filtrar", width=80, command=self.update_analysis).pack(side="left", padx=4)

        ctk.CTkButton(top, text="Gráfico XP/Balance", command=self.show_chart).pack(side="left", padx=10)

        self.lbl_periodo = ctk.CTkLabel(frm, text="Período: (não definido)")
        self.lbl_periodo.pack(anchor="w", padx=12)

        # Metrics Grid
        grid = ctk.CTkFrame(frm)
        grid.pack(fill="x", padx=8, pady=6)

        labels = [
            "Hunts", "Horas", "XP total", "XP/h", "Raw XP", "Raw XP/h",
            "Balance", "Balance/h", "Monstros"
        ]
        self.metric_vars = {}
        for i, title in enumerate(labels):
            row, col = divmod(i, 6)
            box = ctk.CTkFrame(grid, border_width=1)
            box.grid(row=row, column=col, sticky="nsew", padx=3, pady=3)
            ctk.CTkLabel(box, text=title, font=("Arial", 12)).pack(pady=(4,0))
            var = tk.StringVar(value="-")
            ctk.CTkLabel(box, textvariable=var, font=("Arial", 14, "bold"), text_color="white").pack(pady=(0,4))
            self.metric_vars[title] = var
        
        for i in range(6): grid.grid_columnconfigure(i, weight=1)

        # Text Area
        self.txt_analises = ctk.CTkTextbox(frm, width=800, height=200)
        self.txt_analises.pack(fill="both", expand=True, padx=8, pady=8)
        
        # Init
        self.refresh_options()
        self.set_period("mes")

    def refresh_options(self):
        chars = self.repo.list_characters()
        default = self.repo.get_default_character()
        
        vals = [default] + [c for c in chars if c != default] if default in chars else chars
        vals += ["Todos"]
        
        # Preserve selection if possible
        curr = self.combo_personagem.get()
        self.combo_personagem.configure(values=vals)
        if curr in vals:
            self.combo_personagem.set(curr)
        else:
            self.combo_personagem.set(default if default else (vals[0] if vals else ""))
            
        self.update_analysis()

    def set_period(self, mode):
        # ... logic to fill date entries ...
        hoje = date.today()
        ini, fim, label = None, None, ""
        
        if mode == "hoje":
            ini, fim = hoje, hoje
            label = "(Hoje)"
        elif mode == "semana":
            ini = hoje - timedelta(days=hoje.weekday())
            fim = hoje
            label = "(Esta semana)"
        elif mode == "mes":
            ini = hoje.replace(day=1)
            fim = hoje
            label = "(Este mês)"
        elif mode == "ano":
            ini = date(hoje.year, 1, 1)
            fim = hoje
            label = "(Este ano)"
            
        if ini and fim:
            # CTkEntry deletion requires 0, "end" logic similar to tk but safest to explicitly call delete
            self.entry_dt_ini.delete(0, "end")
            self.entry_dt_ini.insert(0, ini.strftime("%d-%m-%Y"))
            self.entry_dt_fim.delete(0, "end")
            self.entry_dt_fim.insert(0, fim.strftime("%d-%m-%Y"))
            self.lbl_periodo.configure(text=f"Período: {ini.strftime('%d-%m-%Y')} a {fim.strftime('%d-%m-%Y')} {label}")
        
        self.update_analysis()

    def _get_dates(self):
        # On some systems, CTkEntry.get() might return None if empty? No, usually ""
        s_ini = self.entry_dt_ini.get()
        s_fim = self.entry_dt_fim.get()
        if s_ini: s_ini = s_ini.strip()
        if s_fim: s_fim = s_fim.strip()
        d_ini, d_fim = None, None
        try:
            if s_ini: d_ini = datetime.strptime(s_ini, "%d-%m-%Y").strftime("%Y-%m-%d")
            if s_fim: d_fim = datetime.strptime(s_fim, "%d-%m-%Y").strftime("%Y-%m-%d")
        except: pass
        return d_ini, d_fim

    def _fmt(self, n):
        try: return f"{int(n):,}".replace(",", ".")
        except: return str(n)

    def update_analysis(self, e=None):
        d_ini, d_fim = self._get_dates()
        char = self.combo_personagem.get()
        
        # Use simple filter to get Raw Data
        filters = {}
        if char and char != "Todos": filters["character"] = char
        if d_ini: filters["date_start"] = d_ini
        if d_fim: filters["date_end"] = d_fim

        raw_hunts = self.repo.get_all(filters)
        
        if not raw_hunts:
            # Clear everything
            for v in self.metric_vars.values(): v.set("-")
            self.txt_analises.delete("1.0", tk.END)
            return

        # DATA HANDLING WITH PANDAS (Enhancement)
        df = pd.DataFrame([h.__dict__ for h in raw_hunts])
        
        # Ensure numerics
        numeric_cols = ["duration_min", "xp_gain", "raw_xp_gain", "loot", "supplies", "balance", "damage", "healing"]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
        total_min = df["duration_min"].sum()
        horas = total_min / 60.0
        
        total_xp = df["xp_gain"].sum()
        total_raw = df["raw_xp_gain"].sum()
        total_balance = df["balance"].sum()
        total_kills = 0 # No monster detail in main dict usually, but check if we need complex aggreg
        
        # Metrics
        self.metric_vars["Hunts"].set(self._fmt(len(df)))
        self.metric_vars["Horas"].set(f"{int(total_min//60):02d}h{int(total_min%60):02d}m")
        self.metric_vars["XP total"].set(self._fmt(total_xp))
        self.metric_vars["XP/h"].set(self._fmt(total_xp/horas if horas>0 else 0))
        self.metric_vars["Raw XP"].set(self._fmt(total_raw))
        self.metric_vars["Raw XP/h"].set(self._fmt(total_raw/horas if horas>0 else 0))
        self.metric_vars["Balance"].set(self._fmt(total_balance))
        self.metric_vars["Balance/h"].set(self._fmt(total_balance/horas if horas>0 else 0))
        
        # Determine top creature if possible (need monster logic) 
        # For now, skip monster detail or iterate if needed
        
        # Text summary
        self.txt_analises.delete("1.0", tk.END)
        self.txt_analises.insert(tk.END, "===== RESUMO GERAL =====\n")
        self.txt_analises.insert(tk.END, f"Personagem: {char}\n")
        self.txt_analises.insert(tk.END, f"Período: {d_ini} a {d_fim}\n")
        self.txt_analises.insert(tk.END, f"Total de Hunts: {len(df)}\n\n")

        # --- RAW XP ANALYSIS ---
        self.txt_analises.insert(tk.END, "===== ANÁLISE DE RAW XP =====\n")
        self.txt_analises.insert(tk.END, f"Total Raw XP:     {self._fmt(total_raw)}\n")
        
        avg_raw = df['raw_xp_gain'].mean()
        self.txt_analises.insert(tk.END, f"Média Raw XP/hunt: {self._fmt(avg_raw)}\n")
        
        # Avoid div zero for calculation of rates per hunt
        # Calculate 'raw_xph' column for stats
        df['hours'] = df['duration_min'] / 60.0
        df['raw_xph'] = df.apply(lambda x: x['raw_xp_gain'] / x['hours'] if x['hours'] > 0 else 0, axis=1)
        
        avg_raw_xph = df['raw_xph'].mean()
        self.txt_analises.insert(tk.END, f"Média Raw XP/h:    {self._fmt(avg_raw_xph)}\n")
        
        max_raw_xph_idx = df['raw_xph'].idxmax()
        max_raw_hunt = df.loc[max_raw_xph_idx]
        self.txt_analises.insert(tk.END, f"Melhor Raw XP/h:   {self._fmt(max_raw_hunt['raw_xph'])} ({max_raw_hunt['date']})\n\n")

        # --- BALANCE ANALYSIS ---
        self.txt_analises.insert(tk.END, "===== ANÁLISE DE BALANCE =====\n")
        self.txt_analises.insert(tk.END, f"Total Balance:    {self._fmt(total_balance)}\n")
        self.txt_analises.insert(tk.END, f"Total Loot:       {self._fmt(df['loot'].sum())}\n")
        self.txt_analises.insert(tk.END, f"Total Supplies:   {self._fmt(df['supplies'].sum())}\n")
        
        avg_bal = df['balance'].mean()
        self.txt_analises.insert(tk.END, f"Média Profit/hunt: {self._fmt(avg_bal)}\n")
        
        df['bal_h'] = df.apply(lambda x: x['balance'] / x['hours'] if x['hours'] > 0 else 0, axis=1)
        avg_bal_h = df['bal_h'].mean()
        self.txt_analises.insert(tk.END, f"Média Profit/h:    {self._fmt(avg_bal_h)}\n")

     

        max_profit_idx = df['balance'].idxmax()
        best_profit = df.loc[max_profit_idx]
        self.txt_analises.insert(tk.END, f"Melhor Profit (total): {self._fmt(best_profit['balance'])} ({best_profit['date']})\n")
        
        max_bal_h_idx = df['bal_h'].idxmax()
        best_bal_h = df.loc[max_bal_h_idx]
        self.txt_analises.insert(tk.END, f"Melhor Profit/h:       {self._fmt(best_bal_h['bal_h'])} ({best_bal_h['date']})\n\n")
        
        if "damage" in df.columns:
            self.txt_analises.insert(tk.END, f"Dano Total:     {self._fmt(df['damage'].sum())}\n")

        # --- MONSTER ANALYSIS ---
        self.txt_analises.insert(tk.END, "\n===== ANÁLISE DE MONSTROS (Top 4) =====\n")
        try:
            monster_stats = self.repo.get_monster_aggregates(filters)
            if monster_stats:
                # Show top 4
                for rank, (name, count) in enumerate(monster_stats[:4], 1):
                    self.txt_analises.insert(tk.END, f"{rank}. {name}: {self._fmt(count)}\n")
            else:
                self.txt_analises.insert(tk.END, "Nenhum monstro registrado no período.\n")
        except Exception as e:
            self.txt_analises.insert(tk.END, f"Erro ao carregar monstros: {e}\n")

        # --- PROGRESS ANALYSIS ---
        self.txt_analises.insert(tk.END, "\n===== PROGRESSO (Evolução) =====\n")
        if len(df) >= 4:
            # Sort by date just to be sure
            if 'date_obj' not in df.columns:
                df['date_obj'] = pd.to_datetime(df['date'])
            df_sorted = df.sort_values('date_obj')
            
            # Helper for growth
            def calc_growth(col_name):
                # Take simple avg of first 3 vs last 3
                first_n = df_sorted.head(3)[col_name].mean()
                last_n = df_sorted.tail(3)[col_name].mean()
                if first_n == 0: return 0.0
                return ((last_n - first_n) / first_n) * 100

            growth_raw = calc_growth('raw_xph')
            growth_bal = calc_growth('bal_h')
            
            self.txt_analises.insert(tk.END, f"Comparação (Primeiras 3 vs Últimas 3 hunts no período):\n")
            self.txt_analises.insert(tk.END, f"Crescimento Raw XP/h: {growth_raw:+.2f}%\n")
            self.txt_analises.insert(tk.END, f"Crescimento Profit/h: {growth_bal:+.2f}%\n")
        else:
            self.txt_analises.insert(tk.END, "Dados insuficientes para cálculo de progresso (mínimo 4 hunts).\n")

    def show_chart(self):
        d_ini, d_fim = self._get_dates()
        char = self.combo_personagem.get()
        filters = {}
        if char and char != "Todos": filters["character"] = char
        if d_ini: filters["date_start"] = d_ini
        if d_fim: filters["date_end"] = d_fim
        
        raw_hunts = self.repo.get_all(filters)
        if not raw_hunts:
             messagebox.showinfo("Sem dados", "Não há hunts no período.")
             return

        # PANDAS CHARTING
        df = pd.DataFrame([h.__dict__ for h in raw_hunts])
        
        # Ensure numerics
        numeric_cols = ["duration_min", "raw_xp_gain", "balance", "supplies"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        df['date_obj'] = pd.to_datetime(df['date'])
        df = df.sort_values('date_obj')
        
        dates = df['date_obj']
        hours = df['duration_min'] / 60.0
        # Avoid zero division
        hours = hours.replace(0, 1) # simple fallback
        
        raw_xph = df['raw_xp_gain'] / hours
        balanceh = df['balance'] / hours
        supplyh = df['supplies'] / hours

        win = ctk.CTkToplevel(self)
        win.title("Gráfico XP/Balance/Supply")
        win.geometry("900x500")
        
        fig = Figure(figsize=(9, 5), dpi=100)
        ax = fig.add_subplot(111)
        
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%m-%Y"))
        
        line1, = ax.plot(dates, raw_xph, marker="o", label="Raw XP/h", color="#1f77b4")
        line2, = ax.plot(dates, balanceh, marker="o", label="Balance/h", color="#2ca02c")
        line3, = ax.plot(dates, supplyh, marker="x", linestyle="--", label="Supply/h", color="#d62728")
        
        fig.autofmt_xdate()
        ax.set_ylabel("Valor")
        ax.grid(True, linestyle=':', alpha=0.6)
            
        ax.legend()

        # Interactivity
        cursor = mplcursors.cursor([line1, line2, line3], hover=True)
        @cursor.connect("add")
        def on_add(sel):
            # Format value
            val = sel.target[1]
            try:
                # Get the date from x data of the artist corresponding to the index
                x_val = sel.target[0]
                date_txt = mdates.num2date(x_val).strftime("%d-%m-%Y")
                sel.annotation.set_text(f"{date_txt}\n{sel.artist.get_label()}: {val:,.0f}")
            except:
                sel.annotation.set_text(f"{val:.0f}")
        
        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
