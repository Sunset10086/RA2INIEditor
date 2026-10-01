"""节中文名解析器：解析 sections_explanation.txt，得到 {节名(大写): 中文名}。

统一规则：
1. 忽略注释行（以 ; 开头）以及行内 ; 之后的内容。
2. 忽略以多个 = 或 - 组成的分隔行、空行、纯中文行。
3. 节名（英文字母开头、可含数字和下划线）与中文名之间以一个或多个
   - = 空格（可混合）连接。
4. 节名可能在左侧（必须在行首，允许前导空格），也可能在右侧（行尾）。
5. 行内 ** 表示隐藏单位，显示时加在中文名后。
6. 行尾 =YR / =RA2 / =GH 表示专属版本，显示时加在中文名前。
"""
import os
import re

from utils import read_file_auto_encoding, strip_ini_comments


class SectionNameMap:
    """解析 sections_explanation.txt。"""

    def __init__(self):
        self.names = {}
        self.loaded = False
        self.source_path = None

    def load(self, filepath):
        self.names = {}
        self.loaded = False
        self.source_path = filepath

        if not os.path.isfile(filepath):
            return False

        content = strip_ini_comments(self._read_file(filepath))
        self.names = self._parse(content)
        self.loaded = True
        return True

    def _read_file(self, filepath):
        content, _ = read_file_auto_encoding(filepath, ('utf-8', 'gbk', 'latin-1'))
        return content

    def _parse(self, content):
        names = {}
        for raw_line in content.splitlines():
            line = raw_line.strip()

            # 忽略空行
            if not line:
                continue
            # 忽略行内注释（分号后的内容）
            if ';' in line:
                line = line.split(';')[0].strip()
                if not line:
                    continue
            # 忽略以等号或分隔符开头的行（==== 分隔行）
            if line.startswith('=') or line.startswith('---'):
                continue
            # 忽略纯中文行（无英文节名）
            if not re.search(r'[A-Za-z]', line):
                continue

            pair = self._parse_line(line)
            if pair:
                sec, cn = pair
                if sec and cn:
                    names.setdefault(sec.upper(), cn)

        return names

    def _parse_line(self, line):
        """解析一行，返回 (节名, 中文名) 或 None。"""
        hidden = '**' in line
        version = self._extract_version(line)

        # 去掉版本标记，避免它干扰后续解析
        line_no_ver = re.sub(r'=\s*[A-Za-z][A-Za-z0-9_]*\s*$', '', line).rstrip()

        # ---- 情况 1：节名在左侧（行首，允许前导空白）----
        m = re.match(r'^([A-Za-z][A-Za-z0-9_]*)[\s\-=]+(.+)$', line_no_ver)
        if m:
            sec = m.group(1)
            cn_part = m.group(2).strip()
            cn = self._clean_cn(cn_part)
            if cn:
                cn = self._decorate_cn(cn, hidden, version)
                return (sec, cn)

        # ---- 情况 3：节名在中间（优先于"行尾模式"，避免误判武器列表）----
        # 用分隔符把行切成若干段，取最左边第一个纯英文段作为节名
        parts = re.split(r'[\s\-=]+', line_no_ver)
        for i, part in enumerate(parts):
            if not part:
                continue
            if re.match(r'^[A-Za-z][A-Za-z0-9_]*$', part):
                left_text = ' '.join(parts[:i]).strip()
                cn = self._clean_cn(left_text)
                if cn:
                    cn = self._decorate_cn(cn, hidden, version)
                    return (part, cn)
                # 左侧没中文，说明这个英文不是节名，继续扫

        # ---- 情况 2：节名在右侧（行尾）----
        # 只有在上面两个都没匹配到时才走这里
        m = re.match(r'^(.+?)[\s\-=]+([A-Za-z][A-Za-z0-9_]*)$', line_no_ver)
        if m:
            cn_part = m.group(1).strip()
            sec = m.group(2)
            cn = self._clean_cn(cn_part)
            if cn:
                cn = self._decorate_cn(cn, hidden, version)
                return (sec, cn)

        return None

    def _extract_version(self, line):
        m = re.search(r'=\s*([A-Za-z][A-Za-z0-9_]*)\s*$', line)
        if m:
            return m.group(1).upper()
        return None
    
    def _decorate_cn(self, cn, hidden, version):
        cn = cn.replace('**', '').strip()
        if version:
            cn = f"[{version}]" + cn
        if hidden:
            cn = cn + "**"
        return cn

    def _clean_cn(self, text):
        """清理中文名中残留的分隔符、等号、方括号内容等。"""
        if not text:
            return ""
        # 去掉尾部残留的 - 或 =（如果中文名后还接了武器列表等）
        text = re.split(r'-{2,}', text, maxsplit=1)[0]
        text = re.split(r'[=＝]', text, maxsplit=1)[0]
        # 去掉可能的 [xxx] 标签
        text = text.split('[')[0]
        # 去掉隐藏标记
        text = text.replace('**', '')
        return text.strip()

    def get(self, section_name):
        if not section_name:
            return None
        return self.names.get(section_name.upper())

    def merge_from_text(self, content):
        """从文本解析后合并到 self.names（覆盖同名节）。"""
        new_names = self._parse(content)
        self.names.update(new_names)
        return len(new_names)
