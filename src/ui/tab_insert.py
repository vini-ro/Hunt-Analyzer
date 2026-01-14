import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from src.application.interfaces.repository import HuntRepository
from src.infrastructure.parser.log_parser import LogParser
from src.domain.entities import Hunt, Monster

class InsertTab(ctk.CTkFrame):
    def __init__(self, parent, repo: HuntRepository, parser: LogParser, main_app):
        super().__init__(parent)
        self.repo = repo
        self.parser = parser
        self.main_app = main_app
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="Personagem").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.combo_personagem_insert = ctk.CTkComboBox(self, width=200, state="readonly")
        self.combo_personagem_insert.grid(row=0, column=1, sticky="w", padx=5, pady=5)

        ctk.CTkButton(self, text="Gerenciar Personagens", command=self.manage_characters).grid(row=0, column=2, padx=5)

        ctk.CTkLabel(self, text="Local").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.combo_local_insert = ctk.CTkComboBox(self, width=200)
        self.combo_local_insert.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        ctk.CTkButton(self, text="Gerenciar Locais", command=self.manage_locations).grid(row=1, column=2, padx=5)

        btns = ctk.CTkFrame(self)
        btns.grid(row=0, column=3, rowspan=2, padx=5, pady=5, sticky="w")
        ctk.CTkButton(btns, text="Abrir Arquivo Hunt", command=self.abrir_arquivo).pack(fill="x", pady=2)
        ctk.CTkButton(btns, text="Importar Arquivo(s) …", command=self.importar_arquivos).pack(fill="x", pady=2)
        
        ctk.CTkLabel(self, text="Conteúdo da Hunt").grid(row=2, column=0, sticky="nw", padx=5, pady=(10, 0))
        self.text_dados = ctk.CTkTextbox(self, width=800, height=400)
        self.text_dados.grid(row=2, column=1, columnspan=3, padx=5, pady=(10, 0), sticky="nsew")

        ctk.CTkButton(self, text="Salvar Hunt Atual", command=self.salvar_hunt_atual).grid(row=3, column=1, pady=10, sticky="w")

        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        self.refresh_combos()

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
            
            # Logic to save directly
            info = self.parser.parse_hunt_data(conteudo)
            if not info["data_inicio"] and not info["hora_inicio"]:
                falhas += 1
                continue
                
            # Default fallback character/location for bulk import
            def_char = self.repo.get_default_character() or "Desconhecido"
            def_loc = "Desconhecido"
            
            monsters_data = self.parser.extract_monsters(conteudo)
            monsters_entities = [Monster(name=n, amount=q) for n, q in monsters_data]
            
            hunt = Hunt(
                id=None,
                character=def_char,
                location=def_loc,
                date=info["data_inicio"] or "",
                start_time=info["hora_inicio"] or "",
                end_time=info["hora_fim"] or "",
                duration_min=info["duracao_min"],
                raw_xp_gain=info["raw_xp_gain"],
                xp_gain=info["xp_gain"],
                loot=info["loot"],
                supplies=info["supplies"],
                balance=info["balance"],
                damage=info["damage"],
                healing=info["healing"],
                raw_text=conteudo,
                monsters=monsters_entities
            )
            try:
                self.repo.save(hunt)
                ok += 1
            except:
                falhas += 1

        messagebox.showinfo("Importação concluída", f"Sucesso: {ok}\nFalhas: {falhas}")
        self.main_app.refresh_all()

    def salvar_hunt_atual(self):
        dados_hunt = self.text_dados.get("1.0", tk.END).strip()
        personagem = self.combo_personagem_insert.get().strip()
        local = self.combo_local_insert.get().strip()

        if not personagem or not local or not dados_hunt:
            messagebox.showwarning("Aviso", "Informe Personagem, Local e carregue/cole a Hunt.")
            return

        info = self.parser.parse_hunt_data(dados_hunt)
        monsters_data = self.parser.extract_monsters(dados_hunt)
        
        monsters_entities = [Monster(name=n, amount=q) for n, q in monsters_data]
        
        hunt = Hunt(
            id=None,
            character=personagem,
            location=local,
            date=info["data_inicio"] or "",
            start_time=info["hora_inicio"] or "",
            end_time=info["hora_fim"] or "",
            duration_min=info["duracao_min"],
            raw_xp_gain=info["raw_xp_gain"],
            xp_gain=info["xp_gain"],
            loot=info["loot"],
            supplies=info["supplies"],
            balance=info["balance"],
            damage=info["damage"],
            healing=info["healing"],
            raw_text=dados_hunt,
            monsters=monsters_entities
        )

        try:
            self.repo.save(hunt)
            messagebox.showinfo("Sucesso", "Hunt salva com sucesso!")
            self.main_app.refresh_all()
        except Exception as e:
             messagebox.showerror("Erro", str(e))

    def manage_characters(self):
        win = ctk.CTkToplevel(self)
        win.title("Gerenciar Personagens")
        win.geometry("420x280")
        
        win.transient(self.winfo_toplevel())
        win.grab_set()

        tree = ttk.Treeview(win, columns=("nome","default"), show="headings")
        tree.heading("nome", text="Nome")
        tree.heading("default", text="Default")
        tree.column("nome", width=260)
        tree.column("default", width=80, anchor="center")
        tree.pack(fill="both", expand=True, padx=5, pady=5)

        def refresh():
            tree.delete(*tree.get_children())
            default = self.repo.get_default_character()
            for nome in self.repo.list_characters():
                tree.insert("", "end", values=(nome, "Sim" if nome == default else ""))

        def set_default():
            item = tree.focus()
            if not item: return
            nome = tree.item(item, "values")[0]
            self.repo.set_default_character(nome)
            refresh()
            self.main_app.refresh_all()

        def add_new():
            nome = simpledialog.askstring("Novo personagem", "Nome do personagem:", parent=win)
            if nome:
                self.repo.add_character(nome)
                refresh()
                self.main_app.refresh_all()

        def delete_sel():
            item = tree.focus()
            if not item: return
            nome = tree.item(item, "values")[0]
            if messagebox.askyesno("Confirmar", f"Apagar personagem '{nome}'?"):
                self.repo.delete_character(nome)
                refresh()
                self.main_app.refresh_all()

        btns = ctk.CTkFrame(win); btns.pack(pady=5)
        ctk.CTkButton(btns, text="Definir como Default", command=set_default).pack(side="left", padx=5)
        ctk.CTkButton(btns, text="Adicionar", command=add_new).pack(side="left", padx=5)
        ctk.CTkButton(btns, text="Remover", fg_color="red", hover_color="darkred", command=delete_sel).pack(side="left", padx=5)
        refresh()

    def manage_locations(self):
        win = ctk.CTkToplevel(self)
        win.title("Gerenciar Locais")
        win.geometry("420x280")
        
        win.transient(self.winfo_toplevel())
        win.grab_set()

        tree = ttk.Treeview(win, columns=("nome",), show="headings")
        tree.heading("nome", text="Local")
        tree.column("nome", width=360)
        tree.pack(fill="both", expand=True, padx=5, pady=5)

        def refresh():
            tree.delete(*tree.get_children())
            for nome in self.repo.list_locations():
                tree.insert("", "end", values=(nome,))

        def add_new():
            nome = simpledialog.askstring("Novo local", "Nome do local:", parent=win)
            if nome:
                self.repo.add_location(nome)
                refresh()
                self.main_app.refresh_all()

        def delete_sel():
            item = tree.focus()
            if not item: return
            nome = tree.item(item, "values")[0]
            if messagebox.askyesno("Confirmar", f"Apagar local '{nome}'?"):
                self.repo.delete_location(nome)
                refresh()
                self.main_app.refresh_all()

        btns = ctk.CTkFrame(win); btns.pack(pady=5)
        ctk.CTkButton(btns, text="Adicionar", command=add_new).pack(side="left", padx=5)
        ctk.CTkButton(btns, text="Remover", fg_color="red", hover_color="darkred", command=delete_sel).pack(side="left", padx=5)
        refresh()

    def refresh_combos(self):
        chars = self.repo.list_characters()
        locs = self.repo.list_locations()
        
        # CTk uses configure(values=...)
        self.combo_personagem_insert.configure(values=chars)
        self.combo_local_insert.configure(values=locs)
        
        default = self.repo.get_default_character()
        current = self.combo_personagem_insert.get()
        if not current and default in chars:
            self.combo_personagem_insert.set(default)

