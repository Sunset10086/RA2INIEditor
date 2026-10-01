"""左侧面板：注册列表 + 节列表 + 查找 + 排序。"""
import re
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from config import (
    UI_FONT_FAMILY, UI_FONT_SIZE,
    LIST_FONT_FAMILY, LIST_FONT_SIZE,
    REGISTRY_SECTIONS, REGISTRY_KEY_AS_NAME,
)
from logic.section_classifier import SectionClassifier
from logic import finder


class SectionsView:
    """左侧面板：包含注册列表和节列表。

    回调：
        on_section_selected(section_name)  选中某个节
        on_jump_to_section(section_name)   双击注册项请求跳转
        on_status(text)                    更新状态栏
    """

    SORT_FILE = "文件顺序"
    SORT_NAME = "名称排序"

    def __init__(self, parent, parser, section_names,
                 on_section_selected, on_jump_to_section, on_status):
        self.parser = parser
        self.section_names = section_names
        self.on_section_selected = on_section_selected
        self.on_jump = on_jump_to_section
        self.on_status = on_status
        self.classifier = SectionClassifier(parser)

        self.current_registry = None
        self.displayed_sections = []
        self.displayed_registry_items = []

        self._last_section_find_pos = -1
        self._last_registry_find_pos = -1
        self._last_section_find_kw = ""
        self._last_registry_find_kw = ""

        self.section_sort_var = tk.StringVar(value=self.SORT_FILE)
        self.registry_sort_var = tk.StringVar(value=self.SORT_FILE)
        self.find_section_var = tk.StringVar()
        self.find_reg_var = tk.StringVar()
        self.filter_var = tk.StringVar()
        self.registry_var = tk.StringVar()
        self._clipboard_section = None

        self._build(parent)

    # ---------------- 构建界面 ----------------

    def _build(self, parent):
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill=tk.BOTH, expand=True)

        # ---- 顶部：查找与排序工具条 ----
        self._build_toolbar(self.frame)

        # ---- 注册列表 ----
        reg_frame = ttk.LabelFrame(self.frame, text="注册列表 (Registry)")
        reg_frame.pack(fill=tk.BOTH, expand=False, pady=(0, 5))

        reg_top = ttk.Frame(reg_frame)
        reg_top.pack(fill=tk.X, padx=3, pady=3)
        ttk.Label(reg_top, text="选择注册表:").pack(side=tk.LEFT)
        self.registry_combo = ttk.Combobox(
            reg_top, textvariable=self.registry_var,
            values=[], state="readonly", width=30)
        self.registry_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.registry_combo.bind('<<ComboboxSelected>>', lambda e: self._on_registry_selected())

        reg_list_frame = ttk.Frame(reg_frame)
        reg_list_frame.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)
        reg_sb = ttk.Scrollbar(reg_list_frame, orient=tk.VERTICAL)
        self.registry_listbox = tk.Listbox(
            reg_list_frame, yscrollcommand=reg_sb.set,
            font=(LIST_FONT_FAMILY, LIST_FONT_SIZE),
            height=8, exportselection=False)
        reg_sb.config(command=self.registry_listbox.yview)
        reg_sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.registry_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.registry_listbox.bind('<Double-1>', lambda e: self._on_registry_double_click())
        self.registry_listbox.bind('<<ListboxSelect>>', lambda e: self._on_registry_item_selected())

        self.registry_kv_label = ttk.Label(
            reg_frame, text="键值对: （未选中）",
            font=(UI_FONT_FAMILY, UI_FONT_SIZE),
            foreground="#0055aa", anchor=tk.W, justify=tk.LEFT, wraplength=280)
        self.registry_kv_label.pack(fill=tk.X, padx=5, pady=(0, 4))

        # ---- 节列表 ----
        sec_frame = ttk.LabelFrame(self.frame, text="节 (Section) 列表")
        sec_frame.pack(fill=tk.BOTH, expand=True)

        left_list_frame = ttk.Frame(sec_frame)
        left_list_frame.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)
        left_sb = ttk.Scrollbar(left_list_frame, orient=tk.VERTICAL)
        self.section_listbox = tk.Listbox(
            left_list_frame, yscrollcommand=left_sb.set,
            font=(LIST_FONT_FAMILY, LIST_FONT_SIZE),
            exportselection=False)
        left_sb.config(command=self.section_listbox.yview)
        left_sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.section_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.section_listbox.bind('<<ListboxSelect>>', lambda e: self._on_section_selected())

        self.section_menu = tk.Menu(self.section_listbox, tearoff=0)
        self.section_menu.add_command(label="添加节...",
                                      command=self._ctx_add_section)
        self.section_menu.add_command(label="重命名节...",
                                      command=self._ctx_rename_section,
                                      accelerator="F2")
        self.section_menu.add_separator()
        self.section_menu.add_command(label="复制节",
                                      command=self._ctx_copy_section,
                                      accelerator="Ctrl+C")
        self.section_menu.add_command(label="粘贴节（-c）",
                                      command=self._ctx_paste_section,
                                      accelerator="Ctrl+V")
        self.section_menu.add_separator()
        self.section_menu.add_command(label="删除整节",
                                      command=self._ctx_del_section,
                                      accelerator="Delete")
        self.section_menu.add_separator()
        self.section_menu.add_command(label="按文件顺序",
                                      command=lambda: self._ctx_set_sort(self.SORT_FILE))
        self.section_menu.add_command(label="按名称排序",
                                      command=lambda: self._ctx_set_sort(self.SORT_NAME))

        self.section_listbox.bind("<Button-3>", self._on_section_right_click)
        # 快捷键
        self.section_listbox.bind("<F2>",       lambda e: self._ctx_rename_section())
        self.section_listbox.bind("<Control-c>",lambda e: self._ctx_copy_section())
        self.section_listbox.bind("<Control-v>",lambda e: self._ctx_paste_section())
        self.section_listbox.bind("<Delete>", self._on_section_delete_key)

    def _on_section_delete_key(self, event):
        self._ctx_del_section()
        return "break"   # 阻止事件冒泡到 root，避免 main_window 的全局 Delete 也触发

    def _build_toolbar(self, parent):
        bar = ttk.Frame(parent, padding=(0, 0, 0, 5))
        bar.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(bar, text="查找节:").pack(side=tk.LEFT, padx=(5, 3))
        e = ttk.Entry(bar, textvariable=self.find_section_var, width=18)
        e.pack(side=tk.LEFT, padx=3)
        e.bind('<Return>', lambda ev: self.find_section())
        ttk.Button(bar, text="定位", command=self.find_section, width=6).pack(side=tk.LEFT, padx=3)

        ttk.Separator(bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        ttk.Label(bar, text="查找注册项:").pack(side=tk.LEFT, padx=(5, 3))
        e2 = ttk.Entry(bar, textvariable=self.find_reg_var, width=18)
        e2.pack(side=tk.LEFT, padx=3)
        e2.bind('<Return>', lambda ev: self.find_registry_item())
        ttk.Button(bar, text="定位", command=self.find_registry_item, width=6).pack(side=tk.LEFT, padx=3)

        ttk.Separator(bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        ttk.Label(bar, text="节排序:").pack(side=tk.LEFT, padx=(5, 3))
        c1 = ttk.Combobox(bar, textvariable=self.section_sort_var,
                          values=[self.SORT_FILE, self.SORT_NAME],
                          state="readonly", width=10)
        c1.pack(side=tk.LEFT, padx=3)
        c1.bind('<<ComboboxSelected>>', lambda e: self._on_sort_changed())

        ttk.Label(bar, text="注册表排序:").pack(side=tk.LEFT, padx=(12, 3))
        c2 = ttk.Combobox(bar, textvariable=self.registry_sort_var,
                          values=[self.SORT_FILE, self.SORT_NAME],
                          state="readonly", width=10)
        c2.pack(side=tk.LEFT, padx=3)
        c2.bind('<<ComboboxSelected>>', lambda e: self._on_sort_changed())

        ttk.Label(bar, text="过滤节:").pack(side=tk.LEFT, padx=(12, 3))
        e3 = ttk.Entry(bar, textvariable=self.filter_var, width=15)
        e3.pack(side=tk.LEFT, padx=3)
        self.filter_var.trace_add('write', lambda *a: self._on_filter_changed())

    # ---------------- 字体 ----------------

    def apply_fonts(self, ui_font, list_font):
        self.registry_listbox.config(font=list_font)
        self.section_listbox.config(font=list_font)
        self.registry_kv_label.config(font=ui_font)

    # ---------------- 数据刷新 ----------------

    def refresh_all(self):
        self._populate_section_list(self.filter_var.get().strip())
        self._refresh_registry_dropdown()

    def invalidate_classifier(self):
        self.classifier.invalidate()

    def get_filter_text(self):
        return self.filter_var.get().strip()

    def get_current_section(self, silent=False):
        selection = self.section_listbox.curselection()
        if not selection:
            if not silent:
                messagebox.showinfo("提示", "请先在左侧选择一个节")
            return None
        return self.section_listbox.get(selection[0])

    def get_current_registry(self):
        return self.current_registry

    def get_classifier(self):
        return self.classifier

    # ---------------- 节列表 ----------------

    def _get_sorted_sections(self):
        sections = list(self.parser.get_sections())
        if self.section_sort_var.get() == self.SORT_NAME:
            sections.sort(key=lambda s: s.lower())
        return sections

    def _populate_section_list(self, filter_text=""):
        self.section_listbox.delete(0, tk.END)
        self.displayed_sections = []
        sections = self._get_sorted_sections()
        if filter_text:
            fl = filter_text.lower()
            sections = [s for s in sections if fl in s.lower()]
        for s in sections:
            self.section_listbox.insert(tk.END, s)
            self.displayed_sections.append(s)

    def _on_section_selected(self):
        sel = self.section_listbox.curselection()
        if not sel:
            return
        name = self.section_listbox.get(sel[0])
        self.on_section_selected(name)

    def _on_filter_changed(self):
        # 过滤时也要通知右侧刷新（如果当前有选中节）
        selection = self.section_listbox.curselection()
        if selection:
            name = self.section_listbox.get(selection[0])
            self.on_section_selected(name)
        else:
            self._populate_section_list(self.filter_var.get().strip())

    def _on_sort_changed(self):
        self._last_section_find_pos = -1
        self._last_registry_find_pos = -1
        self._populate_section_list(self.filter_var.get().strip())
        self._populate_registry_list()

    # ---------------- 注册列表 ----------------

    def _refresh_registry_dropdown(self):
        available = []
        for key in REGISTRY_SECTIONS:
            if key in self.parser.sections:
                available.append(f"{REGISTRY_SECTIONS[key][0]}  [{key}]")
        self.registry_combo['values'] = available
        if self.registry_var.get() not in available:
            self.registry_var.set('')
            self.current_registry = None
            self._populate_registry_list()

    def _on_registry_selected(self):
        text = self.registry_var.get()
        m = re.search(r'\[([^\]]+)\]\s*$', text)
        if not m:
            self.current_registry = None
            self._populate_registry_list()
            return
        self.current_registry = m.group(1)
        self._populate_registry_list()
        self._last_registry_find_pos = -1

    def _sorted_registry_entries(self):
        if not self.current_registry:
            return []
        items = list(self.parser.get_items(self.current_registry))
        if self.registry_sort_var.get() == self.SORT_NAME:
            key_as_name = self.current_registry in REGISTRY_KEY_AS_NAME
            if key_as_name:
                items.sort(key=lambda kv: kv[0].lower())
            else:
                items.sort(key=lambda kv: (kv[1] if kv[1] else kv[0]).lower())
        return items

    def _populate_registry_list(self):
        self.registry_listbox.delete(0, tk.END)
        self.displayed_registry_items = []
        self._set_registry_kv_label(None)
        if not self.current_registry:
            return
        key_as_name = self.current_registry in REGISTRY_KEY_AS_NAME
        for key, value in self._sorted_registry_entries():
            display = key if key_as_name else (value if value else key)
            self.registry_listbox.insert(tk.END, display)
            self.displayed_registry_items.append((key, value))

    def _on_registry_item_selected(self):
        if not self.current_registry:
            self._set_registry_kv_label(None)
            return
        sel = self.registry_listbox.curselection()
        if not sel or sel[0] >= len(self.displayed_registry_items):
            self._set_registry_kv_label(None)
            return
        key, value = self.displayed_registry_items[sel[0]]
        reg_name = REGISTRY_SECTIONS[self.current_registry][0]
        self.on_status(f"[{reg_name}] 键 = {key}  =>  值 = {value}")
        self._set_registry_kv_label((key, value))

    def _set_registry_kv_label(self, kv):
        if kv is None:
            self.registry_kv_label.config(text="键值对: （未选中）")
        else:
            self.registry_kv_label.config(text=f"键: {kv[0]}    值: {kv[1]}")

    def _on_registry_double_click(self):
        if not self.current_registry:
            return
        sel = self.registry_listbox.curselection()
        if not sel or sel[0] >= len(self.displayed_registry_items):
            return
        key, value = self.displayed_registry_items[sel[0]]
        if self.current_registry in REGISTRY_KEY_AS_NAME:
            target = key.strip()
        else:
            target = value.strip() if value.strip() else key.strip()
        if target:
            self.on_jump(target)

    def select_registry(self, section_name):
        for key in REGISTRY_SECTIONS:
            if key == section_name:
                self.registry_var.set(f"{REGISTRY_SECTIONS[key][0]}  [{key}]")
                self.current_registry = key
                self._populate_registry_list()
                return

    # ---------------- 查找 ----------------

    def find_section(self):
        keyword = self.find_section_var.get().strip()
        if not keyword:
            messagebox.showinfo("提示", "请输入要查找的节名")
            return
        if keyword != self._last_section_find_kw:
            self._last_section_find_kw = keyword
            self._last_section_find_pos = -1

        current_view = list(self.section_listbox.get(0, tk.END))
        if not current_view:
            self.filter_var.set('')
            current_view = list(self.section_listbox.get(0, tk.END))
            self._last_section_find_pos = -1
        if not current_view:
            messagebox.showinfo("提示", "节列表为空")
            return

        pos = finder.find_next_in_list(current_view, keyword,
                                       self._last_section_find_pos)
        if pos == -1:
            messagebox.showinfo("提示", f"找不到匹配 '{keyword}' 的节")
            return

        self._last_section_find_pos = pos
        self.section_listbox.selection_clear(0, tk.END)
        self.section_listbox.selection_set(pos)
        self.section_listbox.see(pos)
        self._on_section_selected()
        self.on_status(
            f"已定位到节 [{current_view[pos]}]  (第 {pos + 1}/{len(current_view)} 项)")

    def find_registry_item(self):
        keyword = self.find_reg_var.get().strip()
        if not keyword:
            messagebox.showinfo("提示", "请输入要查找的注册项")
            return
        if keyword != self._last_registry_find_kw:
            self._last_registry_find_kw = keyword
            self._last_registry_find_pos = -1

        if self.current_registry:
            if self._search_next_in_current_registry(keyword):
                return

        kw = keyword.lower()
        reg_list = [r for r in REGISTRY_SECTIONS if r in self.parser.sections]
        if not reg_list:
            messagebox.showinfo("提示", f"找不到 '{keyword}'")
            return

        start_idx = 0
        if self.current_registry in reg_list:
            start_idx = reg_list.index(self.current_registry) + 1

        n = len(reg_list)
        for offset in range(n):
            reg_section = reg_list[(start_idx + offset) % n]
            key_as_name = reg_section in REGISTRY_KEY_AS_NAME
            for key, value in self.parser.get_items(reg_section):
                name = key if key_as_name else (value if value else key)
                if kw in name.lower():
                    self.select_registry(reg_section)
                    self._last_registry_find_pos = -1
                    if self._search_next_in_current_registry(keyword):
                        self.on_status(f"已在 [{reg_section}] 中找到 '{name}'")
                    return

        messagebox.showinfo("提示", f"所有注册表中都找不到 '{keyword}'")

    def _search_next_in_current_registry(self, keyword):
        if not self.current_registry:
            return False
        key_as_name = self.current_registry in REGISTRY_KEY_AS_NAME
        pos = finder.find_next_registry_item(
            self.displayed_registry_items, keyword,
            self._last_registry_find_pos, key_as_name)
        if pos == -1:
            return False
        self._last_registry_find_pos = pos
        self.registry_listbox.selection_clear(0, tk.END)
        self.registry_listbox.selection_set(pos)
        self.registry_listbox.see(pos)
        self._on_registry_item_selected()
        return True

    def jump_to_section(self, target):
        all_sections = self.parser.get_sections()
        if target not in all_sections:
            messagebox.showinfo("提示", f"在节列表中找不到 [{target}]")
            return
        current_view = list(self.section_listbox.get(0, tk.END))
        if target not in current_view:
            self.filter_var.set('')
            current_view = list(self.section_listbox.get(0, tk.END))
        try:
            pos = current_view.index(target)
        except ValueError:
            messagebox.showinfo("提示", f"节 [{target}] 不在当前显示列表中")
            return
        self.section_listbox.selection_clear(0, tk.END)
        self.section_listbox.selection_set(pos)
        self.section_listbox.see(pos)
        self._on_section_selected()

    # ---------------- 外部数据变化回调 ----------------

    def refresh_registry_list_if_showing(self, section_name):
        """如果当前显示的注册表就是 section_name，刷新列表。"""
        if self.current_registry == section_name:
            self._populate_registry_list()

    def _on_section_right_click(self, event):
        idx = self.section_listbox.nearest(event.y)
        if 0 <= idx < self.section_listbox.size():
            self.section_listbox.selection_clear(0, tk.END)
            self.section_listbox.selection_set(idx)
        self.section_menu.tk_popup(event.x_root, event.y_root)

    def _ctx_add_section(self):
        if getattr(self, 'project_mode', False):
            messagebox.showinfo("提示", "项目模式下禁止添加节")
            return
        name = simpledialog.askstring("添加节", "请输入新节名（不含方括号）：", parent=self.frame)
        if not name:
            return
        name = name.strip().strip("[]")
        if not name:
            return
        if name in self.parser.sections:
            messagebox.showinfo("提示", f"节 [{name}] 已存在")
            return

        # 插在当前选中节之后（如果没有选中，就追加到末尾）
        sel = self.section_listbox.curselection()
        after = self.section_listbox.get(sel[0]) if sel else None
        ok = self.parser.add_section(name, after_section=after)
        if not ok:
            messagebox.showerror("错误", "添加节失败")
            return
        self.refresh_all()
        # 选中新节
        self.jump_to_section(name)
        self.on_status(f"已添加节 [{name}]")

    def _ctx_del_section(self):
        if getattr(self, 'project_mode', False):
            messagebox.showinfo("提示", "项目模式下禁止删除节")
            return
        sel = self.section_listbox.curselection()
        if not sel:
            messagebox.showinfo("提示", "请先选择一个节")
            return
        name = self.section_listbox.get(sel[0])
        if not messagebox.askyesno("确认", f"确定要删除整个节 [{name}] 吗？\n"
                                            f"该节下的所有键值、注释将一并删除。"):
            return
        ok = self.parser.del_section(name)
        if not ok:
            messagebox.showerror("错误", f"删除节 [{name}] 失败")
            return
        self.refresh_all()
        self.refresh_registry_all()
        # 通知 detail_view 清空
        self.on_section_selected("")   # 或让它显示"未选中节"
        self.on_status(f"已删除节 [{name}]")

    def _ctx_set_sort(self, mode):
        self.section_sort_var.set(mode)
        self._on_sort_changed()

    def _ctx_rename_section(self):
        if getattr(self, 'project_mode', False):
            messagebox.showinfo("提示", "项目模式下禁止重命名节")
            return
        sel = self.section_listbox.curselection()
        if not sel:
            messagebox.showinfo("提示", "请先选择一个节")
            return
        old = self.section_listbox.get(sel[0])
        new = simpledialog.askstring(
            "重命名节", f"把 [{old}] 重命名为：",
            initialvalue=old, parent=self.frame)
        if not new:
            return
        new = new.strip().strip("[]")
        if not new or new == old:
            return
        if new in self.parser.sections:
            messagebox.showinfo("提示", f"节 [{new}] 已存在")
            return
        if not self.parser.rename_section(old, new):
            messagebox.showerror("错误", "重命名失败")
            return
        self.refresh_all()
        self.jump_to_section(new)
        self.on_status(f"已把 [{old}] 重命名为 [{new}]")


    def _ctx_copy_section(self):
        if getattr(self, 'project_mode', False):
            messagebox.showinfo("提示", "项目模式下禁止复制节")
            return
        sel = self.section_listbox.curselection()
        if not sel:
            messagebox.showinfo("提示", "请先选择一个节")
            return
        name = self.section_listbox.get(sel[0])
        self._clipboard_section = name
        self.on_status(f"已复制节 [{name}]（粘贴时新节名为 [{name}-c]）")


    def _ctx_paste_section(self):
        if getattr(self, 'project_mode', False):
            messagebox.showinfo("提示", "项目模式下禁止粘贴节")
            return
        if not self._clipboard_section:
            messagebox.showinfo("提示", "剪贴板里没有已复制的节")
            return
        src = self._clipboard_section
        if src not in self.parser.sections:
            messagebox.showinfo("提示", f"原节 [{src}] 已不存在，无法粘贴")
            self._clipboard_section = None
            return
        new_name = self.parser.copy_section(src)
        if not new_name:
            messagebox.showerror("错误", "粘贴失败")
            return
        self.refresh_all()
        self.refresh_registry_all()
        self.jump_to_section(new_name)
        self.on_status(f"已粘贴为 [{new_name}]")
    
    def refresh_registry_all(self):
        """刷新下拉框和当前注册表列表（不重建节列表）。"""
        self._refresh_registry_dropdown()
        self._populate_registry_list()

    def set_project_mode(self, enabled):
        """设置项目模式，禁用节修改和添加节。"""
        self.project_mode = enabled
        # 禁用右键菜单中的添加、重命名、删除节选项
        if enabled:
            self.section_menu.entryconfig("添加节...", state=tk.DISABLED)
            self.section_menu.entryconfig("重命名节...", state=tk.DISABLED)
            self.section_menu.entryconfig("删除整节", state=tk.DISABLED)
            self.section_menu.entryconfig("复制节", state=tk.DISABLED)
            self.section_menu.entryconfig("粘贴节（-c）", state=tk.DISABLED)
        else:
            self.section_menu.entryconfig("添加节...", state=tk.NORMAL)
            self.section_menu.entryconfig("重命名节...", state=tk.NORMAL)
            self.section_menu.entryconfig("删除整节", state=tk.NORMAL)
            self.section_menu.entryconfig("复制节", state=tk.NORMAL)
            self.section_menu.entryconfig("粘贴节（-c）", state=tk.NORMAL)
