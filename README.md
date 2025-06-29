
# AtlantisWatcher

AtlantisWatcher 是一个基于 FastAPI 的 Windows 远程控制工具，支持关机、重启、定时关机、取消关机、锁屏、注销、命令行执行、屏幕实时预览等功能，并集成系统托盘和开机自启动。

## 功能特性

- 远程关机、重启、定时关机、取消关机
- 一键锁屏、注销
- 实时屏幕预览（WebSocket 推送）
- 远程命令行/PowerShell 执行
- 托盘显示本机局域网 IP
- 程序开机自启动（自动创建快捷方式到启动文件夹）
- 移动端友好 Web 控制页面


## 截图

![AtlantisWatcher 截图](img/server.png)
![AtlantisWatcher 截图](img/client%20(1).jpg)
![AtlantisWatcher 截图](img/client%20(2).jpg)
![AtlantisWatcher 截图](img/client%20(3).jpg)




## 依赖环境

- Python 3.8+
- FastAPI
- Uvicorn
- pyautogui
- opencv-python
- numpy
- pystray
- pillow
- pywin32
- pydantic

安装依赖：
```
pip install -r requirements.txt
```
或手动安装：
```
pip install fastapi uvicorn pyautogui opencv-python numpy pystray pillow pywin32 pydantic
```

## 打包为 EXE

使用 PyInstaller 一键打包（需先安装 PyInstaller）：
```
pip install pyinstaller
python build.py
```
打包后生成的 `main.exe` 可直接运行。

## 使用说明

1. 运行 `main.py` 或打包后的 `main.exe`，程序会自动添加自启动。
2. 托盘图标显示本机 192.168 开头的 IP，便于局域网访问。
3. 用浏览器访问 `http://本机IP:8988`，即可打开控制页面。
4. 支持移动端访问和操作。

## FastAPI 接口

- `POST /shutdown` 立即关机
- `POST /shutdown/{seconds}` 定时关机
- `POST /reboot` 重启
- `POST /cancel` 取消关机
- `POST /lock` 锁屏
- `POST /logout` 注销
- `POST /cmd` 执行命令（支持 PowerShell）

## 注意事项

- 需以管理员权限运行以保证部分操作（如关机、重启）权限。
- 首次运行会自动添加自启动快捷方式到 `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`。
- 屏幕推流和命令执行仅限局域网内访问，注意安全。
- 确保防火墙允许访问 8988 端口。
- 若使用移动端访问，确保手机和电脑在同一局域网内。
- 注意保护局域网的安全，避免未授权访问。

---

如有问题请提交 Issue。