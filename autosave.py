# -*- coding: utf-8 -*-
"""自动保存管理器：定时把当前编辑的 INI 副本保存到 saves/ 目录。

职责：
- 计算项目根目录和 saves 目录
- 启动/停止定时器（使用 Tk 的 after 机制）
- 每次触发时写一份带时间戳的副本
- 保留最近 N 个副本，超出则删除最旧的
- 提供"打开 saves 文件夹"的跨平台实现

不直接操作界面，状态通过 on_status 回调通知调用方。
"""

import os
import sys
import time
import glob
import subprocess

from config import (
    AUTOSAVE_INTERVAL_MS,
    AUTOSAVE_MAX_FILES,
    AUTOSAVE_DIR_NAME,
    AUTOSAVE_PREFIX,
)


class AutosaveManager:
    """管理定时自动保存。

    参数：
        root:            tk.Tk() 实例（用于 after / after_cancel）
        get_filepath:    回调，返回当前正在编辑的文件路径（str 或 None）
        save_func:       回调，save_func(path) 把当前 parser 的内容写到 path
        on_status:       回调，on_status(text) 更新状态栏（可为 None）
    """

    def __init__(self, root, get_filepath, save_func, on_status=None):
        self.root = root
        self.get_filepath = get_filepath
        self.save_func = save_func
        self.on_status = on_status or (lambda text: None)

        self.enabled = True
        self._job = None
        self.autosave_dir = self._get_autosave_dir()

    # ---------------- 路径 ----------------

    @staticmethod
    def _get_root_dir():
        """项目根目录：本文件所在目录。"""
        try:
            return os.path.dirname(os.path.abspath(__file__))
        except NameError:
            return os.getcwd()

    def _get_autosave_dir(self):
        return os.path.join(self._get_root_dir(), AUTOSAVE_DIR_NAME)

    def ensure_dir(self):
        os.makedirs(self.autosave_dir, exist_ok=True)

    # ---------------- 启停 ----------------

    def start(self):
        """启动（或重启）定时器。"""
        self.cancel()
        if self.enabled:
            self._job = self.root.after(AUTOSAVE_INTERVAL_MS, self._tick)

    def cancel(self):
        if self._job is not None:
            try:
                self.root.after_cancel(self._job)
            except Exception:
                pass
            self._job = None

    def set_enabled(self, flag: bool):
        self.enabled = bool(flag)
        if self.enabled:
            self.start()
        else:
            self.cancel()

    # ---------------- 定时回调 ----------------

    def _tick(self):
        self._job = None
        try:
            self.save_now()
        except Exception as e:
            self.on_status(f"自动保存失败: {e}")
        finally:
            self.start()

    # ---------------- 实际保存 ----------------

    def save_now(self):
        """立即执行一次自动保存（可被菜单手动调用）。"""
        filepath = self.get_filepath()
        if not filepath or not os.path.isfile(filepath):
            return

        self.ensure_dir()

        base = os.path.basename(filepath)
        name, ext = os.path.splitext(base)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        dst_name = f"{AUTOSAVE_PREFIX}{name}_{stamp}{ext or '.ini'}"
        dst_path = os.path.join(self.autosave_dir, dst_name)

        self.save_func(dst_path)
        self._prune()
        self.on_status(
            f"已自动保存副本: {dst_name}  ({time.strftime('%H:%M:%S')})"
        )

    def _prune(self):
        self.ensure_dir()
        pattern = os.path.join(self.autosave_dir, f"{AUTOSAVE_PREFIX}*")
        files = [f for f in glob.glob(pattern) if os.path.isfile(f)]
        files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        for old in files[AUTOSAVE_MAX_FILES:]:
            try:
                os.remove(old)
            except OSError:
                pass

    # ---------------- 打开文件夹 ----------------

    def open_folder(self):
        """在系统文件管理器中打开 saves 目录。"""
        self.ensure_dir()
        path = self.autosave_dir
        if sys.platform.startswith("win"):
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
