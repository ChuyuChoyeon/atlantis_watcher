import subprocess
import sys
import ctypes
from fastapi import FastAPI, HTTPException,WebSocket,status
from fastapi.responses import JSONResponse
import asyncio
import pyautogui
import cv2
import numpy as np
from pydantic import BaseModel
import os
import threading
import pystray
from PIL import Image
import uvicorn
import socket

from uvicorn.config import Config
# 解决打包后路径问题
if getattr(sys, 'frozen', False):
    os.chdir(sys._MEIPASS)
config = Config("main:app", host="0.0.0.0", port=8988,log_config=None)
server = uvicorn.Server(config)
# 解决打包后路径问题
app = FastAPI()
class CommandRequest(BaseModel):
    command: str
    is_powershell: bool = False

def execute_windows_command_safe(command: str):
    """
    使用subprocess安全执行Windows命令
    """
    try:
        result = subprocess.run(
            ["cmd", "/c", command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=False,
            timeout=30
        )
        return {
            "output": result.stdout or "命令执行成功，无输出",
            "error": result.stderr,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"output": "", "error": "命令执行超时", "returncode": -1}
    except Exception as e:
        return {"output": "", "error": str(e), "returncode": -1}


def shutdown_windows(delay: int = 0):
    """
    使用Windows API实现关机
    """
    try:
        if delay > 0:
            command = f"shutdown /s /t {delay}"
        else:
            command = "shutdown /s /t 0"
        return execute_windows_command_safe(command)
    except Exception as e:
        return {"output": "", "error": str(e), "returncode": -1}


def reboot_windows():
    """
    使用Windows API实现重启
    """
    try:
        return execute_windows_command_safe("shutdown /r /t 0")
    except Exception as e:
        return {"output": "", "error": str(e), "returncode": -1}


def cancel_shutdown() -> dict:
    """
    同步执行取消关机命令，返回标准化字典
    """
    try:
        result = subprocess.run(
            ["shutdown", "/a"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout.strip() or "取消关机命令已发送",
            "error": result.stderr,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "命令执行超时", "returncode": -1}
    except Exception as e:
        return {"success": False, "error": str(e), "returncode": -1}

# 命令执行API
@app.post("/cmd")
async def execute_command(request: CommandRequest):
    """
    执行命令的API端点，支持普通命令和PowerShell命令
    """
    try:
        if request.is_powershell:
            # 执行PowerShell命令
            command = f"powershell.exe -Command \"{request.command}\""
        else:
            # 执行普通命令
            command = request.command

        # 执行命令并捕获输出
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30
        )

        return {
            "output": result.stdout or "命令执行成功，无输出",
            "error": result.stderr,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=408,
            detail={"error": "命令执行超时", "output": "", "returncode": -1}
        )
    except subprocess.CalledProcessError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"执行失败: {e}",
                "output": e.stderr,
                "returncode": e.returncode
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"系统错误: {str(e)}",
                "output": "",
                "returncode": -1
            }
        )
# 关机API
@app.post("/shutdown")
async def shutdown():
    return shutdown_windows()


# 定时关机API
@app.post("/shutdown/{seconds}")
async def shutdown_with_delay(seconds: int):
    return shutdown_windows(delay=seconds)


# 取消关机API

@app.post("/cancel")
async def api_cancel_shutdown():
    """
    取消关机的API端点，返回JSON响应
    """
    result = cancel_shutdown()  # 调用同步函数
    if not result["success"]:
        raise HTTPException(
            status_code=500,
            detail=result
        )
    return JSONResponse(content=result)


# 重启API
@app.post("/reboot")
async def reboot():
    return reboot_windows()

def run_server():
    """启动FastAPI服务"""
    server.run()



def on_exit(icon, item):
    """退出应用程序"""
    icon.stop()
    os._exit(0)

def on_restart(icon, item):
    """重启服务"""
    server.should_exit = True
    threading.Thread(target=run_server, daemon=True).start()


def get_lan_ip():
    """获取本机局域网IP（192.168开头）"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('192.168.255.255', 1))
        ip = s.getsockname()[0]
        s.close()
        if ip.startswith('192.168.'):
            return ip
        else:
            return '未检测到192.168网段'
    except Exception:
        return '获取IP失败'

def setup_tray_icon():
    """创建系统托盘图标"""
    ip = get_lan_ip()
    image = Image.open("icon.ico") if os.path.exists("icon.ico") else Image.new('RGB', (64, 64), (255, 255, 255))
    menu = pystray.Menu(
        pystray.MenuItem('重启服务', on_restart),
        pystray.MenuItem(f"本机IP: {ip}", lambda icon, item: None),
        pystray.MenuItem('退出', on_exit)
    )
    icon = pystray.Icon("AtlantisWatcher", image, f"AtlantisWatcher\n本机IP: {ip}\nChoyeon", menu)
    icon.run()

@app.websocket("/ws/screen")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            img = pyautogui.screenshot()
            frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
            await websocket.send_bytes(buffer.tobytes())
            await asyncio.sleep(0.05)  # 10fps
    except Exception as e:
        print(f"连接关闭: {e}")

@app.post("/lock", status_code=status.HTTP_200_OK)
async def lock_screen():
    try:
        result = subprocess.run(
            ["rundll32.exe", "user32.dll,LockWorkStation"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout.strip() or "锁屏命令已发送",
            "error": result.stderr,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=408,
            detail={"error": "锁屏命令执行超时", "output": "", "returncode": -1}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": f"系统错误: {str(e)}", "output": "", "returncode": -1}
        )

@app.post("/logout", status_code=status.HTTP_200_OK)
async def logout():
    try:
        result = subprocess.run(
            ["shutdown", "/l"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout.strip() or "注销命令已发送",
            "error": result.stderr,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=408,
            detail={"error": "注销命令执行超时", "output": "", "returncode": -1}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": f"系统错误: {str(e)}", "output": "", "returncode": -1}
        )
def add_to_startup():
    import win32com.client
    startup_path = os.path.join(
        os.environ["APPDATA"],
        r"Microsoft\Windows\Start Menu\Programs\Startup"
    )
    exe_path = sys.executable
    shortcut_path = os.path.join(startup_path, "AtlantisWatcher.lnk")
    if not os.path.exists(shortcut_path):
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = exe_path
        shortcut.WorkingDirectory = os.path.dirname(exe_path)
        shortcut.IconLocation = exe_path
        shortcut.save()

if __name__ == "__main__":
    add_to_startup()
    def is_admin():
        """检查当前是否具有管理员权限"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False


    if not is_admin():
        # 重新以管理员权限运行程序
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit()
    # 启动服务线程
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # 启动系统托盘
    setup_tray_icon()