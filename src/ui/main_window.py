import customtkinter as ctk
import tkinter as tk  # Keep for minimal fallback if needed
from tkinter import messagebox
from datetime import datetime, date, timedelta
from typing import Optional, List
import os

from src.application.interfaces.repository import HuntRepository
from src.domain.entities import Hunt
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

    def check_auto_import(self):
        folder = self.config.get_log_dir()
        if not folder or not os.path.exists(folder):
            return

        print(f"Checking for new hunts in {folder}...")
        # Simple check logic: iterate all files, parse, see if exists
        # To avoid performance hit, maybe we should only check if 'last_modified' > 'last_check'
        # But user asked to "check for new hunts".
        
        # We can reuse the import logic from TabInsert if possible, or duplicate/extract it.
        # Let's import the file content checking logic.
        
        new_count = 0
        try:
            for fname in os.listdir(folder):
                if not (fname.endswith(".txt") or fname.endswith(".log")): continue
                fpath = os.path.join(folder, fname)
                
                # Parsing every file might be slow if many files. 
                # Optimization: Check if we already have a hunt with same date/start_time/char?
                # For now, simplest approach:
                
                try:
                    with open(fpath, "r", encoding="utf-8") as f: content = f.read()
                except: continue
                
                info = self.parser.parse_hunt_data(content)
                if not info["data_inicio"]: continue
                
                # Check existance by Unique constraint (approx)
                # Ideally Repo should have exists(date, start_time, character)
                # Doing a lightweight check in memory if list small, or just parse one by one.
                
                # To really do "Auto Import" we would need to auto-insert. 
                # But requirement says "Alert the user if there is new hunts".
                # It does NOT say "Import them". Just "Alert".
                
                # To know if they are "new", we must know if they are in DB.
                filters = {"date": info["data_inicio"], "start_time": info["hora_inicio"]} 
                # If char is known, add it.
                
                exists = self.repo.get_all(filters)
                if not exists:
                    new_count += 1
            
            if new_count > 0:
                messagebox.showinfo("Novas Hunts", f"Encontradas {new_count} hunts novas na pasta configurada!\nVá na aba Inserir para importá-las.")
                
        except Exception as e:
            print(f"Auto-check error: {e}")

