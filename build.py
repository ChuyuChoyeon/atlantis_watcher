from PyInstaller import __main__ as pyi
import os
import sys
import shutil
from pathlib import Path

def clean_build_dirs():
    """清理之前的构建目录"""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"已清理目录: {dir_name}")

def get_version_info():
    """获取版本信息"""
    try:
        with open('pyproject.toml', 'r', encoding='utf-8') as f:
            content = f.read()
            for line in content.split('\n'):
                if line.startswith('version'):
                    version = line.split('=')[1].strip().strip('"')
                    return version
    except Exception:
        pass
    return "1.0.0"

def build_application():
    """构建应用程序"""
    print("开始构建 AtlantisWatcher...")
    
    # 清理构建目录
    clean_build_dirs()
    
    version = get_version_info()
    print(f"版本: {version}")
    
    # 打包参数配置
    params = [
        '--noconsole',  # 不显示控制台窗口
        '--onefile',    # 打包成单个文件
        '--icon=icon.ico',  # 设置图标
        '--clean',  # 清理临时文件
        '--windowed',  # 窗口化
        '--uac-admin',  # 请求管理员权限
        '--name=AtlantisWatcher',  # 输出文件名
        
        # 数据文件
        '--add-data=icon.ico;.',
        '--add-data=template;template',
        '--add-data=main.py;.',
        
        
        # 隐藏导入（解决运行时导入问题）
        '--hidden-import=uvicorn.lifespan.on',
        '--hidden-import=uvicorn.lifespan.off',
        '--hidden-import=uvicorn.protocols.websockets.auto',
        '--hidden-import=uvicorn.protocols.http.auto',
        '--hidden-import=uvicorn.protocols.websockets.websockets_impl',
        '--hidden-import=uvicorn.protocols.http.httptools_impl',
        '--hidden-import=uvicorn.protocols.http.h11_impl',
        '--hidden-import=uvicorn.loops.auto',
        '--hidden-import=uvicorn.loops.asyncio',
        '--hidden-import=uvicorn.logging',
        '--hidden-import=pystray._win32',
        '--hidden-import=PIL._tkinter_finder',
        '--hidden-import=cv2',
        '--hidden-import=numpy',
        '--hidden-import=psutil',
        '--hidden-import=pyautogui',
        '--hidden-import=fastapi',
        '--hidden-import=multipart',
        
        # 排除不必要的模块（减小文件大小）
        '--exclude-module=tkinter',
        '--exclude-module=matplotlib',
        '--exclude-module=scipy',
        '--exclude-module=pandas',
        '--exclude-module=jupyter',
        '--exclude-module=IPython',
        '--exclude-module=notebook',
        '--exclude-module=pytest',
        '--exclude-module=setuptools',
        
        # 优化选项
        '--optimize=2',  # 字节码优化
        '--strip',       # 去除调试信息
        
        # 版本信息
        f'--version-file=version_info.txt',
        
        'main.py'
    ]
    
    try:
        # 执行打包
        print("正在执行 PyInstaller...")
        pyi.run(params)
        print("构建完成！")
        
        # 检查输出文件
        exe_path = Path('dist/AtlantisWatcher.exe')
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"输出文件: {exe_path}")
            print(f"文件大小: {size_mb:.2f} MB")
        else:
            print("警告: 未找到输出文件")
            
    except Exception as e:
        print(f"构建失败: {e}")
        sys.exit(1)

def create_version_file():
    """创建版本信息文件"""
    version = get_version_info()
    version_info = f"""# UTF-8
#
# 版本信息
#
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({version.replace('.', ',')},0),
    prodvers=({version.replace('.', ',')},0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'AtlantisWatcher'),
        StringStruct(u'FileDescription', u'Atlantis System Watcher'),
        StringStruct(u'FileVersion', u'{version}'),
        StringStruct(u'InternalName', u'AtlantisWatcher'),
        StringStruct(u'LegalCopyright', u'Copyright (C) 2024'),
        StringStruct(u'OriginalFilename', u'AtlantisWatcher.exe'),
        StringStruct(u'ProductName', u'AtlantisWatcher'),
        StringStruct(u'ProductVersion', u'{version}')])
      ]), 
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)"""
    
    with open('version_info.txt', 'w', encoding='utf-8') as f:
        f.write(version_info)
    print("已创建版本信息文件")

if __name__ == '__main__':
    print("AtlantisWatcher 构建脚本")
    print("=" * 40)
    
    # 创建版本信息文件
    create_version_file()
    
    # 构建应用程序
    build_application()
    
    print("=" * 40)
    print("构建脚本执行完成")