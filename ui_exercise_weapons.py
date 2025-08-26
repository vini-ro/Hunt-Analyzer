import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from exercise_weapons import (
    ExerciseConfig, DummyBonuses,
    Vocation, SkillType, WeaponType,
    calculate_weapons_needed, calculate_reach_with_weapons,
    summarize_result, format_duration
)


class ExerciseWeaponsFrame(ttk.Frame):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self._build_widgets()
        self._wire_events()
        self._toggle_custom()

    # ------------------ UI construction ------------------
    def _build_widgets(self):
        self.columnconfigure(1, weight=1)

        # variables
        self.vocation_var = tk.StringVar(value="knight")
        self.skill_var = tk.StringVar(value="magic")
        self.current_skill_var = tk.StringVar()
        self.percent_var = tk.StringVar()
        self.target_skill_var = tk.StringVar()
        self.loyalty_var = tk.StringVar()
        self.weapon_type_var = tk.StringVar(value="regular")
        self.custom_charges_var = tk.StringVar()
        self.tc_rate_var = tk.StringVar()

        self.private_dummy_var = tk.BooleanVar()
        self.double_skills_var = tk.BooleanVar()
        self.equalize_rates_var = tk.BooleanVar()

        row = 0
        ttk.Label(self, text="Vocation").grid(row=row, column=0, sticky="w", padx=2, pady=2)
        self.vocation_cb = ttk.Combobox(
            self, textvariable=self.vocation_var,
            values=[v.value for v in Vocation if v != Vocation.NONE], state="readonly"
        )
        self.vocation_cb.grid(row=row, column=1, sticky="ew", padx=2, pady=2)

        row += 1
        ttk.Label(self, text="Skill type").grid(row=row, column=0, sticky="w", padx=2, pady=2)
        self.skill_cb = ttk.Combobox(
            self, textvariable=self.skill_var,
            values=[s.value for s in SkillType], state="readonly"
        )
        self.skill_cb.grid(row=row, column=1, sticky="ew", padx=2, pady=2)

        row += 1
        ttk.Label(self, text="Current skill").grid(row=row, column=0, sticky="w", padx=2, pady=2)
        self.current_skill_entry = ttk.Entry(self, textvariable=self.current_skill_var)
        self.current_skill_entry.grid(row=row, column=1, sticky="ew", padx=2, pady=2)

        row += 1
        ttk.Label(self, text="% to next").grid(row=row, column=0, sticky="w", padx=2, pady=2)
        self.percent_entry = ttk.Entry(self, textvariable=self.percent_var)
        self.percent_entry.grid(row=row, column=1, sticky="ew", padx=2, pady=2)

        row += 1
        ttk.Label(self, text="Target skill").grid(row=row, column=0, sticky="w", padx=2, pady=2)
        self.target_skill_entry = ttk.Entry(self, textvariable=self.target_skill_var)
        self.target_skill_entry.grid(row=row, column=1, sticky="ew", padx=2, pady=2)

        row += 1
        ttk.Label(self, text="Loyalty %").grid(row=row, column=0, sticky="w", padx=2, pady=2)
        self.loyalty_entry = ttk.Entry(self, textvariable=self.loyalty_var)
        self.loyalty_entry.grid(row=row, column=1, sticky="ew", padx=2, pady=2)

        row += 1
        ttk.Label(self, text="Weapon type").grid(row=row, column=0, sticky="w", padx=2, pady=2)
        self.weapon_type_cb = ttk.Combobox(
            self, textvariable=self.weapon_type_var,
            values=[w.value for w in WeaponType], state="readonly"
        )
        self.weapon_type_cb.grid(row=row, column=1, sticky="ew", padx=2, pady=2)

        row += 1
        ttk.Label(self, text="Custom charges").grid(row=row, column=0, sticky="w", padx=2, pady=2)
        self.custom_charges_entry = ttk.Entry(self, textvariable=self.custom_charges_var, state="disabled")
        self.custom_charges_entry.grid(row=row, column=1, sticky="ew", padx=2, pady=2)

        row += 1
        self.private_dummy_cb = ttk.Checkbutton(self, text="Private dummy (+10%)", variable=self.private_dummy_var)
        self.private_dummy_cb.grid(row=row, column=0, columnspan=2, sticky="w", padx=2, pady=2)

        row += 1
        self.double_skills_cb = ttk.Checkbutton(self, text="Double skills (×2)", variable=self.double_skills_var)
        self.double_skills_cb.grid(row=row, column=0, columnspan=2, sticky="w", padx=2, pady=2)

        row += 1
        self.equalize_rates_cb = ttk.Checkbutton(self, text="Equalize offensive rates", variable=self.equalize_rates_var)
        self.equalize_rates_cb.grid(row=row, column=0, columnspan=2, sticky="w", padx=2, pady=2)

        row += 1
        ttk.Label(self, text="TC→GP rate").grid(row=row, column=0, sticky="w", padx=2, pady=2)
        self.tc_rate_entry = ttk.Entry(self, textvariable=self.tc_rate_var)
        self.tc_rate_entry.grid(row=row, column=1, sticky="ew", padx=2, pady=2)

        row += 1
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=(4, 2))
        self.calc_btn = ttk.Button(btn_frame, text="Calculate", command=self._on_calculate)
        self.calc_btn.pack(side="left", padx=2)
        self.reach_btn = ttk.Button(btn_frame, text="Reach with N weapons…", command=self._on_reach_with_n)
        self.reach_btn.pack(side="left", padx=2)

        row += 1
        self.output = tk.Text(self, width=60, height=5, state="disabled", wrap="word")
        self.output.grid(row=row, column=0, columnspan=2, sticky="nsew", padx=2, pady=(2, 2))

    def _wire_events(self):
        self.weapon_type_cb.bind("<<ComboboxSelected>>", lambda e: self._toggle_custom())
        for entry in [
            self.current_skill_entry,
            self.percent_entry,
            self.target_skill_entry,
            self.loyalty_entry,
            self.custom_charges_entry,
            self.tc_rate_entry,
        ]:
            entry.bind("<Return>", lambda e: self._on_calculate())

    # ------------------ Helpers ------------------
    def _toggle_custom(self):
        wt = self.weapon_type_var.get()
        if wt == WeaponType.CUSTOM.value:
            self.custom_charges_entry.configure(state="normal")
        else:
            self.custom_charges_entry.configure(state="disabled")
            self.custom_charges_var.set("")

    def _parse_enum(self, value, enum_cls):
        try:
            return enum_cls(value)
        except Exception:
            raise ValueError(f"Invalid {enum_cls.__name__}")

    def _read_int(self, entry, minv=None, maxv=None):
        text = entry.get().strip()
        try:
            val = int(text)
        except Exception:
            raise ValueError("Invalid integer")
        if minv is not None and val < minv:
            raise ValueError(f"Value must be >= {minv}")
        if maxv is not None and val > maxv:
            raise ValueError(f"Value must be <= {maxv}")
        return val

    def _read_float(self, entry, minv=None, maxv=None):
        text = entry.get().strip()
        try:
            val = float(text)
        except Exception:
            raise ValueError("Invalid float")
        if minv is not None and val < minv:
            raise ValueError(f"Value must be >= {minv}")
        if maxv is not None and val > maxv:
            raise ValueError(f"Value must be <= {maxv}")
        return val

    def _build_config(self):
        voc = self._parse_enum(self.vocation_var.get(), Vocation)
        skill = self._parse_enum(self.skill_var.get(), SkillType)
        current = self._read_int(self.current_skill_entry, minv=0)
        percent = self._read_float(self.percent_entry, minv=0, maxv=100)
        target = self._read_int(self.target_skill_entry, minv=0)
        loyalty = self._read_float(self.loyalty_entry, minv=0, maxv=50)
        wt = self._parse_enum(self.weapon_type_var.get(), WeaponType)
        custom = None
        if wt == WeaponType.CUSTOM:
            custom = self._read_int(self.custom_charges_entry, minv=1)
        rate = None
        tc_rate_str = self.tc_rate_var.get().strip()
        if tc_rate_str:
            rate = self._read_float(self.tc_rate_entry, minv=0)
        bonuses = DummyBonuses(
            private_dummy=self.private_dummy_var.get(),
            double_skills=self.double_skills_var.get(),
        )
        cfg = ExerciseConfig(
            vocation=voc,
            skill_type=skill,
            displayed_current_skill=current,
            displayed_percent_to_next=percent,
            displayed_target_skill=target,
            loyalty_pct=loyalty,
            weapon_type=wt,
            custom_charges=custom,
            bonuses=bonuses,
            tc_to_gp_rate=rate,
            equalize_offensive_rates=self.equalize_rates_var.get(),
        )
        return cfg

    # ------------------ Handlers ------------------
    def _on_calculate(self):
        try:
            cfg = self._build_config()
            res = calculate_weapons_needed(cfg)
            self._render_calculate(res)
        except ValueError as e:
            messagebox.showerror("Error", str(e), parent=self)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def _on_reach_with_n(self):
        n = simpledialog.askinteger("Reach", "Number of weapons:", parent=self, minvalue=1)
        if n is None:
            return
        try:
            cfg = self._build_config()
            rr = calculate_reach_with_weapons(cfg, n)
            self._render_reach(rr)
        except ValueError as e:
            messagebox.showerror("Error", str(e), parent=self)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    # ------------------ Renderers ------------------
    def _render_calculate(self, res):
        text = summarize_result(res)
        if "charges/weapon" not in text:
            text += f"\nCharges per weapon: {res.charges_per_weapon}"
        self._write_output(text)

    def _render_reach(self, rr):
        text = (
            f"Reached skill: {rr.reached_skill_integer}\n"
            f"Leftover: {rr.leftover_percent:.2f}%\n"
            f"Charges used: {rr.charges_used}\n"
            f"Time: {format_duration(rr.time_seconds)}"
        )
        self._write_output(text)

    def _write_output(self, text):
        self.output.configure(state="normal")
        self.output.delete("1.0", tk.END)
        self.output.insert(tk.END, text)
        self.output.configure(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Exercise Weapons Calculator")
    root.resizable(False, False)
    frame = ExerciseWeaponsFrame(root)
    frame.pack(fill="both", expand=True)
    root.mainloop()
