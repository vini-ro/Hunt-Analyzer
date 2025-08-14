#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hunt-Analizer (macOS) - v5
- SQLite local database
- Import .txt/.log from Tibia session window
- Extract and persist Hunts + Monsters
- Tabs: Inserir | Análises | Hunts
- Analyses: quick period buttons (Hoje, Esta semana, Este mês, Este ano)
- Default character preselected; "Todos" is last option
- Hunts tab: multiselect delete; double-click to edit; batch edit (personagem/local)
"""

import sqlite3
import tkinter as tk
from tkinter import messagebox, filedialog, ttk, simpledialog
import re
from datetime import datetime, timedelta, date
from contextlib import closing

DB_PATH = "tibia_hunts.db"


# -------------------------
# Database
# -------------------------
def conectar_sqlite():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS Characters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT UNIQUE NOT NULL,
        is_default INTEGER NOT NULL DEFAULT 0
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS Locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT UNIQUE NOT NULL
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS Hunts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        personagem TEXT NOT NULL,
        local TEXT NOT NULL,
        data TEXT,
        hora_inicio TEXT,
        hora_fim TEXT,
        duracao_min INTEGER,
        raw_xp_gain INTEGER,
        xp_gain INTEGER,
        loot INTEGER,
        supplies INTEGER,
        pagamento INTEGER,
        balance INTEGER,
        damage INTEGER,
        healing INTEGER
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS Hunts_Monstros (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hunt_id INTEGER NOT NULL,
        personagem TEXT NOT NULL,
        criatura TEXT NOT NULL,
        quantidade INTEGER NOT NULL,
        FOREIGN KEY(hunt_id) REFERENCES Hunts(id) ON DELETE CASCADE
    )
    """)

    # ensure default "Elite Vini"
    with closing(conn.cursor()) as cur:
        cur.execute("SELECT COUNT(*) FROM Characters WHERE nome = ?", ("Elite Vini",))
        if cur.fetchone()[0] == 0:
            cur.execute("INSERT INTO Characters (nome, is_default) VALUES (?, 1)", ("Elite Vini",))
        else:
            cur.execute("SELECT COUNT(*) FROM Characters WHERE is_default = 1")
            if cur.fetchone()[0] == 0:
                cur.execute("UPDATE Characters SET is_default = 1 WHERE nome = ?", ("Elite Vini",))
    conn.commit()
    return conn


def get_default_character(conn):
    with closing(conn.cursor()) as cur:
        cur.execute("SELECT nome FROM Characters WHERE is_default = 1 LIMIT 1")
        r = cur.fetchone()
        return r[0] if r else ""


def list_characters(conn):
    with closing(conn.cursor()) as cur:
        cur.execute("SELECT nome, is_default FROM Characters ORDER BY nome")
        rows = cur.fetchall()
    default = [n for (n, d) in rows if d]
    others = [n for (n, d) in rows if not d]
    return (default + others)


def set_default_character(conn, nome):
    with closing(conn.cursor()) as cur:
        cur.execute("UPDATE Characters SET is_default = 0")
        cur.execute("UPDATE Characters SET is_default = 1 WHERE nome = ?", (nome,))
    conn.commit()


def add_character(conn, nome):
    if not nome.strip():
        return
    with closing(conn.cursor()) as cur:
        cur.execute("INSERT OR IGNORE INTO Characters (nome) VALUES (?)", (nome.strip(),))
    conn.commit()


def delete_character(conn, nome):
    with closing(conn.cursor()) as cur:
        cur.execute("DELETE FROM Characters WHERE nome = ?", (nome,))
    conn.commit()


def list_locations(conn):
    with closing(conn.cursor()) as cur:
        cur.execute("SELECT nome FROM Locations ORDER BY nome")
        return [r[0] for r in cur.fetchall()]


def add_location(conn, nome):
    if not nome.strip():
        return
    with closing(conn.cursor()) as cur:
        cur.execute("INSERT OR IGNORE INTO Locations (nome) VALUES (?)", (nome.strip(),))
    conn.commit()


def delete_location(conn, nome):
    with closing(conn.cursor()) as cur:
        cur.execute("DELETE FROM Locations WHERE nome = ?", (nome,))
    conn.commit()


# -------------------------
# Parsing helpers
# -------------------------
def seguro_int(valor):
    try:
        return int(valor)
    except Exception:
        try:
            return int(float(valor))
        except Exception:
            return 0


def extrair_monstros(texto):
    m = re.search(r"Killed Monsters:\s*(.*?)(?:Looted Items:|$)", texto, re.DOTALL | re.IGNORECASE)
    trecho = m.group(1) if m else ""
    padrao = re.compile(r'^\s*(\d+)\s*x\s+(.+?)\s*$', re.MULTILINE | re.IGNORECASE)
    monstros = padrao.findall(trecho)
    return [(nome.strip(), seguro_int(qtd)) for qtd, nome in monstros]


def _buscar(texto, padrao, flags=0, default="0"):
    m = re.search(padrao, texto, flags)
    if not m:
        return default
    val = m.group(1)
    val = val.replace(",", "").replace("−", "-").replace("–", "-").strip()
    return val


def extrair_dados_hunt(texto):
    duracao_min = 0
    m = re.search(r"Session:\s+(\d{2}):(\d{2})h", texto)
    if m:
        try:
            h, mm = int(m.group(1)), int(m.group(2))
            duracao_min = h * 60 + mm
        except Exception:
            duracao_min = 0

    raw_xp = seguro_int(_buscar(texto, r"Raw XP Gain:\s*([\d,.]+)"))
    xp = seguro_int(_buscar(texto, r"^XP Gain:\s*([\d,.]+)", flags=re.MULTILINE))
    loot = seguro_int(_buscar(texto, r"Loot:\s*([-\d,−–]+)"))
    supplies = seguro_int(_buscar(texto, r"Supplies:\s*([-\d,−–]+)"))
    balance = seguro_int(_buscar(texto, r"Balance:\s*([-\d,−–]+)"))
    damage = seguro_int(_buscar(texto, r"Damage:\s*([-\d,−–]+)"))
    healing = seguro_int(_buscar(texto, r"Healing:\s*([-\d,−–]+)"))

    data_inicio = _buscar(texto, r"From\s+(\d{4}-\d{2}-\d{2}),", default="")
    hora_inicio = _buscar(texto, r"From\s+\d{4}-\d{2}-\d{2},\s+(\d{2}:\d{2}:\d{2})", default="")
    hora_fim = _buscar(texto, r"to\s+\d{4}-\d{2}-\d{2},\s+(\d{2}:\d{2}:\d{2})", default="")

    return {
        "duracao_min": duracao_min,
        "raw_xp_gain": raw_xp,
        "xp_gain": xp,
        "loot": loot,
        "supplies": supplies,
        "balance": balance,
        "damage": damage,
        "healing": healing,
        "data_inicio": data_inicio,
        "hora_inicio": hora_inicio,
        "hora_fim": hora_fim,
    }


# -------------------------
# App
# -------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Hunt-Analizer")
        self.geometry("1180x720")

        # style padding for tabs (fix clipping)
        style = ttk.Style()
        try:
            style.configure("TNotebook.Tab", padding=[12, 6])
        except Exception:
            pass

        self.conn = conectar_sqlite()
        self.period_mode = "mes"  # default button
        self.custom_start = None
        self.custom_end = None

        self._build_ui()

    # ---------- UI ----------
    def _build_ui(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)

        self.tab_inserir = ttk.Frame(notebook)
        notebook.add(self.tab_inserir, text="Inserir")

        self.tab_analises = ttk.Frame(notebook)
        notebook.add(self.tab_analises, text="Análises")

        self.tab_hunts = ttk.Frame(notebook)
        notebook.add(self.tab_hunts, text="Hunts")

        self._build_tab_inserir()
        self._build_tab_analises()
        self._build_tab_hunts()

    # ---------- Inserir ----------
    def _build_tab_inserir(self):
        frm = self.tab_inserir

        ttk.Label(frm, text="Personagem").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.combo_personagem_insert = ttk.Combobox(frm, width=30, state="readonly")
        self.combo_personagem_insert.grid(row=0, column=1, sticky="w", padx=5, pady=5)

        ttk.Button(frm, text="Gerenciar Personagens", command=self.gerenciar_personagens).grid(row=0, column=2, padx=5)

        ttk.Label(frm, text="Local").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.combo_local_insert = ttk.Combobox(frm, width=30)
        self.combo_local_insert.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        ttk.Button(frm, text="Gerenciar Locais", command=self.gerenciar_locais).grid(row=1, column=2, padx=5)

        btns = ttk.Frame(frm)
        btns.grid(row=0, column=3, rowspan=2, padx=5, pady=5, sticky="w")
        ttk.Button(btns, text="Abrir Arquivo Hunt", command=self.abrir_arquivo).pack(fill="x", pady=2)
        ttk.Button(btns, text="Importar Arquivo(s) …", command=self.importar_arquivos).pack(fill="x", pady=2)

        ttk.Label(frm, text="Conteúdo da Hunt").grid(row=2, column=0, sticky="nw", padx=5, pady=(10, 0))
        self.text_dados = tk.Text(frm, width=110, height=25)
        self.text_dados.grid(row=2, column=1, columnspan=3, padx=5, pady=(10, 0), sticky="nsew")

        ttk.Button(frm, text="Salvar Hunt Atual", command=self.salvar_hunt_atual).grid(row=3, column=1, pady=10, sticky="w")

        frm.grid_rowconfigure(2, weight=1)
        frm.grid_columnconfigure(1, weight=1)

        self.refresh_insert_combos()

    # ---------- Análises ----------
    def _build_tab_analises(self):
        frm = self.tab_analises

        top = ttk.Frame(frm)
        top.pack(fill="x", padx=8, pady=8)

        ttk.Label(top, text="Personagem").pack(side="left")
        self.combo_personagem = ttk.Combobox(top, width=28, state="readonly")
        self.combo_personagem.pack(side="left", padx=6)

        # period buttons
        btns = ttk.Frame(top)
        btns.pack(side="left", padx=12)
        self.btn_hoje = ttk.Button(btns, text="Hoje", command=lambda: self.set_period("hoje"))
        self.btn_semana = ttk.Button(btns, text="Esta semana", command=lambda: self.set_period("semana"))
        self.btn_mes = ttk.Button(btns, text="Este mês", command=lambda: self.set_period("mes"))
        self.btn_ano = ttk.Button(btns, text="Este ano", command=lambda: self.set_period("ano"))
        for b in (self.btn_hoje, self.btn_semana, self.btn_mes, self.btn_ano):
            b.pack(side="left", padx=3)

        ttk.Button(top, text="Atualizar", command=self.atualizar_analises).pack(side="left", padx=10)

        self.lbl_periodo = ttk.Label(frm, text="Período: (não definido)")
        self.lbl_periodo.pack(anchor="w", padx=12)

        # metrics panel (grid of labels)
        grid = ttk.Frame(frm)
        grid.pack(fill="x", padx=8, pady=6)

        labels = [
            "Hunts", "Horas", "XP total", "XP/h", "Raw XP", "Raw XP/h",
            "Lucro (Loot - Supplies - Pagto)", "Lucro/h",
            "Balance bruto", "Monstros", "Monstros/h"
        ]
        self.metric_vars = {}
        for i, title in enumerate(labels):
            box = ttk.Frame(grid, borderwidth=1, relief="groove", padding=6)
            box.grid(row=0, column=i, sticky="nsew", padx=3, pady=3)
            ttk.Label(box, text=title).pack()
            var = tk.StringVar(value="-")
            ttk.Label(box, textvariable=var, font=("TkDefaultFont", 11, "bold")).pack()
            self.metric_vars[title] = var

        for i in range(len(labels)):
            grid.grid_columnconfigure(i, weight=1)

        # detailed text area below
        self.txt_analises = tk.Text(frm, width=120, height=20)
        self.txt_analises.pack(fill="both", expand=True, padx=8, pady=8)

        self.recarregar_filtros_analises()
        # default period
        self.set_period("mes")
        self.atualizar_analises()

    def set_period(self, mode):
        self.period_mode = mode
        hoje = date.today()
        if mode == "hoje":
            ini = hoje
            fim = hoje
            label = f"{ini.isoformat()} a {fim.isoformat()} (Hoje)"
        elif mode == "semana":
            ini = hoje - timedelta(days=(hoje.weekday()))  # Monday
            fim = hoje
            label = f"{ini.isoformat()} a {fim.isoformat()} (Esta semana)"
        elif mode == "mes":
            ini = hoje.replace(day=1)
            fim = hoje
            label = f"{ini.isoformat()} a {fim.isoformat()} (Este mês)"
        elif mode == "ano":
            ini = date(hoje.year, 1, 1)
            fim = hoje
            label = f"{ini.isoformat()} a {fim.isoformat()} (Este ano)"
        else:
            ini, fim, label = None, None, "Período: (não definido)"
        self.custom_start, self.custom_end = ini, fim
        self.lbl_periodo.config(text=f"Período: {label}")

    def _period_limits(self):
        if self.period_mode in ("hoje", "semana", "mes", "ano"):
            return self.custom_start, self.custom_end
        return None, None

    def _fmt(self, n):
        try:
            return f"{int(n):,}".replace(",", ".")
        except Exception:
            try:
                return f"{float(n):,.0f}".replace(",", ".")
            except Exception:
                return str(n)

    def atualizar_analises(self):
        # ensure start/end per current mode
        self.set_period(self.period_mode)

        pers = self.combo_personagem.get().strip()
        dt_ini, dt_fim = self._period_limits()

        cur = self.conn.cursor()
        where = []
        params = []
        if pers and pers != "Todos":
            where.append("h.personagem = ?")
            params.append(pers)
        if dt_ini and dt_fim:
            where.append("h.data >= ? AND h.data <= ?")
            params.extend([dt_ini.isoformat(), dt_fim.isoformat()])
        where_sql = ("WHERE " + " AND ".join(where)) if where else ""

        cur.execute(f"""
            SELECT 
                COUNT(*),
                COALESCE(SUM(h.duracao_min),0),
                COALESCE(SUM(h.xp_gain),0),
                COALESCE(SUM(h.raw_xp_gain),0),
                COALESCE(SUM(h.loot),0),
                COALESCE(SUM(h.supplies),0),
                COALESCE(SUM(h.pagamento),0),
                COALESCE(SUM(h.balance),0)
            FROM Hunts h
            {where_sql}
        """, params)
        row = cur.fetchone()
        qtd, total_min, total_xp, total_raw_xp, total_loot, total_supplies, total_pagto, total_balance = row

        # kills
        cur.execute(f"""
            SELECT COALESCE(SUM(hm.quantidade),0) as total_kills
            FROM Hunts h LEFT JOIN Hunts_Monstros hm ON hm.hunt_id = h.id
            {where_sql}
        """, params)
        total_kills = int(cur.fetchone()[0] or 0)

        horas = total_min / 60.0 if total_min > 0 else 0.0
        xp_h = (total_xp / horas) if horas > 0 else 0.0
        raw_xp_h = (total_raw_xp / horas) if horas > 0 else 0.0
        lucro_total = (total_loot - total_supplies - total_pagto)
        lucro_h = (lucro_total / horas) if horas > 0 else 0.0
        kills_h = (total_kills / horas) if horas > 0 else 0.0

        # metrics panel
        data_map = {
            "Hunts": self._fmt(qtd),
            "Horas": f"{int(total_min//60):02d}h{int(total_min%60):02d}m",
            "XP total": self._fmt(total_xp),
            "XP/h": self._fmt(xp_h),
            "Raw XP": self._fmt(total_raw_xp),
            "Raw XP/h": self._fmt(raw_xp_h),
            "Lucro (Loot - Supplies - Pagto)": self._fmt(lucro_total),
            "Lucro/h": self._fmt(lucro_h),
            "Balance bruto": self._fmt(total_balance),
            "Monstros": self._fmt(total_kills),
            "Monstros/h": self._fmt(kills_h),
        }
        for k, v in data_map.items():
            if k in self.metric_vars:
                self.metric_vars[k].set(v)

        # detailed text (legacy breakdown)
        self.txt_analises.delete("1.0", tk.END)
        def w(line=""):
            self.txt_analises.insert(tk.END, line + "\n")

        w("===== Detalhes =====")
        w(f"Personagem: {pers if pers else '(não definido)'}")
        if dt_ini and dt_fim:
            w(f"Período: {dt_ini.isoformat()} a {dt_fim.isoformat()}")
        else:
            w("Período: Tudo")
        w()
        w(f"Hunts: {qtd}")
        w(f"Duração total: {int(total_min//60):02d}h{int(total_min%60):02d}m")
        w(f"XP total: {self._fmt(total_xp)} | XP/h: {self._fmt(xp_h)}")
        w(f"Raw XP: {self._fmt(total_raw_xp)} | Raw XP/h: {self._fmt(raw_xp_h)}")
        w(f"Lucro total: {self._fmt(lucro_total)} | Lucro/h: {self._fmt(lucro_h)}")
        w(f"Supplies: {self._fmt(total_supplies)} | Pagamento: {self._fmt(total_pagto)} | Balance bruto: {self._fmt(total_balance)}")
        w(f"Monstros: {self._fmt(total_kills)} | Monstros/h: {self._fmt(kills_h)}")

    def recarregar_filtros_analises(self):
        chars = list_characters(self.conn)
        default_char = get_default_character(self.conn)
        ordered = ([default_char] + [c for c in chars if c != default_char]) if default_char in chars else chars[:]
        ordered = ordered + ["Todos"]
        self.combo_personagem["values"] = ordered
        self.combo_personagem.set(default_char if default_char else (ordered[0] if ordered else ""))

    # ---------- Hunts ----------
    def _build_tab_hunts(self):
        frm = self.tab_hunts

        filt = ttk.Frame(frm)
        filt.pack(fill="x", padx=8, pady=6)
        ttk.Label(filt, text="Personagem").pack(side="left")
        self.combo_personagem_list = ttk.Combobox(filt, width=20, state="readonly")
        self.combo_personagem_list.pack(side="left", padx=6)
        ttk.Label(filt, text="Local contém").pack(side="left", padx=(10,2))
        self.entry_local_filter = ttk.Entry(filt, width=22)
        self.entry_local_filter.pack(side="left", padx=6)
        ttk.Button(filt, text="Atualizar", command=self.refresh_hunts_list).pack(side="left", padx=6)

        cols = ("id","data","inicio","fim","duracao","personagem","local","xp","loot","supplies","pagamento","balance")
        self.tree = ttk.Treeview(frm, columns=cols, show="headings", height=18, selectmode="extended")
        for c, w in zip(cols, (60,90,80,80,80,130,180,90,90,90,90,90)):
            self.tree.heading(c, text=c.upper())
            self.tree.column(c, width=w, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=8, pady=6)

        # double-click to edit
        self.tree.bind("<Double-1>", lambda e: self.edit_selected_hunt())

        actions = ttk.Frame(frm)
        actions.pack(fill="x", padx=8, pady=6)
        ttk.Button(actions, text="Editar selecionadas…", command=self.batch_edit_selected).pack(side="left", padx=4)
        ttk.Button(actions, text="Apagar selecionadas", command=self.delete_selected_hunts).pack(side="left", padx=4)

        self.refresh_list_filters()
        self.refresh_hunts_list()

    def refresh_insert_combos(self):
        chars = list_characters(self.conn)
        default_char = get_default_character(self.conn)
        ordered = ([default_char] + [c for c in chars if c != default_char]) if default_char in chars else chars[:]
        self.combo_personagem_insert["values"] = ordered
        self.combo_personagem_insert.set(default_char if default_char else (ordered[0] if ordered else ""))

        locs = list_locations(self.conn)
        self.combo_local_insert["values"] = locs

    def refresh_list_filters(self):
        chars = list_characters(self.conn)
        default_char = get_default_character(self.conn)
        ordered = ([default_char] + [c for c in chars if c != default_char]) if default_char in chars else chars[:]
        ordered = ordered + ["Todos"]
        self.combo_personagem_list["values"] = ordered
        self.combo_personagem_list.set(default_char if default_char else (ordered[0] if ordered else ""))

    def refresh_hunts_list(self):
        pers = self.combo_personagem_list.get()
        loc_like = self.entry_local_filter.get().strip()

        where = []
        params = []
        if pers and pers != "Todos":
            where.append("personagem = ?")
            params.append(pers)
        if loc_like:
            where.append("local LIKE ?")
            params.append(f"%{loc_like}%")

        where_sql = ("WHERE " + " AND ".join(where)) if where else ""
        with closing(self.conn.cursor()) as cur:
            cur.execute(f"""
                SELECT id, data, hora_inicio, hora_fim, duracao_min, personagem, local,
                       xp_gain, loot, supplies, pagamento, balance
                FROM Hunts
                {where_sql}
                ORDER BY COALESCE(data,'9999-99-99') DESC, COALESCE(hora_inicio,'00:00:00') DESC, id DESC
            """, params)
            rows = cur.fetchall()

        self.tree.delete(*self.tree.get_children())
        for r in rows:
            mins = r[4] or 0
            hh = int(mins // 60); mm = int(mins % 60)
            dur = f"{hh:02d}:{mm:02d}h"
            self.tree.insert("", "end", values=(
                r[0], r[1], r[2], r[3], dur, r[5], r[6],
                r[7], r[8], r[9], r[10], r[11]
            ))

    def _get_selected_ids(self):
        sels = self.tree.selection()
        ids = []
        for s in sels:
            vals = self.tree.item(s, "values")
            if vals:
                ids.append(int(vals[0]))
        return ids

    def edit_selected_hunt(self):
        ids = self._get_selected_ids()
        if not ids:
            messagebox.showwarning("Aviso", "Selecione ao menos uma hunt.")
            return
        if len(ids) > 1:
            # fall to batch edit
            self.batch_edit_selected()
            return
        hid = ids[0]
        with closing(self.conn.cursor()) as cur:
            cur.execute("""
                SELECT id, personagem, local, data, hora_inicio, hora_fim, duracao_min,
                       raw_xp_gain, xp_gain, loot, supplies, pagamento, balance, damage, healing
                FROM Hunts WHERE id = ?
            """, (hid,))
            r = cur.fetchone()
        if not r:
            messagebox.showerror("Erro", "Hunt não encontrada.")
            return

        win = tk.Toplevel(self)
        win.title(f"Editar Hunt #{hid}")
        win.geometry("600x520")

        labels = [
            ("Personagem","personagem"), ("Local","local"), ("Data (YYYY-MM-DD)","data"),
            ("Hora início (HH:MM:SS)","hora_inicio"), ("Hora fim (HH:MM:SS)","hora_fim"),
            ("Duração (min)","duracao_min"), ("Raw XP","raw_xp_gain"), ("XP Gain","xp_gain"),
            ("Loot","loot"), ("Supplies","supplies"), ("Pagamento","pagamento"), ("Balance","balance"),
            ("Damage","damage"), ("Healing","healing")
        ]
        entries = {}
        for i,(lbl, key) in enumerate(labels):
            ttk.Label(win, text=lbl).grid(row=i, column=0, sticky="w", padx=6, pady=4)
            e = ttk.Entry(win, width=28)
            e.grid(row=i, column=1, sticky="w", padx=6, pady=4)
            entries[key] = e

        keys = ["id","personagem","local","data","hora_inicio","hora_fim","duracao_min","raw_xp_gain","xp_gain",
                "loot","supplies","pagamento","balance","damage","healing"]
        data_map = dict(zip(keys, r))
        for k in entries:
            val = data_map.get(k, "")
            entries[k].insert(0, "" if val is None else str(val))

        def save_changes():
            try:
                vals = {k: entries[k].get().strip() for k in entries}
                add_character(self.conn, vals["personagem"])
                add_location(self.conn, vals["local"])
                with closing(self.conn.cursor()) as cur2:
                    cur2.execute("""
                        UPDATE Hunts
                        SET personagem=?, local=?, data=?, hora_inicio=?, hora_fim=?, duracao_min=?,
                            raw_xp_gain=?, xp_gain=?, loot=?, supplies=?, pagamento=?, balance=?, damage=?, healing=?
                        WHERE id = ?
                    """, (
                        vals["personagem"], vals["local"], vals["data"], vals["hora_inicio"], vals["hora_fim"],
                        int(vals["duracao_min"] or 0), int(vals["raw_xp_gain"] or 0), int(vals["xp_gain"] or 0),
                        int(vals["loot"] or 0), int(vals["supplies"] or 0), int(vals["pagamento"] or 0),
                        int(vals["balance"] or 0), int(vals["damage"] or 0), int(vals["healing"] or 0), hid
                    ))
                    self.conn.commit()
                self.refresh_insert_combos()
                self.recarregar_filtros_analises()
                self.refresh_hunts_list()
                win.destroy()
                messagebox.showinfo("Sucesso", "Hunt atualizada!")
            except Exception as e:
                messagebox.showerror("Erro", str(e))

        ttk.Button(win, text="Salvar alterações", command=save_changes).grid(row=len(labels), column=0, columnspan=2, pady=10)

    def batch_edit_selected(self):
        ids = self._get_selected_ids()
        if not ids:
            messagebox.showwarning("Aviso", "Selecione ao menos uma hunt.")
            return

        win = tk.Toplevel(self)
        win.title(f"Editar {len(ids)} hunts")
        win.geometry("420x180")

        ttk.Label(win, text="Personagem (deixe vazio para não alterar)").grid(row=0, column=0, padx=6, pady=6, sticky="w")
        entry_char = ttk.Entry(win, width=30)
        entry_char.grid(row=0, column=1, padx=6, pady=6, sticky="w")

        ttk.Label(win, text="Local (deixe vazio para não alterar)").grid(row=1, column=0, padx=6, pady=6, sticky="w")
        entry_loc = ttk.Entry(win, width=30)
        entry_loc.grid(row=1, column=1, padx=6, pady=6, sticky="w")

        def apply_changes():
            new_char = entry_char.get().strip()
            new_loc = entry_loc.get().strip()
            if not new_char and not new_loc:
                win.destroy()
                return
            with closing(self.conn.cursor()) as cur:
                if new_char:
                    add_character(self.conn, new_char)
                    qmarks = ",".join("?" for _ in ids)
                    cur.execute(f"UPDATE Hunts SET personagem=? WHERE id IN ({qmarks})", tuple([new_char] + ids))
                if new_loc:
                    add_location(self.conn, new_loc)
                    qmarks = ",".join("?" for _ in ids)
                    cur.execute(f"UPDATE Hunts SET local=? WHERE id IN ({qmarks})", tuple([new_loc] + ids))
                self.conn.commit()
            self.refresh_insert_combos()
            self.recarregar_filtros_analises()
            self.refresh_hunts_list()
            win.destroy()
            messagebox.showinfo("Sucesso", "Hunts atualizadas.")

        ttk.Button(win, text="Aplicar", command=apply_changes).grid(row=2, column=0, columnspan=2, pady=10)

    def delete_selected_hunts(self):
        ids = self._get_selected_ids()
        if not ids:
            messagebox.showwarning("Aviso", "Selecione ao menos uma hunt.")
            return
        if not messagebox.askyesno("Confirmar", f"Apagar {len(ids)} hunts selecionadas?"):
            return
        with closing(self.conn.cursor()) as cur:
            qmarks = ",".join("?" for _ in ids)
            cur.execute(f"DELETE FROM Hunts WHERE id IN ({qmarks})", tuple(ids))
            self.conn.commit()
        self.refresh_hunts_list()
        messagebox.showinfo("Pronto", "Hunts apagadas.")

    # ---------- File Ops ----------
    def abrir_arquivo(self):
        caminho = filedialog.askopenfilename(
            filetypes=[("Text/Log", "*.txt *.log"), ("Todos", "*.*")]
        )
        if not caminho:
            return
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                conteudo = f.read()
        except UnicodeDecodeError:
            with open(caminho, "r", encoding="latin-1") as f:
                conteudo = f.read()
        self.text_dados.delete("1.0", tk.END)
        self.text_dados.insert(tk.END, conteudo)

    def importar_arquivos(self):
        caminhos = filedialog.askopenfilenames(
            title="Selecione 1 ou mais arquivos de Hunt",
            filetypes=[("Text/Log", "*.txt *.log"), ("Todos", "*.*")]
        )
        if not caminhos:
            return
        ok, falhas = 0, 0
        for c in caminhos:
            try:
                with open(c, "r", encoding="utf-8") as f:
                    conteudo = f.read()
            except UnicodeDecodeError:
                with open(c, "r", encoding="latin-1") as f:
                    conteudo = f.read()
            if self._salvar_hunt(conteudo):
                ok += 1
            else:
                falhas += 1
        self.refresh_insert_combos()
        self.recarregar_filtros_analises()
        self.refresh_hunts_list()
        messagebox.showinfo("Importação concluída", f"Sucesso: {ok}\nFalhas: {falhas}")

    def salvar_hunt_atual(self):
        dados_hunt = self.text_dados.get("1.0", tk.END).strip()
        personagem = self.combo_personagem_insert.get().strip()
        local = self.combo_local_insert.get().strip()

        if not personagem or not local or not dados_hunt:
            messagebox.showwarning("Aviso", "Informe Personagem, Local e carregue/cole a Hunt.")
            return

        if self._salvar_hunt(dados_hunt, personagem, local):
            self.refresh_insert_combos()
            self.recarregar_filtros_analises()
            self.refresh_hunts_list()
            messagebox.showinfo("Sucesso", "Hunt salva com sucesso!")

    def _salvar_hunt(self, dados_hunt, personagem=None, local=None):
        try:
            info = extrair_dados_hunt(dados_hunt)
            if not personagem:
                personagem = get_default_character(self.conn) or "Desconhecido"
            if not local:
                local = "Desconhecido"

            add_character(self.conn, personagem)
            add_location(self.conn, local)

            pagamento = abs(info["balance"]) if info["balance"] < 0 else 0

            valores = (
                personagem, local, info["data_inicio"] or "", info["hora_inicio"] or "", info["hora_fim"] or "",
                info["duracao_min"], info["raw_xp_gain"], info["xp_gain"], info["loot"], info["supplies"],
                pagamento, info["balance"], info["damage"], info["healing"]
            )

            cur = self.conn.cursor()
            cur.execute("""
                INSERT INTO Hunts (
                    personagem, local, data, hora_inicio, hora_fim, duracao_min,
                    raw_xp_gain, xp_gain, loot, supplies, pagamento, balance, damage, healing
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, valores)
            hunt_id = cur.lastrowid

            # Monstros
            monstros = extrair_monstros(dados_hunt)
            for nome, qtd in monstros:
                cur.execute("""
                    INSERT INTO Hunts_Monstros (hunt_id, personagem, criatura, quantidade)
                    VALUES (?, ?, ?, ?)
                """, (hunt_id, personagem, nome, qtd))

            self.conn.commit()
            return True
        except Exception as e:
            messagebox.showerror("Erro ao salvar", str(e))
            return False

    # ---------- Manage registries ----------
    def gerenciar_personagens(self):
        win = tk.Toplevel(self)
        win.title("Gerenciar Personagens")
        win.geometry("420x280")
        tree = ttk.Treeview(win, columns=("nome","default"), show="headings")
        tree.heading("nome", text="Nome")
        tree.heading("default", text="Default")
        tree.column("nome", width=260); tree.column("default", width=80, anchor="center")
        tree.pack(fill="both", expand=True, padx=5, pady=5)

        def refresh():
            tree.delete(*tree.get_children())
            default = get_default_character(self.conn)
            for nome in list_characters(self.conn):
                tree.insert("", "end", values=(nome, "Sim" if nome == default else ""))

        def set_default():
            item = tree.focus()
            if not item:
                return
            nome = tree.item(item, "values")[0]
            set_default_character(self.conn, nome)
            refresh()
            self.refresh_insert_combos()
            self.recarregar_filtros_analises()
            self.refresh_list_filters()

        def add_new():
            nome = simpledialog.askstring("Novo personagem", "Nome do personagem:", parent=win)
            if nome:
                add_character(self.conn, nome)
                refresh()
                self.refresh_insert_combos()
                self.recarregar_filtros_analises()
                self.refresh_list_filters()

        def delete_sel():
            item = tree.focus()
            if not item:
                return
            nome = tree.item(item, "values")[0]
            if messagebox.askyesno("Confirmar", f"Apagar personagem '{nome}'? (não remove hunts já salvas)"):
                delete_character(self.conn, nome)
                refresh()
                self.refresh_insert_combos()
                self.recarregar_filtros_analises()
                self.refresh_list_filters()

        btns = ttk.Frame(win); btns.pack(pady=5)
        ttk.Button(btns, text="Definir como Default", command=set_default).pack(side="left", padx=5)
        ttk.Button(btns, text="Adicionar", command=add_new).pack(side="left", padx=5)
        ttk.Button(btns, text="Remover", command=delete_sel).pack(side="left", padx=5)

        refresh()

    def gerenciar_locais(self):
        win = tk.Toplevel(self)
        win.title("Gerenciar Locais")
        win.geometry("420x280")
        tree = ttk.Treeview(win, columns=("nome",), show="headings")
        tree.heading("nome", text="Local")
        tree.column("nome", width=360)
        tree.pack(fill="both", expand=True, padx=5, pady=5)

        def refresh():
            tree.delete(*tree.get_children())
            for nome in list_locations(self.conn):
                tree.insert("", "end", values=(nome,))

        def add_new():
            nome = simpledialog.askstring("Novo local", "Nome do local:", parent=win)
            if nome:
                add_location(self.conn, nome)
                refresh()
                self.refresh_insert_combos()

        def delete_sel():
            item = tree.focus()
            if not item:
                return
            nome = tree.item(item, "values")[0]
            if messagebox.askyesno("Confirmar", f"Apagar local '{nome}'?"):
                delete_location(self.conn, nome)
                refresh()
                self.refresh_insert_combos()

        btns = ttk.Frame(win); btns.pack(pady=5)
        ttk.Button(btns, text="Adicionar", command=add_new).pack(side="left", padx=5)
        ttk.Button(btns, text="Remover", command=delete_sel).pack(side="left", padx=5)

        refresh()


if __name__ == "__main__":
    app = App()
    app.mainloop()
