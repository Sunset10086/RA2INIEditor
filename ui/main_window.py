"""主窗口：菜单、文件操作、编辑转发、字体调整。

本文件只负责：
- 创建解析器 / 说明对象
- 组装左侧 SectionsView 和右侧 DetailView
- 菜单、文件操作、字体
- 把 DetailView 的编辑结果通知给 SectionsView 刷新

界面控件全部由 SectionsView 和 DetailView 构建。
"""
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from autosave import AutosaveManager
from utils import strip_ini_comments

from config import (
    UI_FONT_FAMILY, UI_FONT_SIZE,
    LIST_FONT_FAMILY, LIST_FONT_SIZE,
    DESC_FONT_FAMILY, DESC_FONT_SIZE,
    WINDOW_WIDTH, WINDOW_HEIGHT, ROW_HEIGHT,
    REGISTRY_SECTIONS,
    EXPLANATION_FILE, SECTIONS_FILE, GENERAL_FILE, WEAPONS_FILE,
    OTHERS_FILE, ARTS_FILE, AI_FILE, ARES_FILE,
)
from parsers.ini_parser import IniParser
from parsers.key_explanation import KeyExplanation
from parsers.section_name_map import SectionNameMap
from ui.sections_view import SectionsView
from ui.detail_view import DetailView
from project_manager import ProjectManager


class IniViewerApp:
    """INI 文件查看器主程序。"""

    def __init__(self, root):
        self.root = root
        self.root.title("RA2 Rules.INI 编辑器")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self._set_window_icon()

        self.parser = IniParser()
        self.current_file = None

        self.explanation = KeyExplanation()
        self.section_names = SectionNameMap()
        self._try_load_explanation_files()
        self.project_manager = ProjectManager()

        self._build_menu()
        self._build_ui()
        self._apply_fonts()

        # 自动保存
        self.autosave = AutosaveManager(
            root=self.root,
            get_filepath=lambda: self.current_file,
            save_func=lambda path: self.parser.save_file(path),
            on_status=self._set_status,
        )
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        #self.root.after(200, self._show_load_report)

    # ---------------- 说明文件加载 ----------------

    def _try_load_explanation_files(self):
        import sys

        # 1) 打包后：exe 所在目录
        if getattr(sys, "frozen", False):
            exe_dir = os.path.dirname(sys.executable)
        else:
            exe_dir = os.path.dirname(os.path.abspath(__file__))

        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            root_dir = os.path.dirname(script_dir)
        except NameError:
            script_dir = os.getcwd()
            root_dir = script_dir

        search_dirs = [
            os.path.join(exe_dir, "explanation"),   # ← 新增：exe 同目录/explanation
            exe_dir,                                # ← 新增：exe 同目录
            os.path.join(root_dir, "explanation"),
            script_dir,
            root_dir,
            os.getcwd(),
        ]

        def find(name):
            for base in search_dirs:
                cand = os.path.join(base, name)
                if os.path.isfile(cand):
                    return cand
            return None

        results = []   # [(类型, 文件名, 是否加载成功, 条目数, 路径)]

        # 1. rules_explanation.txt
        p = find(EXPLANATION_FILE)
        if p and self.explanation.load(p):
            results.append(("通用键说明", EXPLANATION_FILE, True,
                            len(self.explanation.descriptions), p))
        else:
            results.append(("通用键说明", EXPLANATION_FILE, False, 0, None))

        # 2. general_explanation.txt
        p = find(GENERAL_FILE)
        if p and self.explanation.load_general(p):
            n = getattr(self.explanation, "_last_general_count", 0)
            results.append(("全局补充说明", GENERAL_FILE, True, n, p))
        else:
            results.append(("全局补充说明", GENERAL_FILE, False, 0, None))

        # 3. weapons_explanation.txt
        p = find(WEAPONS_FILE)
        if p and self.explanation.load_weapons(p):
            w = len(self.explanation.weapon_descs)
            a = len(self.explanation.warhead_descs)
            pr = len(self.explanation.projectile_descs)
            results.append(("武器/弹头/抛射体说明", WEAPONS_FILE, True,
                            (w, a, pr), p))
        else:
            results.append(("武器/弹头/抛射体说明", WEAPONS_FILE, False, 0, None))

        # 4. others_expanation.txt（粒子/地形/地图/声音的混合说明）
        p = find(OTHERS_FILE)
        if p and self.explanation.load_others(p):
            n = len(self.explanation.others_descs)
            results.append(("其它键说明", OTHERS_FILE, True, n, p))
        else:
            results.append(("其它键说明", OTHERS_FILE, False, 0, None))
    
        # 5. sections_explanation.txt
        p = find(SECTIONS_FILE)
        if p and self.section_names.load(p):
            results.append(("节中文名", SECTIONS_FILE, True,
                            len(self.section_names.names), p))
        else:
            results.append(("节中文名", SECTIONS_FILE, False, 0, None))

        # 6. arts_explanation.txt
        p = find(ARTS_FILE)
        if p and self.explanation.load_arts(p):
            n = len(self.explanation.arts_descs)
            results.append(("图像键说明", ARTS_FILE, True, n, p))
        else:
            results.append(("图像键说明", ARTS_FILE, False, 0, None))

        # 7. ai_explanation.txt
        p = find(AI_FILE)
        if p and self.explanation.load_ai(p):
            n = len(self.explanation.ai_descs)
            results.append(("AI 键说明", AI_FILE, True, n, p))
        else:
            results.append(("AI 键说明", AI_FILE, False, 0, None))
            
        # 8. ares_explanation.txt
        p = find(ARES_FILE)
        if p and self.explanation.load_ares(p):
            n = len(self.explanation.ares_descs)
            results.append(("Ares 扩展说明", ARES_FILE, True, n, p))
        else:
            results.append(("Ares 扩展说明", ARES_FILE, False, 0, None))

        # 保存下来，供菜单里再次查看
        self._load_results = results
        return results

    # ---------------- 菜单 ----------------

    def _build_menu(self):
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="打开...", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="保存", command=self.save_file, accelerator="Ctrl+S")
        file_menu.add_command(label="另存为...", command=self.save_file_as)
        file_menu.add_separator()
        file_menu.add_command(label="重新加载", command=self.reload_file)
        file_menu.add_command(label="打开保存副本文件夹",
                      command=lambda: self.autosave.open_folder())
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        menubar.add_cascade(label="文件", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="添加键", command=self.add_key, accelerator="Ctrl+N")
        edit_menu.add_command(label="修改选中项", command=self.edit_selected)
        edit_menu.add_separator()
        edit_menu.add_command(label="删除选中项", command=self.delete_selected, accelerator="Delete")
        menubar.add_cascade(label="编辑", menu=edit_menu)

        project_menu = tk.Menu(menubar, tearoff=0)
        project_menu.add_command(label="新建项目...", command=self.new_project)
        project_menu.add_command(label="打开项目...", command=self.open_project)
        project_menu.add_command(label="保存项目", command=self.save_project)
        project_menu.add_separator()
        project_menu.add_command(label="添加项目文件...", command=self.add_project_file)
        project_menu.add_command(label="移除项目文件...", command=self.remove_project_file)
        project_menu.add_command(label="加载帮助文件...", command=self.load_helper_files)
        project_menu.add_separator()
        project_menu.add_command(label="单位属性编辑器...", command=self.open_unit_editor)
        project_menu.add_command(label="国家与所属色编辑器...", command=self.open_country_editor)
        project_menu.add_separator()
        project_menu.add_command(label="项目属性...", command=self.show_project_properties)
        menubar.add_cascade(label="项目", menu=project_menu)

        self.root.config(menu=menubar)

        find_menu = tk.Menu(menubar, tearoff=0)
        find_menu.add_command(label="查找节...", command=self.find_section, accelerator="Ctrl+F")
        find_menu.add_command(label="查找注册项...", command=self.find_registry_item, accelerator="Ctrl+R")
        find_menu.add_command(label="查找键（当前节内）...",
                      command=self.find_key_in_section,
                      accelerator="Ctrl+K")
        menubar.add_cascade(label="查找", menu=find_menu)
        
        settings_menu = tk.Menu(menubar, tearoff=0)
        settings_menu.add_command(label="增大字号",
                                  command=lambda: self.change_font_size(+1))
        settings_menu.add_command(label="减小字号",
                                  command=lambda: self.change_font_size(-1))
        settings_menu.add_command(label="重置字号",
                                  command=lambda: self.change_font_size(0, reset=True))
        menubar.add_cascade(label="设置", menu=settings_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="导入键说明文件...", command=self.import_explanation_files)
        help_menu.add_command(label="导入节中文名文件...", command=self.import_sections_files)
        help_menu.add_command(label="关于", command=self.show_about)
        help_menu.add_command(label="查看说明文件加载状态...", command=self._show_load_report)
        help_menu.add_separator()
        menubar.add_cascade(label="帮助", menu=help_menu)

        self.root.config(menu=menubar)

        self.root.bind('<Control-o>', lambda e: self.open_file())
        self.root.bind('<Control-s>', lambda e: self.save_file())
        self.root.bind('<Control-n>', lambda e: self.add_key())
        self.root.bind('<Delete>', lambda e: self.delete_selected())
        self.root.bind('<Control-f>', lambda e: self.find_section())
        self.root.bind('<Control-r>', lambda e: self.find_registry_item())
        self.root.bind('<Control-plus>',  lambda e: self.change_font_size(+1))
        self.root.bind('<Control-minus>', lambda e: self.change_font_size(-1))
        self.root.bind('<Control-0>',     lambda e: self.change_font_size(0, reset=True))
        self.root.bind('<Control-k>', lambda e: self.find_key_in_section())

    # ---------------- 界面构建 ----------------

    def _build_ui(self):
        # Treeview 初始样式
        style = ttk.Style()
        style.configure("Treeview",
                        font=(UI_FONT_FAMILY, UI_FONT_SIZE),
                        rowheight=ROW_HEIGHT)
        style.configure("Treeview.Heading",
                        font=(UI_FONT_FAMILY, UI_FONT_SIZE, "bold"))

        # ---- 顶部第一行工具栏 ----
        toolbar = ttk.Frame(self.root, padding=5)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        ttk.Button(toolbar, text="打开INI文件", command=self.open_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="保存", command=self.save_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="重新加载", command=self.reload_file).pack(side=tk.LEFT, padx=5)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        ttk.Button(toolbar, text="添加键", command=self.add_key).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="修改选中项", command=self.edit_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="删除选中项", command=self.delete_selected).pack(side=tk.LEFT, padx=5)

        self.file_label = ttk.Label(toolbar, text="未打开文件")
        self.file_label.pack(side=tk.LEFT, padx=20)

        self.type_label = ttk.Label(toolbar, text="类型: 未识别",
                                    font=(UI_FONT_FAMILY, UI_FONT_SIZE, "bold"))
        self.type_label.pack(side=tk.LEFT, padx=10)

        # ---- 主体区域 ----
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        left_container = ttk.Frame(main_paned)
        main_paned.add(left_container, weight=1)

        right_container = ttk.Frame(main_paned)
        main_paned.add(right_container, weight=2)

        self.root.update_idletasks()


        # ---- 左侧面板 ----
        self.sections_view = SectionsView(
            parent=left_container,
            parser=self.parser,
            section_names=self.section_names,
            on_section_selected=self._on_section_selected,
            on_jump_to_section=self._jump_to_section,
            on_status=self._set_status,
        )

        # ---- 右侧面板 ----
        self.detail_view = DetailView(
            parent=right_container,
            parser=self.parser,
            explanation=self.explanation,
            section_names=self.section_names,
            classifier=self.sections_view.get_classifier(),
            get_filter_text=self.sections_view.get_filter_text,
            on_status=self._set_status,
        )
        self.root.after(200, self.detail_view.set_initial_sashpos)

        # ---- 状态栏 ----
        self.status_label = ttk.Label(self.root, text="就绪", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

        # 初始状态提示
        msgs = []
        if self.explanation.loaded or self.explanation.weapons_loaded:
            msgs.append(f"键说明 {len(self.explanation.descriptions)} 条")
        if self.section_names.loaded:
            msgs.append(f"节中文名 {len(self.section_names.names)} 条")
        if msgs:
            self.status_label.config(text="已加载: " + "，".join(msgs))
        else:
            self.status_label.config(text="未找到任何说明文件")

    # ---------------- 回调转发 ----------------

    def _set_status(self, text):
        self.status_label.config(text=text)

    def _on_section_selected(self, section_name):
        """SectionsView 选中节时，刷新 DetailView。"""
        self.detail_view.show_section(section_name)

    def _jump_to_section(self, target):
        """双击注册项时，由 SectionsView 跳转到对应节。"""
        self.sections_view.jump_to_section(target)

    # ---------------- 字体 ----------------

    def change_font_size(self, delta, reset=False):
        import config
        if reset:
            config.UI_FONT_SIZE = 11
            config.LIST_FONT_SIZE = 11
            config.DESC_FONT_SIZE = 11
            config.ROW_HEIGHT = 22
        else:
            config.UI_FONT_SIZE = max(8, config.UI_FONT_SIZE + delta)
            config.LIST_FONT_SIZE = max(8, config.LIST_FONT_SIZE + delta)
            config.DESC_FONT_SIZE = max(8, config.DESC_FONT_SIZE + delta)
            config.ROW_HEIGHT = max(16, config.ROW_HEIGHT + delta * 2)
        self._apply_fonts()
        self.status_label.config(text=f"字号已调整为 {config.UI_FONT_SIZE}")

    def _apply_fonts(self):
        import config
        style = ttk.Style()
        style.configure("Treeview",
                        font=(config.UI_FONT_FAMILY, config.UI_FONT_SIZE),
                        rowheight=config.ROW_HEIGHT)
        style.configure("Treeview.Heading",
                        font=(config.UI_FONT_FAMILY, config.UI_FONT_SIZE, "bold"))

        ui_font = (config.UI_FONT_FAMILY, config.UI_FONT_SIZE)
        ui_font_bold = (config.UI_FONT_FAMILY, config.UI_FONT_SIZE, "bold")
        title_font = (config.UI_FONT_FAMILY, config.UI_FONT_SIZE + 1, "bold")
        list_font = (config.LIST_FONT_FAMILY, config.LIST_FONT_SIZE)
        desc_font = (config.DESC_FONT_FAMILY, config.DESC_FONT_SIZE)

        if hasattr(self, "sections_view"):
            self.sections_view.apply_fonts(ui_font, list_font)
        if hasattr(self, "detail_view"):
            self.detail_view.apply_fonts(title_font, ui_font_bold, desc_font)

    # ---------------- 项目功能 ----------------

    def new_project(self):
        """新建项目。"""
        messagebox.showwarning(
            "警告",
            "注意！ini项目为实验性功能，请确保已经备份了所有ini相关文件！\n"
            "项目模式下节修改和添加键禁用。"
        )

        # 1. 选择项目目录
        project_dir = filedialog.askdirectory(title="选择项目根目录")
        if not project_dir:
            return

        # 2. 弹出对话框输入项目名和 rules 文件名
        from ui.dialogs import NewProjectDialog
        dialog = NewProjectDialog(self.root, title="新建项目")
        if not dialog.result:
            return
        project_name, rules_filename = dialog.result

        # 3. 创建项目
        success, message = self.project_manager.create_project(
            project_dir, project_name, rules_filename
        )
        if success:
            messagebox.showinfo("成功", message)
            self._enter_project_mode()
        else:
            messagebox.showerror("错误", message)

    def open_project(self):
        """打开项目。"""
        messagebox.showwarning(
            "警告",
            "注意！ini项目为实验性功能，请确保已经备份了所有ini相关文件！\n"
            "项目模式下节修改和添加键禁用。"
        )

        project_file = filedialog.askopenfilename(
            title="选择 .iniproject 文件",
            filetypes=[("INI 项目文件", "*.iniproject"), ("所有文件", "*.*")]
        )
        if not project_file:
            return

        success, message = self.project_manager.load_project(project_file)
        if success:
            messagebox.showinfo("成功", message)
            self._enter_project_mode()
        else:
            messagebox.showerror("错误", message)

    def _enter_project_mode(self):
        """进入项目模式，更新 UI 和禁用编辑功能。"""
        from project_manager import ProjectParser

        self.current_file = None
        self.file_label.config(text=f"项目: {self.project_manager.project_name}")
        self.type_label.config(text="类型: 项目模式", foreground="#ff6600")

        # 用 ProjectParser 替换 self.parser，让 UI 层直接读取合并后的数据
        self.parser = ProjectParser(self.project_manager)

        # 通知子视图替换 parser
        self.sections_view.parser = self.parser
        self.sections_view.classifier.parser = self.parser
        self.sections_view.classifier.invalidate()
        self.detail_view.parser = self.parser

        # ---- 关键：在刷新之前就把 _is_art_file 设好 ----
        self.detail_view._is_art_file = False

        # 禁用节修改和添加键
        self.sections_view.set_project_mode(True)
        self.detail_view.set_project_mode(True)

        # 刷新界面
        self.sections_view.refresh_all()
        self.detail_view.show_section("")

        # 禁用自动存档
        self.autosave.set_enabled(False)
        
        self.status_label.config(text=f"已进入项目模式（{self.project_manager.project_name}），节修改和添加键已禁用")

        # 加载项目的帮助文件
        helper_count = 0
        for rel in self.project_manager.helper_files:      
            if os.path.isabs(rel):
                hf = rel
            else:
                hf = os.path.join(self.project_manager.project_dir, rel)
            if os.path.isfile(hf):
                try:
                    content = self.explanation._read_file(hf)
                    content = strip_ini_comments(content)
                    self.explanation.merge_from_text(content)
                    self.section_names.merge_from_text(content)
                except Exception as e:
                    print(f"加载帮助文件 {hf} 失败: {e}")
        self.sections_view.refresh_all()
        self.detail_view.refresh_description()
        
    def save_project(self):
        """保存项目。"""
        if not self.project_manager.is_project_mode:
            messagebox.showinfo("提示", "当前不在项目模式")
            return
        success, message = self.project_manager.save_project()
        if success:
            messagebox.showinfo("成功", message)
            self.status_label.config(text=message)
        else:
            messagebox.showerror("错误", message)

    def show_project_properties(self):
        """显示项目属性。"""
        if not self.project_manager.is_project_mode:
            messagebox.showinfo("提示", "当前不在项目模式")
            return
        status = self.project_manager.get_project_status()
        messagebox.showinfo("项目属性", status, parent=self.root)

    # ---------------- 文件操作 ----------------

    def open_file(self):
        if self.project_manager.is_project_mode:
            messagebox.showinfo("提示", "项目模式下请使用“打开项目”功能")
            return
        filepath = filedialog.askopenfilename(
            title="选择INI/地图/PKT文件",
            filetypes=[
                ("所有支持的文件", "*.ini *.map *.mpr *.yrm *.pkt"),
                ("INI文件", "*.ini"),
                ("地图文件", "*.map *.mpr *.yrm"),
                ("PKT注册文件", "*.pkt"),
                ("所有文件", "*.*"),
            ]
        )
        if filepath:
            self.load_file(filepath)

    def reload_file(self):
        if self.current_file:
            self.load_file(self.current_file)
        else:
            messagebox.showinfo("提示", "没有已打开的文件")

    def save_file(self):
        if self.project_manager.is_project_mode:
            self.save_project()
            return
        if not self.current_file:
            self.save_file_as()
            return
        try:
            self.parser.save_file(self.current_file)
            self.status_label.config(text=f"已保存到 {self.current_file}")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败:\n{e}")

    def save_file_as(self):
        if not self.current_file:
            messagebox.showinfo("提示", "尚未打开任何文件")
            return
        filepath = filedialog.asksaveasfilename(
            title="另存为",
            defaultextension=".ini",
            filetypes=[("INI文件", "*.ini"), ("所有文件", "*.*")]
        )
        if filepath:
            try:
                self.parser.save_file(filepath)
                self.current_file = filepath
                self.file_label.config(text=f"文件: {filepath}")
                self.status_label.config(text=f"已保存到 {filepath}")
            except Exception as e:
                messagebox.showerror("错误", f"保存失败:\n{e}")

    def load_file(self, filepath):
        try:
            self.parser.parse_file(filepath)
            self.current_file = filepath
            self.file_label.config(text=f"文件: {filepath}")
            self.sections_view.invalidate_classifier()
            self.sections_view.refresh_all()

            # 识别文件类型
            ini_type, reason = self.parser.detect_type()
            self.current_ini_type = ini_type
            self.current_ini_type_reason = reason

            if hasattr(self, "detail_view"):
                self.detail_view._is_art_file = (ini_type == "art")

            # 更新窗口标题
            type_label = {
                "rules":   "Rules",
                "art":     "Art",
                "ai":      "AI",
                "eva":     "EVA",
                "sound":   "Sound",
                "theater": "Theater",
                "mission": "Mission",
                "ui":      "UI",
                "map":     "Map",  
                "pkt":     "Pkt",   
                "theme":   "Theme",
                "unknown": "未知",
            }.get(ini_type, "未知")

            color = {
                "rules":   "#006600",
                "art":     "#000099",
                "ai":      "#660066",
                "eva":     "#993300",
                "sound":   "#006666",
                "theater": "#0077aa",
                "mission": "#aa5500",
                "ui":      "#aa0077",
                "map":     "#228b22",   # 森林绿，区别于 rules 的 #006600
                "pkt":     "#8b008b",   # 深品红
                "theme":   "#c71585", 
                "unknown": "#888888",
            }.get(ini_type, "#888888")
            self.type_label.config(text=f"类型: {type_label}", foreground=color)

            self.status_label.config(
                text=f"已加载 {len(self.parser.get_sections())} 个节；"
                     f"识别为 {type_label}（{reason}）"
            )
            
            self.autosave.start()

            # 刷新说明区（如果当前有选中键）
            if hasattr(self, "detail_view"):
                self.detail_view.refresh_description()
            
        except Exception as e:
            messagebox.showerror("错误", f"无法加载文件:\n{e}")

    
    # ---------------- 编辑操作（转发到 DetailView） ----------------

    def add_key(self):
        if self.project_manager.is_project_mode:
            messagebox.showinfo("提示", "项目模式下禁止添加键")
            return
        ok = self.detail_view.add_key(self.root)
        if ok:
            sec = self.detail_view.get_current_section()
            self.sections_view.refresh_registry_list_if_showing(sec)
            self.status_label.config(text=f"已向 [{sec}] 添加键")

    def edit_selected(self):
        if self.project_manager.is_project_mode:
            pass
        ok = self.detail_view.edit_selected(self.root)
        if ok:
            sec = self.detail_view.get_current_section()
            self.sections_view.refresh_registry_list_if_showing(sec)
            self.status_label.config(text=f"已修改 [{sec}] 中的项")

    def delete_selected(self):
        ok = self.detail_view.delete_selected()
        if ok:
            sec = self.detail_view.get_current_section()
            self.sections_view.refresh_registry_list_if_showing(sec)
            self.status_label.config(text=f"已删除 [{sec}] 中的项")

    # ---------------- 查找（转发到 SectionsView） ----------------

    def find_section(self):
        if not self.current_file:
            messagebox.showinfo("提示", "请先打开文件")
            return
        self.sections_view.find_section()

    def find_registry_item(self):
        if not self.current_file:
            messagebox.showinfo("提示", "请先打开文件")
            return
        self.sections_view.find_registry_item()
        
    def find_key_in_section(self):
        if not self.current_file:
            messagebox.showinfo("提示", "请先打开文件")
            return
        if not self.detail_view.get_current_section():
            messagebox.showinfo("提示", "请先在左侧选择一个节")
            return
        # 把焦点交给 DetailView 的查找框
        self.detail_view.focus_find_entry()

    # ---------------- 关于 ----------------

    def show_about(self):
        e_loaded = "已加载" if self.explanation.loaded else "未加载"
        e_count = len(self.explanation.descriptions) if self.explanation.loaded else 0
        s_loaded = "已加载" if self.section_names.loaded else "未加载"
        s_count = len(self.section_names.names) if self.section_names.loaded else 0
        messagebox.showinfo(
            "关于",
            "RA2 Rules.INI 查看器\n\n"
            "支持读取、编辑、保存INI文件。\n"
            "以分号开头的行视为注释。\n"
            "双击右侧的键或值可直接修改。\n"
            "左上角可切换注册列表，双击注册项可跳转到对应节。\n"
            "顶部可查找节、查找注册项，并切换排序方式。\n"
            "选中键值对时，右下方显示键的说明。\n"
            "选中节时，标题显示该节的中文名。\n\n"
            f"键说明文件: {e_loaded}（{e_count} 条）\n"
            f"节中文名文件: {s_loaded}（{s_count} 条）"
        )
    def _show_load_report(self):
        """弹窗显示每个说明文件的加载结果。"""
        results = getattr(self, "_load_results", [])
        if not results:
            return

        lines = []
        all_ok = True
        for kind, name, ok, count, path in results:
            if ok:
                if isinstance(count, tuple):
                    cnt_str = f"武器 {count[0]} / 弹头 {count[1]} / 抛射体 {count[2]} 条"
                else:
                    cnt_str = f"{count} 条"
                lines.append(f"[OK] {kind}：{name}")
                lines.append(f"      条目数 {cnt_str}")
                lines.append(f"      路径 {path}")
            else:
                all_ok = False
                lines.append(f"[缺失] {kind}：{name}")
            lines.append("")

        title = "说明文件加载成功" if all_ok else "说明文件加载情况"
        text = "\n".join(lines).rstrip()
        messagebox.showinfo(title, text, parent=self.root)

    def import_explanation_files(self):
        """导入一个或多个键说明 txt（与其它说明文件相同读取方式）。
        导入内容覆盖同名键，仅本次程序运行期间有效。"""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            root_dir = os.path.dirname(script_dir)
        except NameError:
            root_dir = os.getcwd()
        initial_dir = os.path.join(root_dir, "explanation")
        if not os.path.isdir(initial_dir):
            initial_dir = root_dir

        filepaths = filedialog.askopenfilenames(
            title="导入键说明文件（可多选）",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
            initialdir=initial_dir,
        )
        if not filepaths:
            return

        total = 0
        loaded_files = []
        for fp in filepaths:
            try:
                content = self.explanation._read_file(fp)
                content = strip_ini_comments(content)
                n = self.explanation.merge_from_text(content)
                total += n
                loaded_files.append(os.path.basename(fp))
                # 追加到加载报告
                self._load_results.append(
                    ("导入的键说明", os.path.basename(fp), True, n, fp)
                )
            except Exception as e:
                messagebox.showerror("错误", f"无法导入 {fp}:\n{e}")
                self._load_results.append(
                    ("导入的键说明", os.path.basename(fp), False, 0, fp)
                )

        if total:
            self.status_label.config(
                text=f"已导入 {len(loaded_files)} 个键说明文件，共 {total} 条"
            )
            self.detail_view.refresh_description()

    def import_sections_files(self):
        """导入一个或多个节中文名 txt（与 sections_explanation.txt 相同读取方式）。
        导入内容覆盖同名节，仅本次程序运行期间有效。"""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            root_dir = os.path.dirname(script_dir)
        except NameError:
            root_dir = os.getcwd()
        initial_dir = os.path.join(root_dir, "explanation")
        if not os.path.isdir(initial_dir):
            initial_dir = root_dir

        filepaths = filedialog.askopenfilenames(
            title="导入节中文名文件（可多选）",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
            initialdir=initial_dir,
        )
        if not filepaths:
            return

        total = 0
        loaded_files = []
        for fp in filepaths:
            try:
                content = self.section_names._read_file(fp)
                content = strip_ini_comments(content)
                n = self.section_names.merge_from_text(content)
                total += n
                loaded_files.append(os.path.basename(fp))
                self._load_results.append(
                    ("导入的节中文名", os.path.basename(fp), True, n, fp)
                )
            except Exception as e:
                messagebox.showerror("错误", f"无法导入 {fp}:\n{e}")
                self._load_results.append(
                    ("导入的节中文名", os.path.basename(fp), False, 0, fp)
                )

        if total:
            self.status_label.config(
                text=f"已导入 {len(loaded_files)} 个节中文名文件，共 {total} 条"
            )
            cur = self.detail_view.get_current_section()
            if cur:
                self.detail_view.show_section(cur)
    def _on_close(self):
        self.autosave.cancel()
        self.root.destroy()

    def open_unit_editor(self):
        """打开单位属性编辑器（仅项目模式可用）。"""
        if not self.project_manager.is_project_mode:
            messagebox.showinfo("提示", "请先打开或新建一个项目")
            return
        from ui.unit_editor import UnitEditorDialog
        # 传入当前项目模式的 parser（即 ProjectParser）
        UnitEditorDialog(
            parent=self.root,
            parser=self.parser,
            project_manager=self.project_manager,
            section_names=self.section_names,
        )

    def open_country_editor(self):
        """打开国家与所属色编辑器（仅项目模式可用）。"""
        if not self.project_manager.is_project_mode:
            messagebox.showinfo("提示", "请先打开或新建一个项目")
            return
        from ui.country_editor import CountryEditorDialog
        CountryEditorDialog(
            parent=self.root,
            parser=self.parser,
            project_manager=self.project_manager,
            section_names=self.section_names,
        )

    def add_project_file(self):
        if not self.project_manager.is_project_mode:
            messagebox.showinfo("提示", "请先打开或新建一个项目")
            return
        filepaths = filedialog.askopenfilenames(
            title="选择要加入项目的文件",
            filetypes=[
                ("INI 及其它支持文件", "*.ini *.mpr *.yrm *.map *.pkt"),
                ("所有文件", "*.*"),
            ]
        )
        if not filepaths:
            return
        msgs = []
        for fp in filepaths:
            ok, msg = self.project_manager.add_project_file(fp)
            msgs.append(("OK" if ok else "失败") + " " + msg)
        messagebox.showinfo("结果", "\n".join(msgs), parent=self.root)
        # 刷新 UI
        self._refresh_after_project_change()

    def remove_project_file(self):
        if not self.project_manager.is_project_mode:
            messagebox.showinfo("提示", "请先打开或新建一个项目")
            return
        # 弹一个简单的选择对话框
        files = list(self.project_manager.files.keys())
        if not files:
            messagebox.showinfo("提示", "项目中没有文件")
            return
        dlg = tk.Toplevel(self.root)
        dlg.title("移除项目文件")
        dlg.geometry("360x420")
        dlg.transient(self.root)
        dlg.grab_set()

        ttk.Label(dlg, text="选择要移除的文件（可多选）").pack(pady=5)
        lb = tk.Listbox(dlg, selectmode=tk.MULTIPLE,
                        font=(LIST_FONT_FAMILY, LIST_FONT_SIZE))
        lb.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        for f in files:
            lb.insert(tk.END, f)

        def do_remove():
            sels = lb.curselection()
            if not sels:
                return
            removed = []
            for idx in reversed(sels):
                filename = files[idx]
                ok, msg = self.project_manager.remove_project_file(filename)
                removed.append(msg)
            messagebox.showinfo("完成", "\n".join(removed), parent=dlg)
            dlg.destroy()
            self._refresh_after_project_change()

        btn = ttk.Frame(dlg)
        btn.pack(fill=tk.X, pady=5)
        ttk.Button(btn, text="移除", command=do_remove).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn, text="取消", command=dlg.destroy).pack(side=tk.RIGHT)

    def load_helper_files(self):
        """加载帮助文件（txt）。

        每个文件同时尝试按"键说明"和"节中文名"两种格式解析，
        谁解析出条目就采用谁，加载后写入项目，下次打开项目自动加载。
        """
        filepaths = filedialog.askopenfilenames(
            title="选择帮助文件（可多选）",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if not filepaths:
            return

        # 项目模式下记录到项目
        if self.project_manager.is_project_mode:
            cur = list(self.project_manager.helper_files)
            for fp in filepaths:
                if fp not in cur:
                    cur.append(fp)
            self.project_manager.set_helper_files(cur)

        total_key = 0
        total_sec = 0
        for fp in filepaths:
            try:
                content = self.explanation._read_file(fp)
                content = strip_ini_comments(content)
                # 先按键说明解析
                n_key = self.explanation.merge_from_text(content)
                # 再按节中文名解析
                n_sec = self.section_names.merge_from_text(content)
                total_key += n_key
                total_sec += n_sec

                self._load_results.append(
                    ("导入的帮助文件", os.path.basename(fp), True,
                     f"键 {n_key} / 节 {n_sec}", fp)
                )
            except Exception as e:
                messagebox.showerror("错误", f"无法导入 {fp}:\n{e}")

        if total_key or total_sec:
            self.status_label.config(
                text=f"已加载 {len(filepaths)} 个帮助文件：键说明 {total_key} 条，节中文名 {total_sec} 条")
            # 同时刷新节列表和说明区
            self.sections_view.refresh_all()
            self.detail_view.refresh_description()

    def _refresh_after_project_change(self):
        """项目文件变化后，重建 ProjectParser 并刷新 UI。"""
        from project_manager import ProjectParser
        self.parser = ProjectParser(self.project_manager)
        self.sections_view.parser = self.parser
        self.sections_view.classifier.parser = self.parser
        self.sections_view.classifier.invalidate()
        self.detail_view.parser = self.parser
        self.detail_view._is_art_file = False
        self.sections_view.refresh_all()
        self.detail_view.show_section("")

    def _set_window_icon(self):
        """设置窗口图标，兼容未打包和 PyInstaller 打包后的情况。"""
        import sys

        # 候选图标文件（按优先级）
        candidates = []
        if getattr(sys, "frozen", False):
            # 打包后：exe 所在目录
            exe_dir = os.path.dirname(sys.executable)
            candidates.append(os.path.join(exe_dir, "app.ico"))
            # 若用了 --add-data 打包进去，还可以从 _MEIPASS 找
            if hasattr(sys, "_MEIPASS"):
                candidates.append(os.path.join(sys._MEIPASS, "app.ico"))
        else:
            # 未打包：脚本目录 / 项目根目录
            try:
                here = os.path.dirname(os.path.abspath(__file__))
            except NameError:
                here = os.getcwd()
            root_dir = os.path.dirname(here)
            candidates.append(os.path.join(root_dir, "app.ico"))
            candidates.append(os.path.join(here, "app.ico"))
            candidates.append(os.path.join(os.getcwd(), "app.ico"))

        for path in candidates:
            if os.path.isfile(path):
                try:
                    self.root.iconbitmap(path)
                    return
                except Exception as e:
                    print(f"设置窗口图标失败: {path}: {e}")
