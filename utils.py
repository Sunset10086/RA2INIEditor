"""通用工具：跨编码读取文件、去 INI 行内注释。"""


def read_file_auto_encoding(filepath, encodings=('utf-8', 'gbk', 'latin-1', 'cp1252')):
    """尝试多种编码读取文件，返回 (content, encoding)。"""
    for enc in encodings:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                return f.read(), enc
        except UnicodeDecodeError:
            continue
    # 全部失败，用二进制兜底
    with open(filepath, 'rb') as f:
        return f.read().decode('utf-8', errors='ignore'), 'utf-8'


def strip_ini_line_comment(line):
    """去掉行内英文分号 ; 之后的内容（引号内的分号保留）。"""
    in_quotes = False
    for i, ch in enumerate(line):
        if ch == '"':
            in_quotes = not in_quotes
        elif ch == ';' and not in_quotes:
            return line[:i]
    return line


def strip_ini_comments(content):
    """对整个文本按行去注释。"""
    return "\n".join(strip_ini_line_comment(ln) for ln in content.splitlines())
