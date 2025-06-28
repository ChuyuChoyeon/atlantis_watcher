from PyInstaller import __main__ as pyi
import os

# 打包参数配置
params = [
    '--onefile',  # 单文件打包
    '--noconsole',  # 不显示控制台窗口
    '--name=main',  # 输出文件名
    '--add-data=icon.ico;.',  # 添加图标文件
    'main.py'
]

# 执行打包
pyi.run(params)