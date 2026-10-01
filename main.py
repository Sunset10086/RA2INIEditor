"""
RA2 Rules.INI 查看器 —— 程序入口

运行方式：
    python main.py

说明文件（可选，放在同目录下会被自动加载）：
    rules_explanation.txt      通用键说明
    general_explanation.txt    全局段补充说明
    weapons_explanation.txt    武器/弹头/抛射体说明
    sections_explanation.txt   节的中文名
"""
import tkinter as tk

from ui.main_window import IniViewerApp
    
def main():
    try:
        root = tk.Tk()
        app = IniViewerApp(root)
        root.mainloop()
    except Exception:
        import traceback
        traceback.print_exc()
        input("按回车键退出...")


if __name__ == "__main__":
    main()
