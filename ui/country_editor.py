# -*- coding: utf-8 -*-
"""国家与所属色编辑器。

数据来源：
- [Sides]     键=阵营名，值=逗号分隔的国家列表
- [Countries] 键=索引，值=国家节名
- [Colors]    键=颜色名，值=R,G,B
"""

import tkinter as tk
from tkinter import ttk, messagebox
import colorsys

from config import (
    UI_FONT_FAMILY, UI_FONT_SIZE,
    LIST_FONT_FAMILY, LIST_FONT_SIZE,
)


class CountryEditorDialog(tk.Toplevel):
    """国家与所属色编辑器对话框。"""

    # 国家可编辑属性
    # (键名, 中文名, 输入方式)
    COUNTRY_KEYS = [
        ("Name",     "国名",       'text'),
        ("UIName",   "显示国名",   'text'),
        ("Multiplay","是否可选",   'yesno'),
        ("Side",     "阵营",       'side'),
        ("Color",    "所属色",     'color'),
        ("SmartAI",  "智慧AI",     'yesno'),
    ]

    def __init__(self, parent, parser, project_manager, section_names):
        super().__init__(parent)
        self.title("国家与所属色编辑器")
        self.geometry("1050x720")
        self.transient(parent)
        self.grab_set()

        self.parser = parser
        self.pm = project_manager
        self.section_names = section_names

        # 派生数据
        self.side_to_countries = {}    # {阵营名: [国家, ...]}
        self.country_to_side = {}      # {国家: 阵营名}
        self.color_map = {}            # {颜色名: (r, g, b)}
        self.color_hex = {}            # {颜色名: "#rrggbb"}

        self.current_side = None
        self.current_country = None
        self.key_widgets = {}

        self._build_data()
        self._build()
        self._populate_side_list()

    # ---------------- 数据构建 ----------------

    def _build_data(self):
        # 1. 读 Sides
        if "Sides" in self.parser.sections:
            for key, value in self.parser.get_items("Sides"):
                side_name = key.strip()
                countries = [c.strip() for c in value.split(",") if c.strip()]
                if side_name:
                    self.side_to_countries[side_name] = countries
                    for c in countries:
                        self.country_to_side[c] = side_name

        # 2. 读 Colors（值是 H,S,V）
        if "Colors" in self.parser.sections:
            for key, value in self.parser.get_items("Colors"):
                color_name = key.strip()
                parts = [p.strip() for p in value.split(",")]
                if len(parts) < 3:
                    continue
                try:
                    h = int(parts[0])
                    s = int(parts[1])
                    v = int(parts[2])
                except ValueError:
                    continue
                h = max(0, min(255, h))
                s = max(0, min(255, s))
                v = max(0, min(255, v))

                # HSV -> RGB
                h_f = (h / 256.0) % 1.0
                s_f = s / 255.0
                v_f = v / 255.0
                r_f, g_f, b_f = colorsys.hsv_to_rgb(h_f, s_f, v_f)
                r = int(round(r_f * 255))
                g = int(round(g_f * 255))
                b = int(round(b_f * 255))

                self.color_map[color_name] = (r, g, b)
                self.color_hex[color_name] = f"#{r:02x}{g:02x}{b:02x}"
                self.color_hsl = getattr(self, "color_hsl", {})
                self.color_hsl[color_name] = (h, s, v)

    # ---------------- 界面构建 ----------------

    def _build(self):
        main = ttk.Frame(self)
        main.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # ---- 左：阵营列表 ----
        left = ttk.LabelFrame(main, text="阵营（Sides）")
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 5))
        sb1 = ttk.Scrollbar(left, orient=tk.VERTICAL)
        self.side_listbox = tk.Listbox(
            left, yscrollcommand=sb1.set,
            font=(LIST_FONT_FAMILY, LIST_FONT_SIZE),
            width=22, height=32, exportselection=False)
        sb1.config(command=self.side_listbox.yview)
        sb1.pack(side=tk.RIGHT, fill=tk.Y)
        self.side_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3, pady=3)
        self.side_listbox.bind('<<ListboxSelect>>', lambda e: self._on_side_selected())

        # ---- 中：国家列表 ----
        mid = ttk.LabelFrame(main, text="该阵营的国家")
        mid.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 5))
        sb2 = ttk.Scrollbar(mid, orient=tk.VERTICAL)
        self.country_listbox = tk.Listbox(
            mid, yscrollcommand=sb2.set,
            font=(LIST_FONT_FAMILY, LIST_FONT_SIZE),
            width=28, height=32, exportselection=False)
        sb2.config(command=self.country_listbox.yview)
        sb2.pack(side=tk.RIGHT, fill=tk.Y)
        self.country_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3, pady=3)
        self.country_listbox.bind('<<ListboxSelect>>', lambda e: self._on_country_selected())

        # ---- 右：属性编辑 ----
        right = ttk.Frame(main)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.title_label = ttk.Label(
            right, text="（未选择国家）",
            font=(UI_FONT_FAMILY, UI_FONT_SIZE + 2, "bold"))
        self.title_label.pack(anchor=tk.W, padx=5, pady=(0, 3))

        self.warn_label = ttk.Label(
            right, text="", foreground="#cc0000",
            font=(UI_FONT_FAMILY, UI_FONT_SIZE))
        self.warn_label.pack(anchor=tk.W, padx=5, pady=(0, 5))

        # 属性区
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
        ttk.Button(btn_bar, text="查看所属色表", command=self._show_color_table).pack(side=tk.LEFT, padx=5)

    # ---------------- 阵营 / 国家列表 ----------------

    def _populate_side_list(self):
        self.side_listbox.delete(0, tk.END)
        self.side_names = []
        for side in self.side_to_countries:
            self.side_names.append(side)
            cn = self.section_names.get(side) or ""
            display = side if not cn else f"{side}（{cn}）"
            self.side_listbox.insert(tk.END, display)

    def _on_side_selected(self):
        sel = self.side_listbox.curselection()
        if not sel:
            return
        side = self.side_names[sel[0]]
        self.current_side = side
        self._populate_country_list(side)

    def _populate_country_list(self, side):
        self.country_listbox.delete(0, tk.END)
        self.country_names = []
        countries = self.side_to_countries.get(side, [])
        for c in countries:
            self.country_names.append(c)
            cn = self.section_names.get(c) or ""
            display = c if not cn else f"{c}（{cn}）"
            self.country_listbox.insert(tk.END, display)

    def _on_country_selected(self):
        sel = self.country_listbox.curselection()
        if not sel:
            return
        self.current_country = self.country_names[sel[0]]
        self._refresh_country_attributes()

    # ---------------- 属性区 ----------------

    def _refresh_country_attributes(self):
        for widget in self.attr_frame.winfo_children():
            widget.destroy()
        self.key_widgets.clear()

        if not self.current_country:
            self.title_label.config(text="（未选择国家）")
            self.warn_label.config(text="")
            return

        cn = self.section_names.get(self.current_country) or ""
        title = f"[{self.current_country}]"
        if cn:
            title += f"（{cn}）"
        self.title_label.config(text=title)

        # 检查该国家节是否存在
        if self.current_country not in self.parser.sections:
            self.warn_label.config(text=f"（找不到国家节 [{self.current_country}]）")
            return

        # 检查 Side 是否与所在阵营相符
        warn_msgs = []
        items = dict(self.parser.get_items(self.current_country))
        items_lower = {k.lower(): (k, v) for k, v in items.items()}
        if "side" in items_lower:
            _, side_value = items_lower["side"]
            side_value = side_value.strip()
            if side_value and self.current_side and side_value != self.current_side:
                warn_msgs.append(
                    f"警告：该国家节的 Side={side_value}，与阵营列表 [{self.current_side}] 不符")
        if warn_msgs:
            self.warn_label.config(text="\n".join(warn_msgs))
        else:
            self.warn_label.config(text="")

        # 所有阵营名（Side 下拉用）
        side_choices = list(self.side_to_countries.keys())
        # 所有颜色名（Color 下拉用）
        color_choices = list(self.color_map.keys())

        row = 0
        for key_name, cn_name, input_type in self.COUNTRY_KEYS:
            found_key = None
            found_value = ""
            if key_name.lower() in items_lower:
                found_key, found_value = items_lower[key_name.lower()]

            ttk.Label(self.attr_frame, text=f"{cn_name}（{key_name}）:",
                      font=(UI_FONT_FAMILY, UI_FONT_SIZE)).grid(
                row=row, column=0, sticky="w", padx=5, pady=4)

            if input_type == 'yesno':
                var = tk.StringVar(value=found_value if found_value in ("yes", "no") else "no")
                frame = ttk.Frame(self.attr_frame)
                ttk.Radiobutton(frame, text="yes", variable=var, value="yes").pack(side=tk.LEFT)
                ttk.Radiobutton(frame, text="no", variable=var, value="no").pack(side=tk.LEFT)
                frame.var = var
                widget = frame

            elif input_type == 'side':
                var = tk.StringVar(value=found_value)
                values_now = list(side_choices)
                if found_value and found_value not in values_now:
                    values_now.insert(0, found_value)
                cb = ttk.Combobox(self.attr_frame, textvariable=var,
                                  values=values_now, state="readonly", width=28)
                cb.var = var
                widget = cb

            elif input_type == 'color':
                frame = ttk.Frame(self.attr_frame)
                var = tk.StringVar(value=found_value)
                values_now = list(color_choices)
                if found_value and found_value not in values_now:
                    values_now.insert(0, found_value)
                cb = ttk.Combobox(frame, textvariable=var,
                                  values=values_now, state="readonly", width=22)
                cb.var = var
                cb.pack(side=tk.LEFT)
                swatch = tk.Canvas(frame, width=40, height=20,
                                   highlightthickness=1,
                                   highlightbackground="#888")
                swatch.pack(side=tk.LEFT, padx=5)

                def update_swatch(*_, var=var, swatch=swatch):
                    name = var.get().strip()
                    swatch.delete("all")
                    if not name:
                        swatch.create_text(20, 10, text="?", fill="#888")
                        return
                    color = self.color_hex.get(name, "")
                    if color:
                        swatch.create_rectangle(0, 0, 40, 20, fill=color, outline="")
                    else:
                        swatch.create_text(20, 10, text="?", fill="#888")

                cb.bind("<<ComboboxSelected>>", update_swatch)
                update_swatch()   # 立即刷新一次，显示初始色块
                frame.color_var = var
                frame.color_combo = cb
                widget = frame
                        

            else:  # text
                var = tk.StringVar(value=found_value)
                entry = ttk.Entry(self.attr_frame, textvariable=var, width=40)
                entry.var = var
                widget = entry

            widget.grid(row=row, column=1, sticky="ew", padx=5, pady=4)
            self.key_widgets[key_name] = (widget, found_key, found_value)
            row += 1

        self.attr_frame.columnconfigure(1, weight=1)

    # ---------------- 保存 ----------------

    def _save(self):
        if not self.current_country:
            messagebox.showinfo("提示", "请先选择一个国家", parent=self)
            return
        if self.current_country not in self.parser.sections:
            messagebox.showinfo("提示", "该国家节不存在", parent=self)
            return

        changed = 0
        added = 0
        for key_name, (widget, old_key, old_value) in self.key_widgets.items():
            # 读取值
            if hasattr(widget, 'var'):
                new_value = widget.var.get().strip()
            elif hasattr(widget, 'color_var'):
                new_value = widget.color_var.get().strip()
            else:
                new_value = ""

            # 键原本不存在且新值为空 -> 跳过
            if old_key is None and new_value == "":
                continue
            # 值未变化 -> 跳过
            if old_key is not None and new_value == old_value:
                continue

            if old_key is not None:
                items = self.parser.get_items(self.current_country)
                for idx, (k, v) in enumerate(items):
                    if k == old_key:
                        self.parser.update_item(self.current_country, idx, old_key, new_value)
                        changed += 1
                        break
            else:
                self.parser.add_item_for_unit_editor(self.current_country, key_name, new_value)
                added += 1

        messagebox.showinfo(
            "完成",
            f"已修改 {changed} 项，新增 {added} 项。\n"
            f"请点击菜单「项目 → 保存项目」以写回文件。",
            parent=self)
        self._refresh_country_attributes()

    # ---------------- 颜色表 ----------------

    def _show_color_table(self):
        win = tk.Toplevel(self)
        win.title("所属色列表 [Colors]")
        win.geometry("360x480")
        win.transient(self)

        ttk.Label(win, text="所属色列表（值 R,G,B）",
                  font=(UI_FONT_FAMILY, UI_FONT_SIZE + 1, "bold")).pack(pady=5)

        frame = ttk.Frame(win)
        frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        sb = ttk.Scrollbar(frame, orient=tk.VERTICAL)
        tree = ttk.Treeview(
            frame, columns=("name", "rgb", "swatch"),
            show="headings", yscrollcommand=sb.set, height=20)
        tree.heading("name", text="颜色名")
        tree.heading("rgb", text="R,G,B")
        tree.heading("swatch", text="色块")
        tree.column("name", width=110)
        tree.column("rgb", width=100)
        tree.column("swatch", width=80, anchor="center")
        sb.config(command=tree.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 用 Canvas 画色块比较麻烦，简单起见把色块画在 Treeview 里无法直接实现，
        # 这里用一个变通方法：在 Treeview 右侧再放一个 Canvas 同步滚动不可行，
        # 所以改为双击一行弹出色块。但用户要求"查看各色对应的颜色"，
        # 我们改用最直接的方式：列出颜色名 + RGB + 一个 Label 显示色块。
        for name, (r, g, b) in self.color_map.items():
            tree.insert("", tk.END, values=(name, f"{r},{g},{b}", ""), tags=(name,))

        # 色块用另一种方式呈现：弹出的小窗中每行一个 Frame
        # 关闭 Treeview，用 Listbox + 右侧色块来展示
        tree.destroy()
        self._show_color_table_simple(win)

    def _show_color_table_simple(self, win):
        # 清空 win 里的内容，重新构建
        for w in win.winfo_children():
            w.destroy()

        ttk.Label(win, text="所属色列表（值 R,G,B）",
                  font=(UI_FONT_FAMILY, UI_FONT_SIZE + 1, "bold")).pack(pady=5)

        outer = ttk.Frame(win)
        outer.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        canvas = tk.Canvas(outer, highlightthickness=0)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = ttk.Scrollbar(outer, orient=tk.VERTICAL, command=canvas.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.configure(yscrollcommand=sb.set)

        inner = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        for name, (r, g, b) in self.color_map.items():
            row = ttk.Frame(inner)
            row.pack(fill=tk.X, padx=3, pady=2)
            color_hex = self.color_hex.get(name, "#ffffff")
            swatch = tk.Canvas(row, width=40, height=18,
                               highlightthickness=1, highlightbackground="#888")
            swatch.create_rectangle(0, 0, 40, 18, fill=color_hex, outline="")
            swatch.pack(side=tk.LEFT, padx=(0, 6))

            h, s, l = self.color_hsl.get(name, (0, 0, 0))
            ttk.Label(
                row,
                text=f"{name}    HSL({h},{s},{l})  →  RGB({r},{g},{b})",
                font=(UI_FONT_FAMILY, UI_FONT_SIZE)
            ).pack(side=tk.LEFT)
