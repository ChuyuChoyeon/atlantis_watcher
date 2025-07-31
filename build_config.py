# -*- coding: utf-8 -*-
"""
构建配置文件
定义不同的构建模式和选项
"""

# 基础配置
BASE_CONFIG = {
    'name': 'AtlantisWatcher',
    'icon': 'icon.ico',
    'main_script': 'main.py',
    'console': False,
    'windowed': True,
    'uac_admin': True,
    'clean': True,
}

# 数据文件配置
DATA_FILES = [
    ('icon.ico', '.'),
    ('webgui', 'webgui'),
]

# 隐藏导入配置
HIDDEN_IMPORTS = [
    # FastAPI 和 Uvicorn 相关
    'uvicorn.lifespan.on',
    'uvicorn.lifespan.off',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets.websockets_impl',
    'uvicorn.protocols.http.httptools_impl',
    'uvicorn.protocols.http.h11_impl',
    'uvicorn.loops.auto',
    'uvicorn.loops.asyncio',
    'uvicorn.logging',
    
    # 系统托盘和GUI相关
    'pystray._win32',
    'PIL._tkinter_finder',
    
    # 核心依赖
    'cv2',
    'numpy',
    'psutil',
    'pyautogui',
    'fastapi',
    'multipart',
]

# 排除模块配置
EXCLUDE_MODULES = [
    'tkinter',
    'matplotlib',
    'scipy',
    'pandas',
    'jupyter',
    'IPython',
    'notebook',
    'pytest',
    'setuptools',
    'distutils',
    'wheel',
    'pip',
]

# 构建模式配置
BUILD_MODES = {
    'release': {
        'onefile': True,
        'optimize': 2,
        'strip': True,
        'upx': False,  # UPX压缩（可选）
        'debug': False,
        'exclude_modules': EXCLUDE_MODULES,
    },
    
    'debug': {
        'onefile': False,
        'optimize': 0,
        'strip': False,
        'upx': False,
        'debug': True,
        'exclude_modules': [],  # 调试模式不排除模块
    },
    
    'portable': {
        'onefile': True,
        'optimize': 2,
        'strip': True,
        'upx': True,  # 启用UPX压缩以减小文件大小
        'debug': False,
        'exclude_modules': EXCLUDE_MODULES + [
            'email',
            'xml',
            'urllib3',
            'certifi',
        ],
    }
}

# 版本信息模板
VERSION_INFO_TEMPLATE = """# UTF-8
#
# 版本信息
#
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({version_tuple},0),
    prodvers=({version_tuple},0),
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