"""通用对话框：键值对输入。"""
from tkinter import ttk, messagebox, simpledialog


class KeyValueDialog(simpledialog.Dialog):
    """用于输入键值对的对话框。"""

    def __init__(self, parent, title="添加键值", key="", value=""):
        self._init_key = key
        self._init_value = value
        self.result = None
        super().__init__(parent, title)

    def body(self, master):
        ttk.Label(master, text="键 (Key):").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.key_entry = ttk.Entry(master, width=40)
        self.key_entry.grid(row=0, column=1, padx=5, pady=5)
        self.key_entry.insert(0, self._init_key)

        ttk.Label(master, text="值 (Value):").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.value_entry = ttk.Entry(master, width=40)
        self.value_entry.grid(row=1, column=1, padx=5, pady=5)
        self.value_entry.insert(0, self._init_value)

        return self.key_entry

    def validate(self):
        key = self.key_entry.get().strip()
        if not key:
            messagebox.showwarning("提示", "键不能为空", parent=self)
            return False
        return True

    def apply(self):
        key = self.key_entry.get().strip()
        value = self.value_entry.get().strip()
        self.result = (key, value)

class NewProjectDialog(simpledialog.Dialog):
    """新建项目对话框：输入项目名和 rules 文件名。"""

    def __init__(self, parent, title="新建项目",
                 init_project_name="", init_rules_name="rulesmd.ini"):
        self._init_project_name = init_project_name
        self._init_rules_name = init_rules_name
        self.result = None   # (project_name, rules_filename)
        super().__init__(parent, title)

    def body(self, master):
        ttk.Label(master, text="项目名:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.name_entry = ttk.Entry(master, width=40)
        self.name_entry.grid(row=0, column=1, padx=5, pady=5)
        self.name_entry.insert(0, self._init_project_name)

        ttk.Label(master, text="rulesx.ini 文件名:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.rules_entry = ttk.Entry(master, width=40)
        self.rules_entry.grid(row=1, column=1, padx=5, pady=5)
        self.rules_entry.insert(0, self._init_rules_name)

        ttk.Label(
            master,
            text="（提示：项目名会作为 .iniproject 文件名；\n"
                 "rulesx.ini 文件名如 rulesmd.ini、rules.ini 等）",
            foreground="#666666", justify="left"
        ).grid(row=2, column=0, columnspan=2, sticky="w", padx=5, pady=(0, 5))

        return self.name_entry

    def validate(self):
        name = self.name_entry.get().strip()
        rules = self.rules_entry.get().strip()
        if not name:
            messagebox.showwarning("提示", "项目名不能为空", parent=self)
            return False
        if not rules:
            messagebox.showwarning("提示", "rules 文件名不能为空", parent=self)
            return False
        # 做一些基本的文件名合法性检查
        for ch in '\\/:*?"<>|':
            if ch in name:
                messagebox.showwarning("提示", f"项目名不能包含字符 {ch}", parent=self)
                return False
            if ch in rules:
                messagebox.showwarning("提示", f"rules 文件名不能包含字符 {ch}", parent=self)
                return False
        if not rules.lower().endswith(".ini"):
            messagebox.showwarning("提示", "rules 文件名应以 .ini 结尾", parent=self)
            return False
        return True

    def apply(self):
        self.result = (self.name_entry.get().strip(), self.rules_entry.get().strip())
