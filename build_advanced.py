#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级构建脚本
支持多种构建模式和命令行参数

使用方法:
    python build_advanced.py --mode release
    python build_advanced.py --mode debug
    python build_advanced.py --mode portable
    python build_advanced.py --help
"""

import argparse
import os
import sys
import shutil
import time
from pathlib import Path
from PyInstaller import __main__ as pyi
from build_config import (
    BASE_CONFIG, DATA_FILES, HIDDEN_IMPORTS, 
    BUILD_MODES, VERSION_INFO_TEMPLATE
)

class BuildManager:
    """构建管理器"""
    
    def __init__(self, mode='release', verbose=False):
        self.mode = mode
        self.verbose = verbose
        self.start_time = time.time()
        
    def log(self, message, level='INFO'):
        """日志输出"""
        timestamp = time.strftime('%H:%M:%S')
        print(f"[{timestamp}] {level}: {message}")
        
    def clean_build_dirs(self):
        """清理构建目录"""
        dirs_to_clean = ['build', 'dist', '__pycache__', '*.spec']
        
        for pattern in dirs_to_clean:
            if '*' in pattern:
                # 处理通配符
                import glob
                for path in glob.glob(pattern):
                    if os.path.isfile(path):
                        os.remove(path)
                        self.log(f"已删除文件: {path}")
            else:
                if os.path.exists(pattern):
                    if os.path.isdir(pattern):
                        shutil.rmtree(pattern)
                        self.log(f"已清理目录: {pattern}")
                    else:
                        os.remove(pattern)
                        self.log(f"已删除文件: {pattern}")
    
    def get_version_info(self):
        """获取版本信息"""
        try:
            with open('pyproject.toml', 'r', encoding='utf-8') as f:
                content = f.read()
                for line in content.split('\n'):
                    if line.strip().startswith('version'):
                        version = line.split('=')[1].strip().strip('"').strip("'")
                        return version
        except Exception as e:
            self.log(f"读取版本信息失败: {e}", 'WARNING')
        return "1.0.0"
    
    def create_version_file(self, version):
        """创建版本信息文件"""
        version_tuple = version.replace('.', ',')
        version_content = VERSION_INFO_TEMPLATE.format(
            version=version,
            version_tuple=version_tuple
        )
        
        with open('version_info.txt', 'w', encoding='utf-8') as f:
            f.write(version_content)
        self.log("已创建版本信息文件")
    
    def build_params(self, mode_config, version):
        """构建PyInstaller参数"""
        params = []
        
        # 基础配置
        if not BASE_CONFIG['console']:
            params.append('--noconsole')
        if BASE_CONFIG['windowed']:
            params.append('--windowed')
        if BASE_CONFIG['uac_admin']:
            params.append('--uac-admin')
        if BASE_CONFIG['clean']:
            params.append('--clean')
        
        # 图标
        if BASE_CONFIG['icon'] and os.path.exists(BASE_CONFIG['icon']):
            params.append(f"--icon={BASE_CONFIG['icon']}")
        
        # 输出名称
        params.append(f"--name={BASE_CONFIG['name']}")
        
        # 构建模式特定配置
        if mode_config['onefile']:
            params.append('--onefile')
        else:
            params.append('--onedir')
        
        if mode_config['optimize'] > 0:
            params.append(f"--optimize={mode_config['optimize']}")
        
        if mode_config['strip']:
            params.append('--strip')
        
        if mode_config['debug']:
            params.append('--debug=all')
        
        if mode_config.get('upx', False):
            params.append('--upx-dir=upx')  # 需要UPX在PATH中或指定路径
        
        # 数据文件
        for src, dst in DATA_FILES:
            if os.path.exists(src):
                params.append(f'--add-data={src};{dst}')
            else:
                self.log(f"警告: 数据文件不存在: {src}", 'WARNING')
        
        # 隐藏导入
        for module in HIDDEN_IMPORTS:
            params.append(f'--hidden-import={module}')
        
        # 排除模块
        for module in mode_config.get('exclude_modules', []):
            params.append(f'--exclude-module={module}')
        
        # 版本信息
        if os.path.exists('version_info.txt'):
            params.append('--version-file=version_info.txt')
        
        # 主脚本
        params.append(BASE_CONFIG['main_script'])
        
        return params
    
    def validate_environment(self):
        """验证构建环境"""
        # 检查必要文件
        required_files = [BASE_CONFIG['main_script'], BASE_CONFIG['icon']]
        for file_path in required_files:
            if not os.path.exists(file_path):
                self.log(f"错误: 必要文件不存在: {file_path}", 'ERROR')
                return False
        
        # 检查数据目录
        for src, _ in DATA_FILES:
            if not os.path.exists(src):
                self.log(f"警告: 数据文件/目录不存在: {src}", 'WARNING')
        
        return True
    
    def build(self):
        """执行构建"""
        self.log(f"开始构建 {BASE_CONFIG['name']} (模式: {self.mode})")
        
        # 验证环境
        if not self.validate_environment():
            self.log("环境验证失败", 'ERROR')
            return False
        
        # 获取构建配置
        if self.mode not in BUILD_MODES:
            self.log(f"未知的构建模式: {self.mode}", 'ERROR')
            return False
        
        mode_config = BUILD_MODES[self.mode]
        
        # 清理构建目录
        self.clean_build_dirs()
        
        # 获取版本信息
        version = self.get_version_info()
        self.log(f"版本: {version}")
        
        # 创建版本信息文件
        self.create_version_file(version)
        
        # 构建参数
        params = self.build_params(mode_config, version)
        
        if self.verbose:
            self.log("PyInstaller 参数:")
            for param in params:
                self.log(f"  {param}")
        
        try:
            # 执行构建
            self.log("正在执行 PyInstaller...")
            pyi.run(params)
            
            # 检查输出
            self.check_output(mode_config)
            
            # 构建完成
            elapsed = time.time() - self.start_time
            self.log(f"构建完成! 耗时: {elapsed:.2f}秒")
            return True
            
        except Exception as e:
            self.log(f"构建失败: {e}", 'ERROR')
            return False
        finally:
            # 清理临时文件
            if os.path.exists('version_info.txt'):
                os.remove('version_info.txt')
    
    def check_output(self, mode_config):
        """检查输出文件"""
        if mode_config['onefile']:
            exe_path = Path(f'dist/{BASE_CONFIG["name"]}.exe')
        else:
            exe_path = Path(f'dist/{BASE_CONFIG["name"]}/{BASE_CONFIG["name"]}.exe')
        
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            self.log(f"输出文件: {exe_path}")
            self.log(f"文件大小: {size_mb:.2f} MB")
            
            # 性能建议
            if size_mb > 100:
                self.log("提示: 文件较大，考虑使用 portable 模式或排除更多模块", 'WARNING')
        else:
            self.log("警告: 未找到输出文件", 'WARNING')

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='AtlantisWatcher 高级构建脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
构建模式说明:
  release  - 发布版本 (单文件, 优化, 体积适中)
  debug    - 调试版本 (目录形式, 无优化, 包含调试信息)
  portable - 便携版本 (单文件, 高度优化, 最小体积)

示例:
  python build_advanced.py --mode release
  python build_advanced.py --mode debug --verbose
        """
    )
    
    parser.add_argument(
        '--mode', '-m',
        choices=list(BUILD_MODES.keys()),
        default='release',
        help='构建模式 (默认: release)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='详细输出'
    )
    
    parser.add_argument(
        '--list-modes',
        action='store_true',
        help='列出所有可用的构建模式'
    )
    
    args = parser.parse_args()
    
    if args.list_modes:
        print("可用的构建模式:")
        for mode, config in BUILD_MODES.items():
            print(f"  {mode:10} - {'单文件' if config['onefile'] else '目录形式'}, "
                  f"优化级别: {config['optimize']}, "
                  f"调试: {'是' if config['debug'] else '否'}")
        return
    
    # 创建构建管理器并执行构建
    builder = BuildManager(mode=args.mode, verbose=args.verbose)
    success = builder.build()
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()