"""右侧面板：键值表格 + 说明区。"""
import re
import tkinter as tk
from tkinter import ttk, messagebox

from config import (
    UI_FONT_FAMILY, UI_FONT_SIZE,
    DESC_FONT_FAMILY, DESC_FONT_SIZE,
    WINDOW_HEIGHT,
    REGISTRY_SECTIONS, REGISTRY_KEY_AS_NAME,
)
from ui.dialogs import KeyValueDialog


class DetailView:
    """右侧面板：显示选中节的键值对，并提供说明区。

    回调：
        on_status(text)  更新状态栏
    """

    def __init__(self, parent, parser, explanation, section_names,
                 classifier, get_filter_text, on_status):
        self.parser = parser
        self.explanation = explanation
        self.section_names = section_names
        self.classifier = classifier
        self.get_filter_text = get_filter_text
        self.on_status = on_status

        self.current_section = None
        self.current_category = None
        self.tree_row_map = {}
        self.project_mode = False
        self._build(parent)

    # ---------------- 构建界面 ----------------

    def _build(self, parent):
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill=tk.BOTH, expand=True)

        self.right_paned = ttk.PanedWindow(self.frame, orient=tk.VERTICAL)
        self.right_paned.pack(fill=tk.BOTH, expand=True)

        kv_frame = ttk.Frame(self.right_paned)
        self.right_paned.add(kv_frame, weight=3)

        self.right_title = ttk.Label(kv_frame, text="键值对信息:",
                                     font=(UI_FONT_FAMILY, UI_FONT_SIZE + 1, "bold"))
        self.right_title.pack(anchor=tk.W)

        find_bar = ttk.Frame(kv_frame)
        find_bar.pack(fill=tk.X, pady=(3, 0))

        ttk.Label(find_bar, text="查找键:").pack(side=tk.LEFT, padx=(0, 3))
        self.find_key_var = tk.StringVar()
        self.find_entry = ttk.Entry(find_bar, textvariable=self.find_key_var, width=24)
        self.find_entry.pack(side=tk.LEFT, padx=3)
        self.find_entry.bind('<Return>', lambda e: self.find_next_key())
        self.find_entry.bind('<Escape>', lambda e: self._clear_find())

        ttk.Button(find_bar, text="下一个", command=self.find_next_key, width=8).pack(side=tk.LEFT, padx=3)
        ttk.Button(find_bar, text="清除", command=self._clear_find, width=6).pack(side=tk.LEFT, padx=3)

        sort_bar = ttk.Frame(kv_frame)
        sort_bar.pack(fill=tk.X, pady=(3, 0))
        ttk.Label(sort_bar, text="排序:").pack(side=tk.LEFT)
        self.kv_sort_var = tk.StringVar(value="文件顺序")
        c = ttk.Combobox(sort_bar, textvariable=self.kv_sort_var,
                         values=["文件顺序", "按键名", "按值名"],
                         state="readonly", width=10)
        c.pack(side=tk.LEFT, padx=3)
        c.bind('<<ComboboxSelected>>', lambda e: self.show_section(self.current_section))

        # 查找模式：键名 / 值 / 两者
        self.find_mode_var = tk.StringVar(value="both")
        ttk.Radiobutton(find_bar, text="键", variable=self.find_mode_var,
                        value="key").pack(side=tk.LEFT, padx=(10, 0))
        ttk.Radiobutton(find_bar, text="值", variable=self.find_mode_var,
                        value="value").pack(side=tk.LEFT)
        ttk.Radiobutton(find_bar, text="键或值", variable=self.find_mode_var,
                        value="both").pack(side=tk.LEFT)

        # 查找状态（记录上次位置，用于循环查找）
        self._last_find_pos = -1
        self._last_find_kw = ""

        tree_frame = ttk.Frame(kv_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        sb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        self.kv_tree = ttk.Treeview(
            tree_frame, columns=("key", "value"), show="headings",
            yscrollcommand=sb.set, selectmode="extended")
        self.kv_tree.heading("key", text="键 (Key)")
        self.kv_tree.heading("value", text="值 (Value)")
        self.kv_tree.column("key", width=200, minwidth=100)
        self.kv_tree.column("value", width=500, minwidth=200)
        sb.config(command=self.kv_tree.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.kv_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.kv_tree.bind('<Double-1>', self._on_double_click)
        self.kv_tree.bind('<<TreeviewSelect>>', lambda e: self._on_tree_selection_changed())

        desc_frame = ttk.LabelFrame(self.right_paned, text="说明 (Description)")
        self.right_paned.add(desc_frame, weight=1)

        desc_top = ttk.Frame(desc_frame)
        desc_top.pack(fill=tk.X, padx=3, pady=(3, 0))
        self.desc_key_label = ttk.Label(desc_top, text="未选中键",
                                        font=(UI_FONT_FAMILY, UI_FONT_SIZE, "bold"))
        self.desc_key_label.pack(side=tk.LEFT)

        desc_text_frame = ttk.Frame(desc_frame)
        desc_text_frame.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)
        desc_sb = ttk.Scrollbar(desc_text_frame, orient=tk.VERTICAL)
        self.desc_text = tk.Text(
            desc_text_frame, wrap=tk.WORD, yscrollcommand=desc_sb.set,
            font=(DESC_FONT_FAMILY, DESC_FONT_SIZE), state=tk.DISABLED,
            background="#f7f7f7", padx=6, pady=6)
        desc_sb.config(command=self.desc_text.yview)
        desc_sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.desc_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.kv_menu = tk.Menu(self.kv_tree, tearoff=0)
        self.kv_menu.add_command(label="修改选中项", command=self._ctx_edit)
        self.kv_menu.add_command(label="删除选中项", command=self._ctx_delete)
        self.kv_menu.add_separator()
        self.kv_menu.add_command(label="按文件顺序", command=lambda: self._ctx_set_sort("文件顺序"))
        self.kv_menu.add_command(label="按键名排序", command=lambda: self._ctx_set_sort("按键名"))
        self.kv_menu.add_command(label="按值名排序", command=lambda: self._ctx_set_sort("按值名"))

        self.kv_tree.bind("<Button-3>", self._on_kv_right_click)

    def set_initial_sashpos(self):
        """由主窗口在布局完成后调用，设置初始上下分割位置。"""
        try:
            self.frame.update_idletasks()
            total_h = self.right_paned.winfo_height()
            if total_h > 1:
                self.right_paned.sashpos(0, int(total_h * 0.55))
        except Exception:
            pass

    # ---------------- 字体 ----------------

    def apply_fonts(self, ui_font, ui_font_bold, desc_font):
        self.right_title.config(font=ui_font_bold)
        self.desc_key_label.config(font=ui_font_bold)
        self.desc_text.config(font=desc_font)

    # ---------------- 数据显示 ----------------

    def show_section(self, section_name):

        if not section_name:
            for item in self.kv_tree.get_children():
                self.kv_tree.delete(item)
            self.tree_row_map.clear()
            self.current_section = None
            self.right_title.config(text="键值对信息: （未选中节）")
            self._show_description(None)
            return

        self.current_section = section_name
        for item in self.kv_tree.get_children():
            self.kv_tree.delete(item)
        self.tree_row_map.clear()

        items = self.parser.get_items(section_name)
        # 记录原始下标，用于 tree_row_map（因为排序后显示顺序 ≠ 内存顺序）
        indexed = list(enumerate(items))

        sort_mode = self.kv_sort_var.get()
        if sort_mode == "按键名":
            indexed.sort(key=lambda x: x[1][0].lower())
        elif sort_mode == "按值名":
            indexed.sort(key=lambda x: x[1][1].lower())
        # "文件顺序" 保持原顺序

        filter_text = self.get_filter_text().lower()
        for orig_idx, (key, value) in indexed:
            if filter_text:
                if filter_text not in key.lower() and filter_text not in value.lower():
                    continue
            row_id = self.kv_tree.insert("", tk.END, values=(key, value))
            self.tree_row_map[row_id] = orig_idx      # ← 关键：映射到内存里的原下标

        self.current_category = self.classifier.classify(section_name)

        cn = self.section_names.get(section_name)
        title_name = f"[{section_name}]"
        if cn:
            title_name += f"（{cn}）"
        cat_label = {
            'warhead':         '弹头',
            'weapon':          '武器',
            'projectile':      '抛射体',
            'particle_system': '粒子系统',
            'particle':        '粒子',
        }.get(self.current_category, '')
        if cat_label:
            title_name += f"  [{cat_label}]"

        registry = self._get_registry_of_section(section_name)
        if registry:
            reg_name = REGISTRY_SECTIONS[registry][0]
            hint = f"  ← 该节是 [{registry}]（{reg_name}）中的注册项"
            self.right_title.config(
                text=f"键值对信息: {title_name}  ({len(items)} 项){hint}  —— 双击可修改")
            self.on_status(f"{title_name} 是 {reg_name} [{registry}] 中注册的对象")
        elif section_name in REGISTRY_SECTIONS:
            reg_name = REGISTRY_SECTIONS[section_name][0]
            self.right_title.config(
                text=f"键值对信息: {title_name}  ({len(items)} 项)  ← 这是{reg_name}  —— 双击可修改")
            self.on_status(f"{title_name} 是{reg_name}")
        else:
            self.right_title.config(
                text=f"键值对信息: {title_name}  ({len(items)} 项)  —— 双击可修改")
            if cn:
                self.on_status(f"当前节: {title_name}")
            else:
                self.on_status(f"当前节: [{section_name}]（无中文名记录）")

        self._show_description(None)

    def get_current_section(self):
        return self.current_section

    def get_selected_tree_index(self):
        sel = self.kv_tree.selection()
        if not sel:
            return None
        return self.tree_row_map.get(sel[0])

    def get_selected_key_value(self):
        """返回当前选中行的 (key, value)，未选中返回 (None, None)。"""
        idx = self.get_selected_tree_index()
        if idx is None:
            return (None, None)
        items = self.parser.get_items(self.current_section)
        if 0 <= idx < len(items):
            return items[idx]
        return (None, None)

    # ---------------- 编辑操作 ----------------

    def add_key(self, root):
        if getattr(self, 'project_mode', False):
            messagebox.showinfo("提示", "项目模式下禁止添加键")
            return False
        if not self.current_section:
            messagebox.showinfo("提示", "请先在左侧选择一个节")
            return False
        dialog = KeyValueDialog(root, title=f"向 [{self.current_section}] 添加键值")
        if not dialog.result:
            return False
        key, value = dialog.result
        if not key:
            messagebox.showwarning("提示", "键不能为空")
            return False
        self.parser.add_item(self.current_section, key, value)
        self.show_section(self.current_section)
        return True

    def edit_selected(self, root):
        sel = self.kv_tree.selection()
        if len(sel) == 0:
            messagebox.showinfo("提示", "请先在右侧选择一个键值对")
            return False
        if len(sel) > 1:
            messagebox.showinfo("提示", "多选状态下不能修改，请只选一项，"
                                        "或使用「批量删除」")
        if not self.current_section:
            messagebox.showinfo("提示", "请先在左侧选择一个节")
            return False
        idx = self.get_selected_tree_index()
        if idx is None:
            messagebox.showinfo("提示", "请先在右侧选择一个键值对")
            return False
        old_key, old_value = self.parser.get_items(self.current_section)[idx]
        dialog = KeyValueDialog(
            root, title=f"修改 [{self.current_section}] 中的项",
            key=old_key, value=old_value)
        if not dialog.result:
            return False
        new_key, new_value = dialog.result
        if not new_key:
            messagebox.showwarning("提示", "键不能为空")
            return False

        # 项目模式下禁止修改键名
        if getattr(self, 'project_mode', False) and new_key != old_key:
            messagebox.showinfo("提示", "项目模式下禁止修改键名，只允许修改值")
            return False

        self.parser.update_item(self.current_section, idx, new_key, new_value)
        self.show_section(self.current_section)
        return True

    def delete_selected(self):
        sel = self.kv_tree.selection()
        if not sel:
            messagebox.showinfo("提示", "请先在右侧选择至少一个键值对")
            return False

        section = self.current_section
        if not section:
            return False

        idxs = sorted((self.tree_row_map[r] for r in sel), reverse=True)

        if len(idxs) == 1:
            key, _ = self.parser.get_items(section)[idxs[0]]
            if not messagebox.askyesno("确认", f"确定要删除 [{section}] 中的 {key} 吗？"):
                return False
        else:
            if not messagebox.askyesno("确认", f"确定要删除选中的 {len(idxs)} 项吗？"):
                return False

        # 从大到小删，避免索引偏移
        for idx in idxs:
            self.parser.del_item(section, idx)

        # 刷新
        self.show_section(section)
        return True

    def _on_double_click(self, event):
        region = self.kv_tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        row_id = self.kv_tree.identify_row(event.y)
        if not row_id:
            return
        self.kv_tree.selection_set(row_id)
        # 双击直接进入编辑
        parent = self.kv_tree.winfo_toplevel()
        self.edit_selected(parent)

    def _rebuild_item_line(self, section):
        """该节在内存里的项顺序变了之后，重建 (section, idx) -> 行号 的映射。
        思路：只保留那些 idx 仍在有效范围的映射，并按 idx 排序重新分配。
        """
        # 收集该节在 raw_lines 里实际存在的行号（按大小排序）
        linenos = sorted(
            lineno for (s, idx), lineno in self.parser.item_line.items()
            if s == section
        )
        # 先清掉旧的
        for (s, idx) in [k for k in self.parser.item_line if k[0] == section]:
            del self.parser.item_line[(s, idx)]
        # 按新索引顺序重新分配
        for new_idx, lineno in enumerate(linenos):
            if new_idx < len(self.parser.sections[section]):
                self.parser.item_line[(section, new_idx)] = lineno

    # ---------------- 说明区 ----------------

    def refresh_description(self):
        """当外部（比如重新加载说明文件）后，刷新一下说明区。"""
        self._on_tree_selection_changed()

    def _on_tree_selection_changed(self):
        sel = self.kv_tree.selection()
        if not sel:
            self._show_description(None)
            return
        vals = self.kv_tree.item(sel[0], "values")
        if not vals:
            self._show_description(None)
            return
        self._show_description(vals[0])

    def _show_description(self, key):
        self.desc_text.config(state=tk.NORMAL)
        self.desc_text.delete("1.0", tk.END)

        if not key:
            self.desc_key_label.config(text="未选中键")
            self.desc_text.insert(tk.END,
                                  "在右侧键值对列表中选中一行，此处会显示该键的说明。")
            self.desc_text.config(state=tk.DISABLED)
            return

        cat_label = {
            'warhead':         '弹头',
            'weapon':          '武器',
            'projectile':      '抛射体',
            'particle_system': '粒子系统',
            'particle':        '粒子',
        }.get(self.current_category, '')
        if cat_label:
            self.desc_key_label.config(text=f"键: {key}   [{cat_label}]")
        else:
            self.desc_key_label.config(text=f"键: {key}")

        is_art_file = getattr(self, "_is_art_file", False)
        desc = None

        # ---- 1. art 文件：arts 说明优先级最高 ----
        if is_art_file and self.explanation.arts_loaded:
            desc = self.explanation.get_art(key)
            if desc is not None:
                self.desc_text.insert(tk.END, desc)
                self.desc_text.config(state=tk.DISABLED)
                return

        # ---- 2. 武器 / 弹头 / 抛射体 分段说明 ----
        if self.explanation.weapons_loaded:
            if self.current_category == 'weapon':
                desc = self.explanation.get_weapon(key)
            elif self.current_category == 'warhead':
                desc = self.explanation.get_warhead(key)
            elif self.current_category == 'projectile':
                desc = self.explanation.get_projectile(key)
        if desc is None and self.explanation.particles_loaded:
            if self.current_category == 'particle_system':
                desc = self.explanation.get_particle_system(key)
            elif self.current_category == 'particle':
                desc = self.explanation.get_particle(key)

        # 兜底：即使分类不匹配也尝试武器/弹头/抛射体说明
        if desc is None and self.explanation.weapons_loaded:
            if self.current_category == 'weapon':
                desc = self.explanation.get_weapon(key)
            elif self.current_category == 'warhead':
                desc = self.explanation.get_warhead(key)
            elif self.current_category == 'projectile':
                desc = self.explanation.get_projectile(key)

        # ---- 3. AI 说明 ----
        if desc is None and self.explanation.ai_loaded:
            desc = self.explanation.get_ai(key)

        # ---- 4. 通用 rules 说明 ----
        if desc is None and self.explanation.loaded:
            desc = self.explanation.get(key)

        # ---- 5. arts 说明（非 art 文件时，优先级低于 rules） ----
        if desc is None and (not is_art_file) and self.explanation.arts_loaded:
            desc = self.explanation.get_art(key)

        # ---- 6. others 说明 ----
        if desc is None and self.explanation.others_loaded:
            desc = self.explanation.get_others(key)

        # ---- 7. Ares 说明（最低优先级） ----
        if desc is None and self.explanation.ares_loaded:
            desc = self.explanation.get_ares(key)
            if desc:
                desc = "[Ares]\n" + desc

        if desc:
            self.desc_text.insert(tk.END, desc)
        else:
            if (self.explanation.loaded or self.explanation.weapons_loaded
                    or self.explanation.arts_loaded):
                self.desc_text.insert(tk.END, f"（说明文件中没有 '{key}' 的条目）")
            else:
                self.desc_text.insert(tk.END, "（未加载任何说明文件）")
        self.desc_text.config(state=tk.DISABLED)

    # ---------------- 辅助 ----------------

    def _get_registry_of_section(self, section_name):
        for reg_section in REGISTRY_SECTIONS:
            if reg_section not in self.parser.sections:
                continue
            key_as_name = reg_section in REGISTRY_KEY_AS_NAME
            for key, value in self.parser.get_items(reg_section):
                if key_as_name:
                    if key.strip() == section_name:
                        return reg_section
                else:
                    if value.strip() == section_name:
                        return reg_section
        return None

    def find_next_key(self):
        """在当前节的键值对列表中查找下一个匹配项（循环）。"""
        kw = self.find_key_var.get().strip()
        if not kw:
            self.on_status("请输入要查找的键名或值")
            return

        # 关键字变化时重置起点
        if kw != self._last_find_kw:
            self._last_find_kw = kw
            self._last_find_pos = -1

        # 直接基于 Treeview 中已显示的行来查找，这样过滤后的可见项也能查到
        rows = self.kv_tree.get_children()
        if not rows:
            self.on_status("当前节没有可查找的项")
            return

        n = len(rows)
        start = self._last_find_pos + 1
        if start >= n:
            start = 0

        kw_lower = kw.lower()
        mode = self.find_mode_var.get()

        for offset in range(n):
            i = (start + offset) % n
            row_id = rows[i]
            vals = self.kv_tree.item(row_id, "values")
            if not vals:
                continue
            key = str(vals[0])
            value = str(vals[1]) if len(vals) > 1 else ""

            if mode == "key":
                hit = kw_lower in key.lower()
            elif mode == "value":
                hit = kw_lower in value.lower()
            else:
                hit = kw_lower in key.lower() or kw_lower in value.lower()

            if hit:
                self._last_find_pos = i
                self.kv_tree.selection_clear()
                self.kv_tree.selection_set(row_id)
                self.kv_tree.focus(row_id)
                self.kv_tree.see(row_id)
                self._on_tree_selection_changed()   # 更新说明区
                self.on_status(
                    f"已定位到 [{key}] = {value}  (第 {i + 1}/{n} 项)"
                )
                return

        self.on_status(f"未找到匹配 '{kw}' 的键")


    def _clear_find(self):
        """清除查找条件并重置查找位置。"""
        self.find_key_var.set("")
        self._last_find_kw = ""
        self._last_find_pos = -1
        self.on_status("已清除查找")

    def focus_find_entry(self):
        """把焦点交给查找框，方便快捷键触发。"""
        # find_entry 在 _build 里创建，需要保存为实例属性
        if hasattr(self, "find_entry"):
            self.find_entry.focus_set()
            self.find_entry.select_range(0, tk.END)

    def _on_kv_right_click(self, event):
        row_id = self.kv_tree.identify_row(event.y)
        if row_id:
            # 如果右键的行不在当前选中集里，就让它成为唯一选中
            if row_id not in self.kv_tree.selection():
                self.kv_tree.selection_set(row_id)
            # 如果没选中任何行，也允许弹出菜单（用于排序项）
        self.kv_menu.tk_popup(event.x_root, event.y_root)

    def set_project_mode(self, enabled):
        self.project_mode = bool(enabled)
        if self.project_mode:
            pass

    def _ctx_edit(self):
        self.edit_selected(self.kv_tree.winfo_toplevel())

    def _ctx_delete(self):
        self.delete_selected()

    def _ctx_set_sort(self, mode):
        self.kv_sort_var.set(mode)
        self.show_section(self.current_section)


