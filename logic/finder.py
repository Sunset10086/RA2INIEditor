"""查找逻辑：循环查找下一个节 / 下一个注册项。

这些函数只负责算出「下一个匹配位置」，不做 UI 选中。
UI 层拿到位置后自己调用 listbox.selection_set 等。
"""


def find_next_in_list(items, keyword, start_pos):
    """在 items（字符串列表）里，从 start_pos+1 开始循环查找包含 keyword 的项。

    返回找到的位置；找不到返回 -1。匹配不区分大小写。
    """
    if not items:
        return -1
    n = len(items)
    if start_pos >= n:
        start_pos = -1
    start = start_pos + 1
    kw = keyword.lower()
    for offset in range(n):
        i = (start + offset) % n
        if kw in items[i].lower():
            return i
    return -1


def find_next_registry_item(displayed_items, keyword, start_pos, key_as_name):
    """在注册表项里循环查找。

    displayed_items : [(key, value), ...] 当前显示顺序
    keyword         : 关键字（大小写不敏感）
    start_pos       : 上次找到的位置（-1 表示从头开始）
    key_as_name     : True 表示用 key 作为名字匹配，False 用 value
    返回找到的位置；找不到返回 -1。
    """
    if not displayed_items:
        return -1
    n = len(displayed_items)
    if start_pos >= n:
        start_pos = -1
    start = start_pos + 1
    kw = keyword.lower()
    for offset in range(n):
        i = (start + offset) % n
        key, value = displayed_items[i]
        name = key if key_as_name else (value if value else key)
        if kw in name.lower():
            return i
    return -1


def registry_name_of(displayed_items, pos, key_as_name):
    """取 displayed_items[pos] 用于匹配的名字（key 或 value）。"""
    if pos < 0 or pos >= len(displayed_items):
        return None
    key, value = displayed_items[pos]
    return key if key_as_name else (value if value else key)
