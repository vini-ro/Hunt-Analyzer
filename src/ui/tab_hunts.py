import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import os
import re

from src.application.interfaces.repository import HuntRepository
from src.domain.entities import Hunt

class HuntsTab(ctk.CTkFrame):
    def __init__(self, parent, repo: HuntRepository, main_app):
        super().__init__(parent)
        self.repo = repo
        self.main_app = main_app
        self._build()

    def _build(self):
        frm = self
        
        # Filter Frame
        filt = ctk.CTkFrame(frm)
        filt.pack(fill="x", padx=8, pady=6)
        ctk.CTkLabel(filt, text="Personagem").pack(side="left", padx=5)
        self.combo_personagem_list = ctk.CTkComboBox(filt, width=150, state="readonly")
        self.combo_personagem_list.pack(side="left", padx=6)
        ctk.CTkLabel(filt, text="Local contém").pack(side="left", padx=(10,2))
        self.entry_local_filter = ctk.CTkEntry(filt, width=180)
        self.entry_local_filter.pack(side="left", padx=6)
        ctk.CTkButton(filt, text="Atualizar", width=100, command=self.refresh_list).pack(side="left", padx=6)

        # Treeview (Keep ttk for now as CTK has no native table)
        # We need a style wrapper for dark mode treeview usually, but standard works for now.
        cols = ("id","data","inicio","fim","duracao","personagem","local","xp","loot","supplies","pagamento","balance")
        self.tree = ttk.Treeview(frm, columns=cols, show="headings", height=18, selectmode="extended")
        
        for c, w in zip(cols, (60,90,80,80,80,130,180,90,90,90,90,90)):
            self.tree.heading(c, text=c.upper())
            self.tree.column(c, width=w, anchor="center")
            
        self.tree.pack(fill="both", expand=True, padx=8, pady=6)
        
        # Double click -> Edit
        self.tree.bind("<Double-1>", self.edit_selected_hunt)

        # Actions
        actions = ctk.CTkFrame(frm)
        actions.pack(fill="x", padx=8, pady=6)
        ctk.CTkButton(actions, text="Editar", command=self.edit_selected_hunt).pack(side="left", padx=4)
        ctk.CTkButton(actions, text="Exportar selecionadas…", command=self.export_selected_hunts).pack(side="left", padx=4)
        ctk.CTkButton(actions, text="Apagar selecionadas", fg_color="red", hover_color="darkred", command=self.delete_selected_hunts).pack(side="left", padx=4)
        
        self.refresh_list()

    def refresh_list(self):
        # Refresh combo using repo
        chars = self.repo.list_characters()
        default = self.repo.get_default_character()
        
        # Keep current selection if valid
        curr = self.combo_personagem_list.get()
        combo_vals = ["Todos"] + chars
        self.combo_personagem_list["values"] = combo_vals
        if not curr or curr not in combo_vals:
             if default in chars:
                 self.combo_personagem_list.set(default)
             else:
                 self.combo_personagem_list.set("Todos")
        
        # Build filters
        f_char = self.combo_personagem_list.get()
        f_loc = self.entry_local_filter.get().strip()
        
        filters = {}
        if f_char and f_char != "Todos":
            filters["character"] = f_char
        if f_loc:
            filters["location_like"] = f_loc
            
        hunts = self.repo.get_all(filters)
        
        # Populate Tree
        self.tree.delete(*self.tree.get_children())
        for h in hunts:
            # Format display
            hh = int(h.duration_min // 60)
            mm = int(h.duration_min % 60)
            dur = f"{hh:02d}:{mm:02d}h"
            
            data_fmt = h.date
            try:
                data_fmt = datetime.strptime(h.date, "%Y-%m-%d").strftime("%d-%m-%Y")
            except: pass
            
            self.tree.insert("", "end", values=(
                h.id, data_fmt, h.start_time, h.end_time, dur, h.character, h.location,
                h.xp_gain, h.loot, h.supplies, h.payment, h.balance
            ))

    def _get_selected_ids(self):
        sels = self.tree.selection()
        ids = []
        for s in sels:
            vals = self.tree.item(s, "values")
            if vals:
                ids.append(int(vals[0]))
        return ids

    def edit_selected_hunt(self, event=None):
        # Debounce/Prevent accidental double firing if window is already opening
        if self.focus_get() and isinstance(self.focus_get(), tk.Toplevel):
            return "break"

        if event:
            try:
                item = self.tree.identify_row(event.y)
                if item:
                    self.tree.selection_set(item)
            except: pass

        ids = self._get_selected_ids()
        if not ids:
            if event: return "break"
            messagebox.showwarning("Aviso", "Selecione ao menos uma hunt.")
            return
        
        if len(ids) > 1:
            self.batch_edit_selected(ids)
            if event: return "break"
            return
            
        hunt = self.repo.get_by_id(ids[0])
        if not hunt: 
            if event: return "break"
            return
        
        self._open_edit_window(hunt)
        if event:
            return "break"

    def batch_edit_selected(self, ids: list[int]):
        win = ctk.CTkToplevel(self)
        win.title(f"Editar {len(ids)} hunts")
        win.geometry("420x220")
        
        # MacOS / Modal fixes
        win.resizable(False, False)
        win.transient(self.winfo_toplevel())
        win.grab_set()
        win.focus_force()

        ctk.CTkLabel(win, text="Personagem (vazio = não alterar)").grid(row=0, column=0, padx=6, pady=6, sticky="w")
        entry_char = ctk.CTkEntry(win, width=200)
        entry_char.grid(row=0, column=1, padx=6, pady=6, sticky="w")

        ctk.CTkLabel(win, text="Local (vazio = não alterar)").grid(row=1, column=0, padx=6, pady=6, sticky="w")
        entry_loc = ctk.CTkEntry(win, width=200)
        entry_loc.grid(row=1, column=1, padx=6, pady=6, sticky="w")

        def apply_changes(e=None):
            new_char = entry_char.get().strip()
            new_loc = entry_loc.get().strip()
            
            updates = {}
            if new_char: updates["character"] = new_char
            if new_loc: updates["location"] = new_loc

            if not updates:
                win.destroy()
                return

            try:
                self.repo.update_many(ids, updates)
                self.main_app.refresh_all()
                win.destroy()
                messagebox.showinfo("Sucesso", "Hunts atualizadas.")
            except Exception as e:
                messagebox.showerror("Erro", str(e))

        win.bind("<Return>", apply_changes)
        ctk.CTkButton(win, text="Aplicar", command=apply_changes).grid(row=2, column=0, columnspan=2, pady=10)

    def _open_edit_window(self, hunt: Hunt):
        # Check if an edit window is already open?
        # For now, simplistic approach: Force modal + transient + special attributes
        
        win = ctk.CTkToplevel(self)
        win.title(f"Editar Hunt #{hunt.id}")
        
        # Geometry management
        # Position it slightly offset to avoid overlapping exactly if multiple open (though we block interaction)
        x = self.winfo_rootx() + 50
        y = self.winfo_rooty() + 50
        win.geometry(f"600x520+{x}+{y}")
        
        # MacOS Tabbing Prevention Attempts
        win.resizable(False, False) 
        # On some macOS versions, making it non-resizable helps prevent tabbing.
        # attributes("-toolwindow") might also help but changes style
        
        # win.transient(self.winfo_toplevel())  <-- Moved to bottom
        # win.grab_set() <--- Moved to bottom
        win.focus_force()

        labels = [
            ("Personagem","character"), ("Local","location"), ("Data (DD-MM-YYYY)","date"),
            ("Hora início (HH:MM:SS)","start_time"), ("Hora fim (HH:MM:SS)","end_time"),
            ("Duração (min)","duration_min"), ("Raw XP","raw_xp_gain"), ("XP Gain","xp_gain"),
            ("Loot","loot"), ("Supplies","supplies"), ("Balance","balance"),
            ("Damage","damage"), ("Healing","healing")
        ]
        entries = {}
        
        data_fmt = hunt.date
        try:
            data_fmt = datetime.strptime(hunt.date, "%Y-%m-%d").strftime("%d-%m-%Y")
        except: pass
        
        # Temporarily mutate hunt.date for display
        display_vals = hunt.__dict__.copy()
        display_vals["date"] = data_fmt
        
        # Configure grid weight to prevent squash
        win.grid_columnconfigure(1, weight=1)

        for i, (lbl, key) in enumerate(labels):
            ctk.CTkLabel(win, text=lbl).grid(row=i, column=0, sticky="w", padx=6, pady=4)
            e = ctk.CTkEntry(win, width=200)
            e.grid(row=i, column=1, sticky="w", padx=6, pady=4)
            val = display_vals.get(key, "")
            e.insert(0, str(val))
            entries[key] = e
        
        # Ensure transient is applied LAST to prevent geometry issues on macOS
        win.update_idletasks()
        win.lift() 
        win.transient(self.winfo_toplevel())
        win.grab_set()

        def save_changes():
            try:
                vals = {k: entries[k].get().strip() for k in entries}
                # Parse date back
                d_str = vals["date"]
                try:
                    vals["date"] = datetime.strptime(d_str, "%d-%m-%Y").strftime("%Y-%m-%d")
                except:
                    messagebox.showerror("Erro", "Data inválida. Use DD-MM-YYYY.")
                    return
                
                # Update entity
                hunt.character = vals["character"]
                hunt.location = vals["location"]
                hunt.date = vals["date"]
                hunt.start_time = vals["start_time"]
                hunt.end_time = vals["end_time"]
                hunt.duration_min = int(vals["duration_min"] or 0)
                hunt.raw_xp_gain = int(vals["raw_xp_gain"] or 0)
                hunt.xp_gain = int(vals["xp_gain"] or 0)
                hunt.loot = int(vals["loot"] or 0)
                hunt.supplies = int(vals["supplies"] or 0)
                hunt.balance = int(vals["balance"] or 0)
                hunt.damage = int(vals["damage"] or 0)
                hunt.healing = int(vals["healing"] or 0)
                
                self.repo.update(hunt)
                self.main_app.refresh_all()
                win.destroy()
                # messagebox.showinfo("Sucesso", "Hunt atualizada!")  # Removed for faster flow
            except Exception as e:
                messagebox.showerror("Erro", str(e))

        win.bind("<Return>", lambda e: save_changes())
        ctk.CTkButton(win, text="Salvar alterações", command=save_changes).grid(row=len(labels), column=0, columnspan=2, pady=10)

    def delete_selected_hunts(self):
        ids = self._get_selected_ids()
        if not ids: return
        if not messagebox.askyesno("Confirmar", f"Apagar {len(ids)} hunts?"):
            return
        
        self.repo.delete_many(ids)
        self.main_app.refresh_all()
        messagebox.showinfo("Pronto", "Hunts apagadas.")

    def export_selected_hunts(self):
        ids = self._get_selected_ids()
        if not ids: return
        
        folder = filedialog.askdirectory(title="Selecione a pasta de destino")
        if not folder: return
        
        ok = 0
        for hid in ids:
            h = self.repo.get_by_id(hid)
            if not h: continue
            
            def _san(s): return re.sub(r"[^0-9A-Za-z_-]+", "_", s.strip()) if s else ""
            fname = f"hunt_{h.id}_{_san(h.date)}_{_san(h.character)}_{_san(h.location)}.txt"
            
            try:
                # Prefer raw_text if available, else reconstruct (omitted reconstruction for brevity)
                content = h.raw_text or f"Hunt ID {h.id} (Raw text missing)"
                with open(os.path.join(folder, fname), "w", encoding="utf-8") as f:
                    f.write(content)
                ok += 1
            except: pass
            
        messagebox.showinfo("Exportação", f"Exportadas: {ok}")
