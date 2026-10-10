import customtkinter as ctk
import tkinter as tk  # Keep for minimal fallback if needed
from tkinter import messagebox
from datetime import datetime, date, timedelta
from typing import Optional, List
import os

from src.application.interfaces.repository import HuntRepository
from src.domain.entities import Hunt, Monster
from src.infrastructure.parser.log_parser import LogParser
from src.infrastructure.config_repository import ConfigRepository

ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

class MainApp(ctk.CTk):
    def __init__(self, repository: HuntRepository, parser: LogParser):
        super().__init__()
        self.repo = repository
        self.parser = parser
        self.config = ConfigRepository()
        
        self.title("Hunt-Analyzer")
        
        # Icon
        try:
            # 1. Try .icns for macOS Dock/Window (standard way)
            if os.path.exists("tibia-analyzer.icns"):
                self.wm_iconbitmap("tibia-analyzer.icns")
            
            # 2. Try .png with iconphoto (Cross-platform and fallback for some macOS contexts)
            # This often fixes the dock icon when running from source if .icns fails
            if os.path.exists("tibia-analyzer.png"):
                icon_img = tk.PhotoImage(file="tibia-analyzer.png")
                self.wm_iconphoto(True, icon_img)
        except Exception as e:
            print(f"Warning: Could not load icon: {e}")

        # Restore configuration
        saved_geo = self.repo.get_setting("window_geometry")
        if saved_geo:
            self.geometry(saved_geo)
        else:
            w = self.winfo_screenwidth()
            h = self.winfo_screenheight()
            self.geometry(f"{1180}x{720}+0+0")
            
        self.minsize(1180, 720)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.log_folder = self.config.get_log_dir()
        self.period_mode = "mes"

        self._build_ui()
        self.after(1000, self.check_auto_import)

    def on_close(self):
        try:
            geo = self.geometry()
            self.repo.set_setting("window_geometry", geo)
        except Exception:
            pass
        self.destroy()

    def _build_ui(self):
        # Use CTkTabview for modern look
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=8, pady=8)

        # Create tabs
        self.tabview.add("Inserir")
        self.tabview.add("Análises")
        self.tabview.add("Hunts")

        # We will create separate classes/frames for each tab to improve SRP
        from src.ui.tab_insert import InsertTab
        from src.ui.tab_analysis import AnalysisTab
        from src.ui.tab_hunts import HuntsTab

        # Parent is now the specific tab frame within tabview
        self.tab_inserir = InsertTab(self.tabview.tab("Inserir"), self.repo, self.parser, self)
        self.tab_inserir.pack(fill="both", expand=True)

        self.tab_analises = AnalysisTab(self.tabview.tab("Análises"), self.repo, self)
        self.tab_analises.pack(fill="both", expand=True)
        
        self.tab_hunts = HuntsTab(self.tabview.tab("Hunts"), self.repo, self)
        self.tab_hunts.pack(fill="both", expand=True)

    def refresh_all(self):
        """Called when data changes"""
        # self.tab_inserir.refresh_combos() # if needed
        self.tab_analises.refresh_options()
        self.tab_hunts.refresh_list()

    def check_auto_import(self, silent=True):
        folder = self.config.get_log_dir()
        if not folder or not os.path.exists(folder):
            if not silent:
                 messagebox.showwarning("Aviso", "Pasta de logs não configurada ou inválida.")
            return

        print(f"Checking for new hunts in {folder}...")
        
        imported_count = 0
        default_char = self.repo.get_default_character() or "Nerdola Farmador"

        try:
            for fname in os.listdir(folder):
                if not (fname.lower().endswith(".txt") or fname.lower().endswith(".log")): 
                    continue
                fpath = os.path.join(folder, fname)
                
                content = ""
                try:
                    with open(fpath, "r", encoding="utf-8") as f: 
                        content = f.read()
                except UnicodeDecodeError:
                    try:
                        with open(fpath, "r", encoding="latin-1") as f: 
                            content = f.read()
                    except: continue
                except: continue
                
                if not content: continue

                info = self.parser.parse_hunt_data(content)
                if not info["data_inicio"]: continue
                
                # Check existence: Character + Date + StartTime
                # We assume these log files belong to the default character 
                filters = {
                    "character": default_char,
                    "date": info["data_inicio"],
                    "start_time": info["hora_inicio"]
                }
                
                exists_list = self.repo.get_all(filters)
                if not exists_list:
                    # Parse and Insert
                    monsters_data = self.parser.extract_monsters(content)
                    monsters_entities = [
                        Monster(name=n, amount=q) for n, q in monsters_data
                    ]

                    hunt = Hunt(
                        id=None,
                        character=default_char,
                        location="Desconhecido", # Default location
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
                        raw_text=content,
                        monsters=monsters_entities
                    )
                    
                    try:
                        self.repo.save(hunt)
                        imported_count += 1
                    except Exception as e:
                        print(f"Error saving {fname}: {e}")
            
            if imported_count > 0:
                self.refresh_all()
                msg = f"Importadas {imported_count} novas hunts (Personagem: {default_char})."
                messagebox.showinfo("Auto Importação", msg)
            elif not silent:
                messagebox.showinfo("Verificação", f"Nenhuma hunt nova encontrada para {default_char}.")
                
        except Exception as e:
            print(f"Auto-check error: {e}")
            if not silent:
                messagebox.showerror("Erro check", str(e))

