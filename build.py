from PyInstaller import __main__ as pyi
import os

# 打包参数配置
params = [
    '--noconsole',  # 不显示控制台窗口
    '--icon=icon.ico',  # 设置图标
    '--clean',  # 清理临时文件
    '--windowed',  # 窗口化
    '--uac-admin',  # 请求管理员权限
    '--name=AtlantisWatcher',  # 输出文件名
    '--add-data=icon.ico;.',  # 添加图标文件
    '--add-data=webgui;webgui',  # 添加webgui目录
    '--add-data=main.py;.',  # 添加主程序文件
    
    
    'main.py'
]

# 执行打包
pyi.run(params)