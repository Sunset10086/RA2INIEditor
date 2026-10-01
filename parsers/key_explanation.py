"""键说明解析器：支持四种说明文件格式。

- rules_explanation.txt      : Key= 后面跟多行说明
- general_explanation.txt    : Key=值 中文说明（值忽略、数字变 X）
- weapons_explanation.txt    : 按「武器代码 / 弹头代码 / 抛射体代码」三段分开
- particle_explanation.txt   : 粒子系统与粒子键说明
- arts_explanation.txt       : 图像相关键说明
"""
import os
import re

from utils import read_file_auto_encoding, strip_ini_comments


class KeyExplanation:
    """解析键说明文件，得到 {键名(小写): 说明文本} 的字典。"""

    # 段落分隔标记
    SECTION_WEAPON     = "weapon"
    SECTION_WARHEAD    = "warhead"
    SECTION_PROJECTILE = "projectile"

    def __init__(self):
        self.descriptions = {}          # rules / general 的通用说明
        # weapons_explanation 的分段说明
        self.weapon_descs     = {}
        self.warhead_descs    = {}
        self.projectile_descs = {}
        self.weapons_loaded   = False
        self.loaded = False
        self.source_path = None
        self.particles_loaded = False
        self.others_descs = {}          
        self.others_loaded = False
        self.sources = {
            "rules":     None,
            "general":   None,
            "weapons":   None,
            "particles": None,
            "others":    None,
            "arts":      None,
        }
        self.arts_descs = {}
        self.arts_loaded = False
        self.ai_descs = {}
        self.ai_loaded = False
        self.sources["ai"] = None
        self.sources["ares"] = None

    # ---------------- 通用说明 ----------------

    def load(self, filepath):
        self.descriptions = {}
        self.loaded = False
        self.source_path = filepath

        if not os.path.isfile(filepath):
            return False

        content = strip_ini_comments(self._read_file(filepath))
        self.descriptions = self._parse_unified(content)
        self.loaded = True
        self.sources["rules"] = filepath
        return True

    def load_others(self, filepath):
        """加载 others_expanation.txt（粒子/地形/地图/声音的混合说明）。"""
        if not os.path.isfile(filepath):
            return False
        content = strip_ini_comments(self._read_file(filepath))
        self.others_descs = self._parse_unified(content)
        self.others_loaded = True
        self.sources["others"] = filepath
        return True

    def get_others(self, key):
        if not key:
            return None
        return self.others_descs.get(key.lower())

    def load_arts(self, filepath):
        if not os.path.isfile(filepath):
            return False
        content = strip_ini_comments(self._read_file(filepath))
        self.arts_descs = self._parse_unified(content)
        self.arts_loaded = True
        self.sources["arts"] = filepath
        return True
    
    def load_ai(self, filepath):
        if not os.path.isfile(filepath):
            return False
        content = strip_ini_comments(self._read_file(filepath))
        self.ai_descs = self._parse_unified(content)
        self.ai_loaded = True
        self.sources["ai"] = filepath
        return True

    def _read_file(self, filepath):
        content, _ = read_file_auto_encoding(filepath)
        return content

    # ---------------- 数字替换与双引号处理 ----------------

    @staticmethod
    def _replace_numbers_for_display(text):
        """
        替换数字为 X，但：
        1. 英文双引号 "" 中的内容完全不动；
        2. 含字母或下划线的标识符 token（如 E1、4A5827、special_1）整体保留；
        3. 数字-数字 形式的区间（如 50-100、3.5-10）整体保留；
        最后去掉所有英文双引号。
        """
        if not text:
            return text

        protected = []

        def protect(m):
            protected.append(m.group(0))
            return chr(0xE000 + len(protected) - 1)

        # 1) 保护双引号内容
        text = re.sub(r'"[^"]*"', protect, text)

        # 2) 保护"数字-数字"区间（如 50-100、3.5-10、200-300-400）
        text = re.sub(r'\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)+(?![\d.])', protect, text)

        # 3) 保护"含字母或下划线的标识符 token"
        text = re.sub(
            r'(?<![A-Za-z0-9])(?=[A-Za-z0-9_=]*[A-Za-z_])[A-Za-z0-9_=]+(?![A-Za-z0-9])',
            protect, text
        )

        # 4) 替换剩余数字
        text = re.sub(r'\d+(\.\d+)?%?', 'X', text)

        # 5) 还原占位符
        text = re.sub(r'[\uE000-\uF8FF]',
                      lambda m: protected[ord(m.group(0)) - 0xE000],
                      text)

        # 6) 去掉引号
        return text.replace('"', '')

    # ---------------- 统一解析逻辑 ----------------

    def _parse_unified(self, content):
        """
        统一的解析函数。
        """
        result = {}
        lines = content.splitlines()

        current_keys = []
        current_lines = []
        pending_keys = []  # 用于处理“遇到下一个键仍未读取到中文”的情况

        # 增强键匹配：允许键名后跟 = 或 空格，或者直接跟中文
        key_pattern = re.compile(r'^([A-Za-z][A-Za-z0-9_.]*)\s*=\s*(.*)$')
        # 模块分隔符：以多个 - 或 = 开头和结尾的行
        module_pattern = re.compile(r'^[-=]{3,}.*[-=]{3,}$')

        def has_chinese(text):
            return any('\u4e00' <= ch <= '\u9fff' for ch in text)

        def extract_chinese(text):
            """提取文本中的中文部分（包括标点符号和数字），如果包含中文则返回该部分"""
            if not text:
                return ""
            start = -1
            for i, ch in enumerate(text):
                if '\u4e00' <= ch <= '\u9fff':
                    start = i
                    break
            if start == -1:
                return ""
            return text[start:].strip()

        def flush():
            nonlocal current_keys, current_lines, pending_keys
            if not current_keys and not current_lines:
                return

            all_keys = pending_keys + current_keys
            text = "\n".join(current_lines).strip()

            if not text:
                if all_keys:
                    pending_keys.extend(all_keys)
                current_keys = []
                current_lines = []
                return

            processed_text = KeyExplanation._replace_numbers_for_display(text)

            # 只保留尚未存在于 result 中的键
            new_keys = [k for k in all_keys if k.lower() not in result]

            if new_keys:
                key_list = " / ".join(f"{k}=" for k in new_keys)
                display = f"{key_list}\n\n{processed_text}"
                for k in new_keys:
                    result[k.lower()] = display

            pending_keys = []
            current_keys = []
            current_lines = []

        for line in lines:
            stripped = line.strip()

            # 1. 忽略分号后的内容
            if ';' in stripped:
                stripped = stripped.split(';')[0].strip()

            if not stripped:
                if current_keys or pending_keys:
                    current_lines.append("")
                continue

            # 2. 模块行检测（保留，不忽略）
            if module_pattern.match(stripped):
                if current_lines:
                    current_lines.append(stripped)
                else:
                    flush()
                continue

            # 3. 键值对检测
            m = key_pattern.match(stripped)
            if m:
                key_name = m.group(1)
                rest = m.group(2).strip()

                # 如果当前有说明文字在收集，且遇到了新键，先提交之前的内容
                if current_lines:
                    flush()

                current_keys.append(key_name)

                # 检查 = 后面是否有中文
                if rest:
                    cn_text = extract_chinese(rest)
                    if cn_text:
                        current_lines.append(cn_text)
                        flush()
                continue

            # 4. 普通说明行
            if current_keys or pending_keys:
                if not current_lines:
                    cn_text = extract_chinese(stripped)
                    if cn_text:
                        current_lines.append(cn_text)
                else:
                    current_lines.append(stripped)
            else:
                if has_chinese(stripped):
                    # 没有键在收集时的纯中文行，忽略（通常是模块描述）
                    pass

        flush()
        return result

    # ---------------- weapons 分段说明 ----------------

    def load_weapons(self, filepath):
        """加载 weapons_explanation.txt，按段落分别存入三个字典。"""
        if not os.path.isfile(filepath):
            return False
        content = strip_ini_comments(self._read_file(filepath))
        self.weapon_descs, self.warhead_descs, self.projectile_descs = \
            self._parse_weapons(content)
        self.weapons_loaded = True
        self.sources["weapons"] = filepath
        return True

    def _parse_weapons(self, content):
        """
        针对 weapons_explanation.txt 的特殊处理。
        因为该文件有明确的模块划分（武器代码、弹头代码、抛射体代码），
        需要返回三个不同的字典。
        """
        weapon_descs = {}
        warhead_descs = {}
        projectile_descs = {}

        lines = content.splitlines()
        current_section = None
        current_key = None
        current_lines = []
        pending_keys = []

        key_pattern = re.compile(r'^([A-Za-z][A-Za-z0-9_.]*)\s*=\s*(.*)$')
        section_header_weapon = re.compile(r'=+\s*武器代码\s*=+')
        section_header_warhead = re.compile(r'=+\s*弹头代码\s*=+')
        section_header_projectile = re.compile(r'=+\s*抛射体代码\s*=+')
        module_pattern = re.compile(r'^[-=]{3,}.*[-=]{3,}$')

        def has_chinese(text):
            return any('\u4e00' <= ch <= '\u9fff' for ch in text)

        def extract_chinese(text):
            if not text:
                return ""
            start = -1
            for i, ch in enumerate(text):
                if '\u4e00' <= ch <= '\u9fff':
                    start = i
                    break
            if start == -1:
                return ""
            return text[start:].strip()

        def flush():
            nonlocal current_key, current_lines, pending_keys
            if not current_key and not pending_keys:
                return

            all_keys = pending_keys + ([current_key] if current_key else [])
            text = "\n".join(current_lines).strip()

            if not text:
                if all_keys:
                    pending_keys.extend(all_keys)
                current_key = None
                current_lines = []
                return

            processed_text = KeyExplanation._replace_numbers_for_display(text)

            # 根据当前模块确定目标字典
            target = None
            if current_section == self.SECTION_WEAPON:
                target = weapon_descs
            elif current_section == self.SECTION_WARHEAD:
                target = warhead_descs
            elif current_section == self.SECTION_PROJECTILE:
                target = projectile_descs

            if target is not None and all_keys:
                # 只保留尚未存在于 target 中的键
                new_keys = [k for k in all_keys if k.lower() not in target]
                if new_keys:
                    key_list = " / ".join(f"{k}=" for k in new_keys)
                    display = f"{key_list}\n\n{processed_text}"
                    for k in new_keys:
                        target[k.lower()] = display

            pending_keys = []
            current_key = None
            current_lines = []

        for line in lines:
            stripped = line.strip()
            if ';' in stripped:
                stripped = stripped.split(';')[0].strip()
            if not stripped:
                if current_key or pending_keys:
                    current_lines.append("")
                continue

            # 检测模块标题（保留，作为当前模块说明的一部分）
            if section_header_weapon.search(stripped):
                flush()
                current_section = self.SECTION_WEAPON
                current_lines.append(stripped)
                continue
            if section_header_warhead.search(stripped):
                flush()
                current_section = self.SECTION_WARHEAD
                current_lines.append(stripped)
                continue
            if section_header_projectile.search(stripped):
                flush()
                current_section = self.SECTION_PROJECTILE
                current_lines.append(stripped)
                continue

            # 普通模块分隔符（如 ----），保留
            if module_pattern.match(stripped):
                if current_lines:
                    current_lines.append(stripped)
                else:
                    flush()
                    if has_chinese(stripped):
                        current_lines.append(stripped)
                continue

            m = key_pattern.match(stripped)
            if m:
                key_name = m.group(1)
                rest = m.group(2).strip()

                if current_lines:
                    flush()

                current_key = key_name
                if rest:
                    cn_text = extract_chinese(rest)
                    if cn_text:
                        current_lines.append(cn_text)
                        flush()
                continue

            # 普通说明行
            if current_key or pending_keys:
                if not current_lines:
                    cn_text = extract_chinese(stripped)
                    if cn_text:
                        current_lines.append(cn_text)
                else:
                    current_lines.append(stripped)

        flush()
        return weapon_descs, warhead_descs, projectile_descs

    # ---------------- general 补充说明 ----------------

    def load_general(self, filepath):
        if not os.path.isfile(filepath):
            return False
        content = self._read_file(filepath)
        content = strip_ini_comments(content)
        extra = self._parse_unified(content)
        added = 0
        for k, v in extra.items():
            if k not in self.descriptions:
                self.descriptions[k] = v
            else:
                self.descriptions[k] = self.descriptions[k] + "\n\n【补充】\n" + v
            added += 1
        self.loaded = True
        self.sources["general"] = filepath
        self._last_general_count = added    # ← 记下来
        return True

    def load_ares(self, filepath):
        if not os.path.isfile(filepath):
            return False
        content = strip_ini_comments(self._read_file(filepath))
        self.ares_descs = self._parse_unified(content)
        self.ares_loaded = True
        self.sources["ares"] = filepath
        return True

    def merge_from_text(self, content):
        """从文本解析后合并到 self.descriptions（覆盖同名键）。"""
        new_descs = self._parse_unified(content)
        self.descriptions.update(new_descs)   # 导入的覆盖已有
        return len(new_descs)

    def merge_from_text_ai(self, content):
        new_descs = self._parse_unified(content)
        self.ai_descs.update(new_descs)
        return len(new_descs)

    def merge_from_text_ares(self, content):
        new_descs = self._parse_unified(content)
        self.ares_descs.update(new_descs)
        return len(new_descs)

    # ---------------- 查询接口 ----------------

    def get_particle_system(self, key):
        if not key:
            return None
        return self.particle_system_descs.get(key.lower())

    def get_particle(self, key):
        if not key:
            return None
        return self.particle_descs.get(key.lower())

    def get_art(self, key):
        if not key:
            return None
        return self.arts_descs.get(key.lower())

    def get(self, key):
        if not key:
            return None
        return self.descriptions.get(key.lower())

    def get_weapon(self, key):
        if not key:
            return None
        return self.weapon_descs.get(key.lower())

    def get_warhead(self, key):
        if not key:
            return None
        return self.warhead_descs.get(key.lower())

    def get_projectile(self, key):
        if not key:
            return None
        return self.projectile_descs.get(key.lower())

    def get_ai(self, key):
        if not key:
            return None
        return self.ai_descs.get(key.lower())

    def get_ares(self, key):
        if not key:
            return None
        return self.ares_descs.get(key.lower())

