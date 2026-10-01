# -*- coding: utf-8 -*-
"""单位属性编辑器：按顺序显示和编辑注册单位的属性，并支持主/副武器编辑。"""

import tkinter as tk
from tkinter import ttk, messagebox

from config import UI_FONT_FAMILY, UI_FONT_SIZE, LIST_FONT_FAMILY, LIST_FONT_SIZE


class UnitEditorDialog(tk.Toplevel):
    """单位属性编辑器对话框。"""

    # 单位键的顺序与中文名
    # (键名, 中文名, 适用类型, 输入方式)
    UNIT_KEYS = [
        ("Name",           "单位名",         'all',          'text'),
        ("UIName",         "单位名CSF",       'all',          'text'),
        ("Image",          "单位图像",       'all',          'text'),
        ("Cameo",          "建造图标",       'all',          'text'),
        ("AltCameo",       "一星建造图标",   'all',          'text'),
        ("Strength",       "血量",           'all',          'text'),
        ("Cost",           "造价",           'all',          'text'),
        ("Soylent",        "售价",           'all',          'text'),
        ("BuildCat",       "建筑类型",       'building',     'choice'),
        ("Prerequisite",   "建造前提",       'all',          'text'),
        ("Adjacent",       "建筑延伸距离",   'building',     'text'),
        ("Speed",          "移动速度",       'non_building', 'text'),
        ("MovementZone",   "移动类型",       'non_building', 'choice'),
        ("Locomotor",      "移动方式",       'non_building', 'choice'),
        ("Size",           "所占运输空间",   'non_building', 'text'),
        ("Armor",          "装甲",           'all',          'choice'),
        ("Primary",        "主武器",         'all',          'text'),
        ("Secondary",      "副武器",         'all',          'text'),
        ("Sight",          "视野",           'all',          'text'),
        ("TechLevel",      "科技等级",       'all',          'text'),
        ("Owner",          "所属国",         'all',          'text'),
        ("Power",          "耗电",           'building',     'text'),
        ("Capturable",     "能否被占领",     'building',     'yesno'),
        ("Spyable",        "能否被渗透",     'building',     'yesno'),
        ("SpySat",         "能否开全图",     'building',     'yesno'),
        ("Immune",            "是否无敌",     'all',         'yesno'),
        ("ImmuneToPsionics",  "是否免疫心控", 'all',         'yesno'),
        ("ImmuneToRadiation", "是否免疫辐射", 'all',         'yesno'),
        ("ImmuneToPoison",    "是否免疫毒素", 'all',         'yesno'),
        ("Trainable",         "能否升级",     'all',         'yesno'),
    ]

    # 建筑默认 yes 的键
    BUILDING_DEFAULT_YES = {
        "ImmuneToPsionics", "ImmuneToRadiation", "ImmuneToPoison",
    }

    # 下拉项：(显示文本, 实际值)
    CHOICES = {
        "BuildCat": [
            ("防御建筑 (Combat)", "Combat"),
            ("基础设施 (Infrastructure)", "Infrastructure"),
            ("资源建筑 (Resource)", "Resource"),
            ("电力建筑 (Power)", "Power"),
            ("科技建筑 (Tech)", "Tech"),
            ("其他 (DontCare)", "DontCare"),
        ],
        "MovementZone": [
            ("两栖 (Amphibious)", "Amphibious"),
            ("两栖碾压 (AmphibiousCrusher)", "AmphibiousCrusher"),
            ("两栖破坏 (AmphibiousDestroyer)", "AmphibiousDestroyer"),
            ("陆地碾压 (Crusher)", "Crusher"),
            ("陆地全碾压 (CrusherAll)", "CrusherAll"),
            ("陆地破坏 (Destroyer)", "Destroyer"),
            ("飞行 (Fly)", "Fly"),
            ("步兵 (Infantry)", "Infantry"),
            ("步兵破坏 (InfantryDestroyer)", "InfantryDestroyer"),
            ("常规 (Normal)", "Normal"),
            ("钻地 (Subterannean)", "Subterannean"),
            ("水中 (Water)", "Water"),
            ("水陆两栖 (WaterBeach)", "WaterBeach"),
        ],
        "Locomotor": [
            ("VXL地面载具 ({4A582741-9839-11d1-B709-00A024DDAFD1})",
             "{4A582741-9839-11d1-B709-00A024DDAFD1}"),
            ("悬浮载具 ({4A582742-9839-11d1-B709-00A024DDAFD1})",
             "{4A582742-9839-11d1-B709-00A024DDAFD1}"),
            ("钻地载具 ({4A582743-9839-11d1-B709-00A024DDAFD1})",
             "{4A582743-9839-11d1-B709-00A024DDAFD1}"),
            ("地面步兵 ({4A582744-9839-11d1-B709-00A024DDAFD1})",
             "{4A582744-9839-11d1-B709-00A024DDAFD1}"),
            ("机场飞机 ({4A582746-9839-11d1-B709-00A024DDAFD1})",
             "{4A582746-9839-11d1-B709-00A024DDAFD1}"),
            ("超时空运动 ({4A582747-9839-11d1-B709-00A024DDAFD1})",
             "{4A582747-9839-11d1-B709-00A024DDAFD1}"),
            ("Jumpjet ({92612C46-F71F-11d1-AC9F-006008055BB5})",
             "{92612C46-F71F-11d1-AC9F-006008055BB5}"),
            ("船 ({2BEA74E1-7CCA-11d3-BE14-00104B62A16C})",
             "{2BEA74E1-7CCA-11d3-BE14-00104B62A16C}"),
            ("V3/无畏导弹 ({B7B49766-E576-11d3-9BD9-00104B972FE8})",
             "{B7B49766-E576-11d3-9BD9-00104B972FE8}"),
        ],
        "Armor": [
            ("无护甲 (none)", "none"),
            ("防弹衣 (flak)", "flak"),
            ("板甲 (plate)", "plate"),
            ("轻型 (light)", "light"),
            ("中型 (medium)", "medium"),
            ("重型 (heavy)", "heavy"),
            ("木质 (wood)", "wood"),
            ("钢铁 (steel)", "steel"),
            ("混凝土 (concrete)", "concrete"),
            ("特殊1 (special_1)", "special_1"),
            ("特殊2 (special_2)", "special_2"),
        ],
    }

    # 武器键顺序
    WEAPON_KEYS = [
        ("Damage",     "伤害"),
        ("ROF",        "攻击间隔"),
        ("Range",      "攻击范围"),
        ("Speed",      "弹道速度"),
        ("Projectile", "发射体"),
        ("Warhead",    "弹头"),
    ]

    REGISTRY_TYPE_NAMES = {
        "InfantryTypes": "步兵",
        "VehicleTypes":  "载具",
        "AircraftTypes": "飞行器",
        "BuildingTypes": "建筑",
    }

    def __init__(self, parent, parser, project_manager, section_names):
        super().__init__(parent)
        self.title("单位属性编辑器")
        self.geometry("1000x750")
        self.transient(parent)
        self.grab_set()

        self.parser = parser
        self.pm = project_manager
        self.section_names = section_names

        self.units = []
        self.displayed_units = []
        self.current_section = None
        self.current_type = None
        self.current_registry = None
        self.key_widgets = {}          # 单位属性 {键名: (widget, 原键名或None, 原值)}
        self.weapon_widgets = {}       # 武器属性 {(武器节名, 键名): (widget, 原键名或None, 原值)}

        self._build()
        self._load_units()

    # ---------------- 构建界面 ----------------

    def _build(self):
        main = ttk.Frame(self)
        main.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 左侧：单位列表
        left = ttk.LabelFrame(main, text="单位列表")
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 5))

        filter_bar = ttk.Frame(left)
        filter_bar.pack(fill=tk.X, padx=3, pady=3)
        ttk.Label(filter_bar, text="过滤:").pack(side=tk.LEFT)
        self.filter_var = tk.StringVar()
        entry = ttk.Entry(filter_bar, textvariable=self.filter_var, width=18)
        entry.pack(side=tk.LEFT, padx=3, fill=tk.X, expand=True)
        self.filter_var.trace_add('write', lambda *a: self._populate_unit_list())

        list_frame = ttk.Frame(left)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)
        sb = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        self.unit_listbox = tk.Listbox(
            list_frame, yscrollcommand=sb.set,
            font=(LIST_FONT_FAMILY, LIST_FONT_SIZE),
            width=36, height=34, exportselection=False)
        sb.config(command=self.unit_listbox.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.unit_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.unit_listbox.bind('<<ListboxSelect>>', lambda e: self._on_unit_selected())

        # 右侧：属性编辑区
        right = ttk.Frame(main)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.title_label = ttk.Label(
            right, text="（未选择单位）",
            font=(UI_FONT_FAMILY, UI_FONT_SIZE + 2, "bold"))
        self.title_label.pack(anchor=tk.W, padx=5, pady=(0, 3))

        self.desc_label = ttk.Label(
            right, text="", foreground="#666666",
            font=(UI_FONT_FAMILY, UI_FONT_SIZE))
        self.desc_label.pack(anchor=tk.W, padx=5, pady=(0, 5))

        # 属性滚动区
        container = ttk.Frame(right)
        container.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(container, highlightthickness=0)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb = ttk.Scrollbar(container, orient=tk.VERTICAL, command=canvas.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.configure(yscrollcommand=vsb.set)

        self.attr_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=self.attr_frame, anchor="nw")

        self.attr_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        # 底部按钮
        btn_bar = ttk.Frame(right)
        btn_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=5)
        ttk.Button(btn_bar, text="保存修改", command=self._save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_bar, text="关闭", command=self.destroy).pack(side=tk.RIGHT)

    # ---------------- 单位列表 ----------------

    def _load_units(self):
        self.units = []
        registry_order = [
            "InfantryTypes", "VehicleTypes", "AircraftTypes", "BuildingTypes",
        ]
        for registry in registry_order:
            if registry not in self.parser.sections:
                continue
            for key, value in self.parser.get_items(registry):
                value = value.strip()
                if not value:
                    continue
                unit_type = 'building' if registry == "BuildingTypes" else 'non_building'
                self.units.append((registry, key, value, unit_type))
        self._populate_unit_list()

    def _populate_unit_list(self):
        self.unit_listbox.delete(0, tk.END)
        self.displayed_units = []
        filter_text = self.filter_var.get().strip().lower()
        for registry, key, section, unit_type in self.units:
            cn = self.section_names.get(section) or ""
            display = f"[{self.REGISTRY_TYPE_NAMES.get(registry, registry)}] {section}"
            if cn:
                display += f"（{cn}）"
            if filter_text:
                if (filter_text not in section.lower()
                        and filter_text not in cn.lower()):
                    continue
            self.unit_listbox.insert(tk.END, display)
            self.displayed_units.append((registry, key, section, unit_type))

    def _on_unit_selected(self):
        sel = self.unit_listbox.curselection()
        if not sel or sel[0] >= len(self.displayed_units):
            return
        registry, key, section, unit_type = self.displayed_units[sel[0]]
        self.current_registry = registry
        self.current_section = section
        self.current_type = unit_type
        self._refresh_attributes()

    # ---------------- 属性区 ----------------

    def _refresh_attributes(self):
        for widget in self.attr_frame.winfo_children():
            widget.destroy()
        self.key_widgets.clear()
        self.weapon_widgets.clear()

        if not self.current_section:
            self.title_label.config(text="（未选择单位）")
            self.desc_label.config(text="")
            return

        cn = self.section_names.get(self.current_section) or ""
        type_name = self.REGISTRY_TYPE_NAMES.get(self.current_registry, "")
        title = f"[{self.current_section}]"
        if cn:
            title += f"（{cn}）"
        self.title_label.config(text=title)
        self.desc_label.config(text=f"类型：{type_name}    注册表：{self.current_registry}")

        items = dict(self.parser.get_items(self.current_section))
        items_lower = {k.lower(): (k, v) for k, v in items.items()}

        row = 0
        for key_name, cn_name, applicable, input_type in self.UNIT_KEYS:
            if applicable == 'building' and self.current_type != 'building':
                continue
            if applicable == 'non_building' and self.current_type == 'building':
                continue

            found_key = None
            found_value = ""
            if key_name.lower() in items_lower:
                found_key, found_value = items_lower[key_name.lower()]

            # 建筑默认 yes
            if (self.current_type == 'building'
                    and key_name in self.BUILDING_DEFAULT_YES
                    and found_key is None):
                found_value = "yes"

            ttk.Label(self.attr_frame, text=f"{cn_name}（{key_name}）:",
                      font=(UI_FONT_FAMILY, UI_FONT_SIZE)).grid(
                row=row, column=0, sticky="w", padx=5, pady=3)

            widget = self._create_widget(input_type, key_name, found_value)
            widget.grid(row=row, column=1, sticky="ew", padx=5, pady=3)
            self.key_widgets[key_name] = (widget, found_key, found_value)
            row += 1

        # 主/副武器编辑区
        self._build_weapon_section(row)

        self.attr_frame.columnconfigure(1, weight=1)

    def _create_widget(self, input_type, key_name, value):
        if input_type == 'choice':
            choices = self.CHOICES.get(key_name, [])
            display_values = [d for d, v in choices]
            # 找到当前值对应的显示文本
            display_now = ""
            for d, v in choices:
                if v.lower() == value.lower():
                    display_now = d
                    break
            if not display_now:
                display_now = value

            var = tk.StringVar(value=display_now)
            cb = ttk.Combobox(self.attr_frame, textvariable=var,
                              values=display_values, state="readonly", width=40)
            # 保存值 <-> 显示文本的映射
            cb.display_to_value = {d: v for d, v in choices}
            cb.value_to_display = {v: d for d, v in choices}
            cb.var = var
            return cb
        elif input_type == 'yesno':
            var = tk.StringVar(value=value if value in ("yes", "no") else "no")
            frame = ttk.Frame(self.attr_frame)
            ttk.Radiobutton(frame, text="yes", variable=var, value="yes").pack(side=tk.LEFT)
            ttk.Radiobutton(frame, text="no", variable=var, value="no").pack(side=tk.LEFT)
            frame.var = var
            return frame
        else:
            var = tk.StringVar(value=value)
            entry = ttk.Entry(self.attr_frame, textvariable=var, width=40)
            entry.var = var
            return entry

    # ---------------- 武器编辑区 ----------------

    def _build_weapon_section(self, start_row):
        # 分隔
        ttk.Separator(self.attr_frame, orient=tk.HORIZONTAL).grid(
            row=start_row, column=0, columnspan=2, sticky="ew", pady=6)
        start_row += 1

        # 读取主副武器的节名
        items = dict(self.parser.get_items(self.current_section))
        items_lower = {k.lower(): v for k, v in items.items()}
        primary = items_lower.get("primary", "").strip()
        secondary = items_lower.get("secondary", "").strip()

        # 弹头可选列表
        warhead_choices = []
        if "Warheads" in self.parser.sections:
            for _, value in self.parser.get_items("Warheads"):
                value = value.strip()
                if value:
                    warhead_choices.append(value)

        # 主武器区
        if primary:
            start_row = self._build_one_weapon(start_row, "主武器", primary, warhead_choices)
        # 副武器区
        if secondary:
            start_row = self._build_one_weapon(start_row, "副武器", secondary, warhead_choices)

    def _build_one_weapon(self, start_row, label, weapon_section, warhead_choices):
        # 标题
        cn = self.section_names.get(weapon_section) or ""
        title = f"【{label}】[{weapon_section}]"
        if cn:
            title += f"（{cn}）"
        ttk.Label(
            self.attr_frame, text=title,
            font=(UI_FONT_FAMILY, UI_FONT_SIZE + 1, "bold"),
            foreground="#004488"
        ).grid(row=start_row, column=0, columnspan=2, sticky="w", padx=5, pady=(4, 2))
        start_row += 1

        # 若武器节不存在，提示一行
        if weapon_section not in self.parser.sections:
            ttk.Label(
                self.attr_frame,
                text=f"（找不到武器节 [{weapon_section}]）",
                foreground="#aa0000",
            ).grid(row=start_row, column=0, columnspan=2, sticky="w", padx=5, pady=2)
            return start_row + 1

        weapon_items = dict(self.parser.get_items(weapon_section))
        weapon_items_lower = {k.lower(): (k, v) for k, v in weapon_items.items()}

        for key_name, cn_name in self.WEAPON_KEYS:
            found_key = None
            found_value = ""
            if key_name.lower() in weapon_items_lower:
                found_key, found_value = weapon_items_lower[key_name.lower()]

            ttk.Label(self.attr_frame, text=f"  {cn_name}（{key_name}）:",
                      font=(UI_FONT_FAMILY, UI_FONT_SIZE)).grid(
                row=start_row, column=0, sticky="w", padx=5, pady=3)

            if key_name == "Warhead":
                # 弹头下拉
                var = tk.StringVar(value=found_value)
                cb = ttk.Combobox(self.attr_frame, textvariable=var,
                                  values=warhead_choices, width=40)
                cb.var = var
                widget = cb
            else:
                var = tk.StringVar(value=found_value)
                entry = ttk.Entry(self.attr_frame, textvariable=var, width=40)
                entry.var = var
                widget = entry

            widget.grid(row=start_row, column=1, sticky="ew", padx=5, pady=3)
            self.weapon_widgets[(weapon_section, key_name)] = (widget, found_key, found_value)
            start_row += 1

        return start_row

    # ---------------- 保存 ----------------

    def _save(self):
        if not self.current_section:
            messagebox.showinfo("提示", "请先选择一个单位", parent=self)
            return

        changed = 0
        added = 0

        # ---- 1. 单位属性 ----
        for key_name, (widget, old_key, old_value) in self.key_widgets.items():
            new_value = self._read_widget_value(widget)
            if old_key is None and new_value == "":
                continue
            if old_key is not None and new_value == old_value:
                continue

            if old_key is not None:
                items = self.parser.get_items(self.current_section)
                for idx, (k, v) in enumerate(items):
                    if k == old_key:
                        self.parser.update_item(self.current_section, idx, old_key, new_value)
                        changed += 1
                        break
            else:
                self.parser.add_item_for_unit_editor(self.current_section, key_name, new_value)
                added += 1

        # ---- 2. 武器属性 ----
        for (weapon_section, key_name), (widget, old_key, old_value) in self.weapon_widgets.items():
            new_value = self._read_widget_value(widget)
            if old_key is None and new_value == "":
                continue
            if old_key is not None and new_value == old_value:
                continue

            if old_key is not None:
                items = self.parser.get_items(weapon_section)
                for idx, (k, v) in enumerate(items):
                    if k == old_key:
                        self.parser.update_item(weapon_section, idx, old_key, new_value)
                        changed += 1
                        break
            else:
                # 如果武器节不存在，跳过（避免往不存在的节添加）
                if weapon_section not in self.parser.sections:
                    continue
                self.parser.add_item_for_unit_editor(weapon_section, key_name, new_value)
                added += 1

        messagebox.showinfo(
            "完成",
            f"已修改 {changed} 项，新增 {added} 项。\n"
            f"请点击菜单「项目 → 保存项目」以写回文件。",
            parent=self)
        self._refresh_attributes()

    def _read_widget_value(self, widget):
        """从控件读取当前值。"""
        if hasattr(widget, 'var'):
            v = widget.var.get().strip()
            # 下拉框：显示文本 -> 实际值
            if hasattr(widget, 'display_to_value'):
                return widget.display_to_value.get(v, v)
            return v
        return ""
