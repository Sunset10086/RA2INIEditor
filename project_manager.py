# -*- coding: utf-8 -*-
"""项目管理器：处理 .iniproject 文件的创建、读取、合并与保存。

职责：
- 新建项目：在指定目录创建 .iniproject 文件，记录项目名、文件列表、最后编辑时间。
- 读取项目：解析 .iniproject 文件，加载所有关联的 INI 文件，并合并同名节的键值对。
- 保存项目：将内存中修改过的键值对写回对应的 INI 文件。
- 提供项目状态信息（已有文件、缺失文件等）。
"""

import os
import json
import time
from datetime import datetime

from parsers.ini_parser import IniParser


class ProjectManager:
    """管理 RA2 INI 项目。"""

    PROJECT_FILE_TEMPLATES = [
        "rulesx.ini", "artx.ini", "aix.ini", "missionx.ini",
        "battlex.ini", "mapselx.ini", "evax.ini", "soundx.ini",
        "themex.ini", "uix.ini", "mpmodesx.ini", "missionx.pkt"
    ]

    def __init__(self):
        self.project_path = None
        self.project_name = None
        self.project_dir = None
        self.files = {}
        self.include_files = {}
        self.helper_files = []
        self.missing_files = []
        self.last_edit_time = None
        self.parsers = {}
        self.merged_sections = {}
        self.section_order = []
        self.is_project_mode = False

    # ---------------- 通用工具 ----------------

    def _read_includes(self, parser):
        """从解析器里读取 [#include] 节，返回子文件名列表。"""
        results = []
        for section in parser.get_sections():
            if section.strip().lower() == "#include":
                for key, value in parser.get_items(section):
                    value = value.strip()
                    if value:
                        results.append(value)
        return results

    # ---------------- 新建项目 ----------------

    def create_project(self, project_dir, project_name, rules_filename):
        if not project_name or not rules_filename:
            return False, "项目名和 rules 文件名不能为空"

        os.makedirs(project_dir, exist_ok=True)
        project_file = os.path.join(project_dir, f"{project_name}.iniproject")
        if os.path.exists(project_file):
            return False, f"项目文件 {project_file} 已存在"

        # 从 rules_filename 推导后缀
        # 例：rulesmd.ini -> "md"；rulesmo.ini -> "mo"；rules.ini -> ""
        rules_base = os.path.splitext(rules_filename)[0]   # rulesmd
        rules_lower = rules_base.lower()
        if rules_lower.startswith("rules"):
            suffix = rules_lower[len("rules"):]            # "md" / "mo" / ""
        else:
            suffix = ""                                    # 非标准命名，按无后缀处理

        project_data = {
            "project_name": project_name,
            "rules_filename": rules_filename,
            "files": {},
            "include_files": {},
            "helper_files": [],
            "missing_files": [],
            "last_edit_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # 按后缀匹配目录中的文件
        # 每个模板的"键"（去掉 x 和后缀的部分）：
        # 匹配规则：文件名的"键+后缀+.ini"（或.pkt）完全相等。
        templates = [
            ("art",      ".ini"),
            ("ai",       ".ini"),
            ("mission",  ".ini"),
            ("battle",   ".ini"),
            ("mapsel",   ".ini"),
            ("eva",      ".ini"),
            ("sound",    ".ini"),
            ("theme",    ".ini"),
            ("ui",       ".ini"),
            ("mpmodes",  ".ini"),
            ("mission",  ".pkt"),
        ]

        # rules 文件由用户指定
        rules_path = os.path.join(project_dir, rules_filename)
        if os.path.exists(rules_path):
            project_data["files"][rules_filename] = rules_path
        else:
            project_data["missing_files"].append(rules_filename)

        # 其他文件：按"键+后缀+扩展名"精确匹配
        for prefix, ext in templates:
            expected = f"{prefix}{suffix}{ext}"
            for filename in os.listdir(project_dir):
                if filename.lower() == expected.lower():
                    project_data["files"][filename] = os.path.join(project_dir, filename)
                    break
            else:
                # 没找到
                project_data["missing_files"].append(expected)

        try:
            with open(project_file, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            return False, f"写入项目文件失败: {e}"

        self.load_project(project_file)
        return True, f"项目 {project_name} 创建成功"

    # ---------------- 读取项目 ----------------

    def load_project(self, project_file):
        if not os.path.isfile(project_file):
            return False, f"项目文件不存在: {project_file}"

        try:
            with open(project_file, 'r', encoding='utf-8') as f:
                project_data = json.load(f)
        except Exception as e:
            return False, f"读取项目文件失败: {e}"

        self.project_path = project_file
        self.project_name = project_data.get("project_name", "未命名项目")
        self.project_dir = os.path.dirname(project_file)
        self.files = project_data.get("files", {})
        self.include_files = project_data.get("include_files", {})
        self.helper_files = project_data.get("helper_files", [])
        self.missing_files = project_data.get("missing_files", [])
        self.last_edit_time = project_data.get("last_edit_time", "未知")

        self.parsers = {}
        for filename, filepath in self.files.items():
            if not os.path.isfile(filepath):
                continue
            parser = IniParser()
            try:
                parser.parse_file(filepath)
            except Exception as e:
                print(f"加载 {filename} 失败: {e}")
                continue
            self.parsers[filename] = parser

            includes = self._read_includes(parser)
            self.include_files[filename] = includes
            for sub in includes:
                sub_path = os.path.join(self.project_dir, sub)
                if not os.path.isfile(sub_path):
                    if sub not in self.missing_files:
                        self.missing_files.append(sub)
                    continue
                if sub in self.parsers:
                    continue
                sub_parser = IniParser()
                try:
                    sub_parser.parse_file(sub_path)
                    self.parsers[sub] = sub_parser
                except Exception as e:
                    print(f"加载 include 文件 {sub} 失败: {e}")

        self._merge_sections()
        self.is_project_mode = True
        return True, f"项目 {self.project_name} 加载成功"

    # ---------------- 合并 ----------------

    def _merge_sections(self):
        self.merged_sections = {}
        self.section_order = []

        priority_order = [
            "rulesx.ini", "artx.ini", "aix.ini", "missionx.ini",
            "battlex.ini", "mapselx.ini", "evax.ini", "soundx.ini",
            "themex.ini", "uix.ini", "mpmodesx.ini", "missionx.pkt"
        ]

        ordered_files = []
        for template in priority_order:
            base, ext = os.path.splitext(template)
            if base.endswith('x'):
                base = base[:-1]
            for filename in self.files:
                if filename.lower().startswith(base.lower()) and filename.lower().endswith(ext.lower()):
                    if filename not in ordered_files:
                        ordered_files.append(filename)

        final_order = []
        for main_file in ordered_files:
            for sub in self.include_files.get(main_file, []):
                if sub in self.parsers and sub not in final_order:
                    final_order.append(sub)
            if main_file not in final_order:
                final_order.append(main_file)

        for filename in final_order:
            if filename not in self.parsers:
                continue
            parser = self.parsers[filename]
            for section in parser.get_sections():
                if section.strip().lower() == "#include":
                    continue
                if section not in self.merged_sections:
                    self.merged_sections[section] = []
                    self.section_order.append(section)
                existing_keys = {k for k, v, src in self.merged_sections[section]}
                for key, value in parser.get_items(section):
                    if key not in existing_keys:
                        self.merged_sections[section].append((key, value, filename))
                        existing_keys.add(key)

    # ---------------- 保存 ----------------

    def save_project(self):
        if not self.is_project_mode:
            return False, "当前不在项目模式"

        for filename, parser in self.parsers.items():
            filepath = self.files.get(filename) or os.path.join(self.project_dir, filename)
            if filepath and os.path.isfile(filepath):
                try:
                    parser.save_file(filepath)
                except Exception as e:
                    return False, f"保存 {filename} 失败: {e}"

        self.last_edit_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._update_project_file()
        return True, "项目保存成功"

    def _update_project_file(self):
        if not self.project_path:
            return
        try:
            with open(self.project_path, 'r', encoding='utf-8') as f:
                project_data = json.load(f)
            project_data["last_edit_time"] = self.last_edit_time
            project_data["files"] = self.files
            project_data["include_files"] = self.include_files
            project_data["helper_files"] = self.helper_files
            project_data["missing_files"] = self.missing_files
            with open(self.project_path, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"更新项目文件失败: {e}")

    # ---------------- 增删文件 ----------------

    def add_project_file(self, filepath):
        if not self.is_project_mode:
            return False, "当前不在项目模式"
        if not os.path.isfile(filepath):
            return False, f"文件不存在: {filepath}"
        filename = os.path.basename(filepath)
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ('.ini', '.mpr', '.yrm', '.map', '.pkt'):
            return False, f"不支持的文件类型: {ext}"
        if filename in self.files:
            return False, f"项目中已存在同名文件: {filename}"

        parser = IniParser()
        try:
            parser.parse_file(filepath)
        except Exception as e:
            return False, f"解析文件失败: {e}"

        self.files[filename] = filepath
        self.parsers[filename] = parser

        includes = self._read_includes(parser)
        self.include_files[filename] = includes
        for sub in includes:
            sub_path = os.path.join(self.project_dir, sub)
            if not os.path.isfile(sub_path):
                if sub not in self.missing_files:
                    self.missing_files.append(sub)
                continue
            if sub in self.parsers:
                continue
            sub_parser = IniParser()
            try:
                sub_parser.parse_file(sub_path)
                self.parsers[sub] = sub_parser
            except Exception:
                pass

        self._merge_sections()
        return True, f"已添加文件: {filename}"

    def remove_project_file(self, filename):
        if not self.is_project_mode:
            return False, "当前不在项目模式"
        if filename not in self.files:
            return False, f"项目中没有该文件: {filename}"

        includes = self.include_files.pop(filename, [])
        self.files.pop(filename, None)
        self.parsers.pop(filename, None)

        all_includes = set()
        for incs in self.include_files.values():
            all_includes.update(incs)
        for sub in includes:
            if sub in all_includes:
                continue
            self.parsers.pop(sub, None)
            if sub in self.missing_files:
                self.missing_files.remove(sub)

        self._merge_sections()
        return True, f"已移除文件: {filename}"

    def set_helper_files(self, filepaths):
        """存相对路径（相对项目目录）以支持项目搬迁。"""
        rels = []
        for fp in filepaths:
            try:
                rel = os.path.relpath(fp, self.project_dir)
            except ValueError:
                rel = fp  # 跨盘符，只能存绝对
            rels.append(rel)
        self.helper_files = rels

    # ---------------- 状态 ----------------

    def get_project_status(self):
        if not self.is_project_mode:
            return "当前不在项目模式"

        lines = []
        lines.append(f"项目名: {self.project_name}")
        lines.append(f"项目文件: {self.project_path}")
        lines.append(f"项目目录: {self.project_dir}")
        lines.append(f"最后编辑时间: {self.last_edit_time}")
        lines.append("")
        lines.append("已有文件:")
        for filename in self.files:
            lines.append(f"  - {filename}")
            for sub in self.include_files.get(filename, []):
                if sub in self.parsers:
                    lines.append(f"      [#include] {sub}")
                else:
                    lines.append(f"      [#include] {sub} （缺失）")
        lines.append("")
        lines.append("帮助文件:")
        if self.helper_files:
            for hf in self.helper_files:
                lines.append(f"  - {os.path.basename(hf)}")
        else:
            lines.append("  （无）")
        lines.append("")
        lines.append("缺失文件:")
        if self.missing_files:
            for f in self.missing_files:
                lines.append(f"  - {f}")
        else:
            lines.append("  （无）")
        lines.append("")
        lines.append(f"合并后节数量: {len(self.section_order)}")
        return "\n".join(lines)

    # ---------------- 辅助 ----------------

    def get_merged_items(self, section_name):
        return self.merged_sections.get(section_name, [])

    def get_merged_sections(self):
        return self.section_order

    def update_item_by_index(self, section_name, index, new_key, new_value):
        items = self.merged_sections.get(section_name, [])
        if not (0 <= index < len(items)):
            return False
        old_key, old_value, filename = items[index]
        items[index] = (new_key, new_value, filename)
        if filename in self.parsers:
            parser = self.parsers[filename]
            for idx, (pk, pv) in enumerate(parser.get_items(section_name)):
                if pk == old_key:
                    parser.update_item(section_name, idx, new_key, new_value)
                    return True
        return False

    def del_item_by_index(self, section_name, index):
        items = self.merged_sections.get(section_name, [])
        if not (0 <= index < len(items)):
            return False
        key, value, filename = items[index]
        del items[index]
        if filename in self.parsers:
            parser = self.parsers[filename]
            for idx, (pk, pv) in enumerate(parser.get_items(section_name)):
                if pk == key and pv == value:
                    parser.del_item(section_name, idx)
                    break
        return True

    def add_item_to_section(self, section_name, key, value):
        target_filename = None
        items = self.merged_sections.get(section_name, [])
        if items:
            target_filename = items[0][2]
        if not target_filename:
            for filename, parser in self.parsers.items():
                if section_name in parser.sections:
                    target_filename = filename
                    break
        if not target_filename:
            for filename in self.parsers:
                if filename.lower().startswith("rules"):
                    target_filename = filename
                    break
        if not target_filename or target_filename not in self.parsers:
            return False

        parser = self.parsers[target_filename]
        if section_name not in parser.sections:
            return False

        parser.add_item(section_name, key, value)
        if section_name not in self.merged_sections:
            self.merged_sections[section_name] = []
            self.section_order.append(section_name)
        self.merged_sections[section_name].append((key, value, target_filename))
        return True

class ProjectParser:
    """项目模式的虚拟解析器：对外接口与 IniParser 一致，
    内部使用 ProjectManager 的合并数据。
    
    这样可以无缝替换主窗口的 self.parser，UI 层无需修改。
    """

    def __init__(self, project_manager):
        self.pm = project_manager
        self.sections = {}          # {节名: [(key, value), ...]}，注意没有来源文件名
        self.section_order = []
        self._rebuild()

    def _rebuild(self):
        """根据合并数据重建 sections 和 section_order。"""
        self.sections = {}
        self.section_order = list(self.pm.get_merged_sections())
        for sec in self.section_order:
            items = self.pm.get_merged_items(sec)
            # 去掉来源文件名，变成 (key, value) 二元组
            self.sections[sec] = [(k, v) for k, v, _ in items]

    # ---- 与 IniParser 一致的接口 ----

    def get_sections(self):
        return self.section_order

    def get_items(self, section_name):
        return self.sections.get(section_name, [])

    def update_item(self, section_name, index, key, value):
        """修改某一项。同时更新 ProjectManager 的原始数据。"""
        if section_name not in self.sections:
            return False
        if not (0 <= index < len(self.sections[section_name])):
            return False
        # 更新本地
        self.sections[section_name][index] = (key, value)
        # 更新 ProjectManager（会同步到具体的 IniParser）
        self.pm.update_item_by_index(section_name, index, key, value)
        return True

    def add_item(self, section_name, key, value):
        """项目模式下禁止添加键，这里只做一个空实现，防止调用出错。"""
        return False

    def add_section(self, name, after_section=None, before_section=None):
        """项目模式下禁止添加节。"""
        return False

    def del_section(self, name):
        """项目模式下禁止删除节。"""
        return False

    def rename_section(self, old_name, new_name):
        """项目模式下禁止重命名节。"""
        return False

    def copy_section(self, src_name):
        """项目模式下禁止复制节。"""
        return None

    def del_item(self, section, index):
        """项目模式下允许删除键，但需要同步到具体文件。"""
        if section not in self.sections:
            return False
        if not (0 <= index < len(self.sections[section])):
            return False
        # 先通知 ProjectManager 删除
        ok = self.pm.del_item_by_index(section, index)
        if not ok:
            return False
        # 更新本地
        del self.sections[section][index]
        return True

    def save_file(self, filepath):
        """项目模式的保存由 ProjectManager 负责，这里不做任何事。"""
        return self.pm.save_project()[0]


        # 向具体 parser 添加
        parser.add_item(section_name, key, value)

        # 同步合并数据
        if section_name not in self.merged_sections:
            self.merged_sections[section_name] = []
            self.section_order.append(section_name)
        self.merged_sections[section_name].append((key, value, target_filename))
        return True

    def add_item_for_unit_editor(self, section_name, key, value):
        """仅由单位编辑器调用，向指定节添加键。"""
        if section_name not in self.sections:
            self.sections[section_name] = []
        self.sections[section_name].append((key, value))
        return self.pm.add_item_to_section(section_name, key, value)


    

            
            
