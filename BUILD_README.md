# AtlantisWatcher 构建指南

本项目提供了多种构建脚本来满足不同的打包需求。

## 构建脚本说明

### 1. build.py (优化版基础构建脚本)

这是优化后的基础构建脚本，包含了以下改进：

- ✅ 自动清理构建目录
- ✅ 版本信息自动提取
- ✅ 隐藏导入配置（解决运行时错误）
- ✅ 模块排除优化（减小文件大小）
- ✅ 构建结果验证
- ✅ 错误处理和日志

**使用方法：**
```bash
python build.py
```

### 2. build_advanced.py (高级构建脚本)

支持多种构建模式和命令行参数的高级构建脚本。

**构建模式：**

| 模式 | 描述 | 特点 |
|------|------|------|
| `release` | 发布版本 | 单文件、优化级别2、适中体积 |
| `debug` | 调试版本 | 目录形式、无优化、包含调试信息 |
| `portable` | 便携版本 | 单文件、高度优化、最小体积 |

**使用方法：**
```bash
# 发布版本（默认）
python build_advanced.py

# 指定构建模式
python build_advanced.py --mode release
python build_advanced.py --mode debug
python build_advanced.py --mode portable

# 详细输出
python build_advanced.py --mode release --verbose

# 查看帮助
python build_advanced.py --help

# 列出所有构建模式
python build_advanced.py --list-modes
```

### 3. build_config.py (构建配置文件)

包含所有构建相关的配置，便于维护和自定义。

## 构建优化说明

### 隐藏导入 (Hidden Imports)

解决以下运行时导入问题：
- FastAPI 和 Uvicorn 相关模块
- 系统托盘 (pystray) Windows 实现
- PIL 图像处理
- OpenCV、NumPy 等核心依赖

### 模块排除 (Exclude Modules)

排除不必要的模块以减小文件大小：
- 开发工具：pytest, setuptools, pip
- 数据科学：matplotlib, scipy, pandas
- Jupyter 相关：jupyter, IPython, notebook
- GUI 框架：tkinter

### 优化选项

- `--optimize=2`: 字节码优化
- `--strip`: 去除调试信息
- `--onefile`: 打包成单个可执行文件
- `--upx`: UPX 压缩（portable 模式）

## 构建前准备

1. **确保所有依赖已安装：**
   ```bash
   pip install -r requirements.txt
   # 或者如果使用 pyproject.toml
   pip install .
   ```

2. **检查必要文件：**
   - `main.py` - 主程序文件
   - `icon.ico` - 应用程序图标
   - `webgui/` - Web界面目录
   - `pyproject.toml` - 项目配置文件

## 构建输出

构建完成后，输出文件位于：
- **单文件模式**: `dist/AtlantisWatcher.exe`
- **目录模式**: `dist/AtlantisWatcher/AtlantisWatcher.exe`

## 故障排除

### 常见问题

1. **ModuleNotFoundError 运行时错误**
   - 检查 `build_config.py` 中的 `HIDDEN_IMPORTS` 配置
   - 添加缺失的模块到隐藏导入列表

2. **文件大小过大**
   - 使用 `portable` 模式
   - 在 `EXCLUDE_MODULES` 中添加更多不需要的模块
   - 考虑使用 UPX 压缩

3. **构建失败**
   - 使用 `--verbose` 参数查看详细日志
   - 检查 PyInstaller 版本兼容性
   - 确保所有依赖文件存在

### 调试技巧

1. **使用调试模式：**
   ```bash
   python build_advanced.py --mode debug
   ```

2. **检查依赖：**
   ```bash
   pyi-makespec --onefile main.py
   # 检查生成的 .spec 文件
   ```

3. **测试隐藏导入：**
   ```bash
   python -c "import uvicorn.lifespan.on"
   ```

## 自定义配置

要自定义构建配置，编辑 `build_config.py` 文件：

```python
# 添加新的隐藏导入
HIDDEN_IMPORTS.append('your_module')

# 排除额外模块
EXCLUDE_MODULES.append('unwanted_module')

# 添加新的构建模式
BUILD_MODES['custom'] = {
    'onefile': True,
    'optimize': 1,
    'strip': False,
    'upx': False,
    'debug': False,
    'exclude_modules': ['tkinter'],
}
```

## 性能建议

1. **首次构建**: 使用 `debug` 模式快速验证
2. **发布构建**: 使用 `release` 模式平衡性能和大小
3. **分发构建**: 使用 `portable` 模式获得最小文件
4. **定期清理**: 构建脚本会自动清理，但可手动删除 `build/` 和 `dist/` 目录

## 版本信息

构建脚本会自动从 `pyproject.toml` 提取版本信息并嵌入到可执行文件中。确保版本格式正确：

```toml
[project]
version = "1.0.0"
```

---

**注意**: 首次构建可能需要较长时间，后续构建会更快。建议在发布前测试所有构建模式。