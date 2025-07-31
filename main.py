import subprocess
import sys
import ctypes
import time
import functools
from fastapi import FastAPI, HTTPException,WebSocket,status, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
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
import psutil
import json
from datetime import datetime
import subprocess
import logging
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path

from uvicorn.config import Config

# 配置日志系统
def setup_logging():
    """设置日志配置"""
    # 创建日志目录
    log_dir = Path.cwd()
    log_file = log_dir / "log.txt"
    
    # 创建自定义格式器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 创建文件处理器（带轮转）
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # 配置uvicorn日志
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.handlers = [file_handler, console_handler]
    uvicorn_logger.setLevel(logging.INFO)
    
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_access_logger.handlers = [file_handler]
    uvicorn_access_logger.setLevel(logging.INFO)
    
    # 配置FastAPI日志
    fastapi_logger = logging.getLogger("fastapi")
    fastapi_logger.handlers = [file_handler, console_handler]
    fastapi_logger.setLevel(logging.INFO)
    
    return logging.getLogger(__name__)

# 初始化日志
logger = setup_logging()
logger.info("=== Atlantis Watcher 启动 ===")

# 异常处理装饰器
def log_exceptions(func):
    """异常处理装饰器"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"函数 {func.__name__} 发生异常: {str(e)}")
            logger.error(f"异常详情: {traceback.format_exc()}")
            raise
    return wrapper

def async_log_exceptions(func):
    """异步函数异常处理装饰器"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"异步函数 {func.__name__} 发生异常: {str(e)}")
            logger.error(f"异常详情: {traceback.format_exc()}")
            raise
    return wrapper

# 解决打包后路径问题
if getattr(sys, 'frozen', False):
    os.chdir(sys._MEIPASS)
config = Config("main:app", host="0.0.0.0", port=8988,log_config=None)
server = uvicorn.Server(config)
# 解决打包后路径问题
app = FastAPI()

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有头部
)

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")


# 根路径返回主页
@app.get("/")
async def read_root():
    return FileResponse("template/index.html")
class CommandRequest(BaseModel):
    command: str
    is_powershell: bool = False

class ProcessKillRequest(BaseModel):
    pid: int
    force: bool = False

@log_exceptions
def execute_windows_command_safe(command: str):
    """
    使用subprocess安全执行Windows命令
    
    Args:
        command: 要执行的命令字符串
        
    Returns:
        包含命令执行结果的字典，包括输出、错误和返回码
        
    Raises:
        subprocess.TimeoutExpired: 当命令执行超时时
        Exception: 其他执行错误
    """
    try:
        # 记录即将执行的命令
        logger.info(f"执行CMD命令: {command}")
        
        # 检查命令是否包含危险操作
        dangerous_commands = ['format', 'deltree', 'rd /s', 'rmdir /s', 'del /f', 'del /q']
        for cmd in dangerous_commands:
            if cmd.lower() in command.lower():
                error_msg = f"命令包含危险操作: {cmd}"
                logger.warning(f"安全检查失败: {error_msg} - 原命令: {command}")
                return {
                    "output": "", 
                    "error": error_msg, 
                    "returncode": -1,
                    "success": False
                }
        
        # 执行命令
        logger.debug(f"开始执行命令: {command}")
        result = subprocess.run(
            ["cmd", "/c", command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=False,
            timeout=60  # 增加超时时间到60秒
        )
        
        # 处理结果
        success = result.returncode == 0
        output = result.stdout.strip()
        error = result.stderr.strip()
        
        # 如果成功但没有输出，添加默认消息
        if success and not output:
            output = "命令执行成功，无输出"
            
        response = {
            "output": output,
            "error": error,
            "returncode": result.returncode,
            "success": success
        }
        
        if success:
            logger.info(f"命令执行成功: {command}")
        else:
            logger.warning(f"命令执行失败 (返回码: {result.returncode}): {command} - 错误: {error}")
            
        return response
    except subprocess.TimeoutExpired:
        error_msg = "命令执行超时（60秒）"
        logger.error(f"命令执行超时: {command} - 超时时间: 60秒")
        return {
            "output": "", 
            "error": error_msg, 
            "returncode": -1,
            "success": False
        }
    except Exception as e:
        error_msg = f"命令执行异常: {str(e)}"
        logger.error(f"命令执行异常: {command} - 错误: {error_msg}")
        logger.error(f"异常详情: {traceback.format_exc()}")
        return {
            "output": "", 
            "error": error_msg, 
            "returncode": -1,
            "success": False
        }


@log_exceptions
def shutdown_windows(delay: int = 0):
    """
    使用Windows API实现关机
    """
    logger.info(f"执行系统关机操作，延迟: {delay}秒")
    try:
        if delay > 0:
            command = f"shutdown /s /t {delay}"
        else:
            command = "shutdown /s /t 0"
        result = execute_windows_command_safe(command)
        if result.get("success", True):
            logger.info("系统关机命令执行成功")
        else:
            logger.error(f"系统关机失败: {result.get('error', '')}")
        return result
    except Exception as e:
        logger.error(f"系统关机异常: {str(e)}")
        logger.error(f"异常详情: {traceback.format_exc()}")
        return {"output": "", "error": str(e), "returncode": -1, "success": False}


@log_exceptions
def reboot_windows():
    """
    使用Windows API实现重启
    """
    logger.info("执行系统重启操作")
    try:
        result = execute_windows_command_safe("shutdown /r /t 0")
        if result.get("success", True):
            logger.info("系统重启命令执行成功")
        else:
            logger.error(f"系统重启失败: {result.get('error', '')}")
        return result
    except Exception as e:
        logger.error(f"系统重启异常: {str(e)}")
        logger.error(f"异常详情: {traceback.format_exc()}")
        return {"output": "", "error": str(e), "returncode": -1, "success": False}


@log_exceptions
def cancel_shutdown() -> dict:
    """
    同步执行取消关机命令，返回标准化字典
    """
    logger.info("执行取消关机/重启操作")
    try:
        result = subprocess.run(
            ["shutdown", "/a"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        success = result.returncode == 0
        response = {
            "success": success,
            "output": result.stdout.strip() or "取消关机命令已发送",
            "error": result.stderr,
            "returncode": result.returncode
        }
        if success:
            logger.info("取消关机/重启命令执行成功")
        else:
            logger.warning(f"取消关机/重启失败 - 返回码: {result.returncode}, 错误: {result.stderr}")
        return response
    except subprocess.TimeoutExpired:
        logger.error("取消关机/重启命令执行超时")
        return {"success": False, "error": "命令执行超时", "returncode": -1}
    except Exception as e:
        logger.error(f"取消关机/重启异常: {str(e)}")
        logger.error(f"异常详情: {traceback.format_exc()}")
        return {"success": False, "error": str(e), "returncode": -1}

# 命令执行API
@app.post("/cmd")
async def execute_command(request: CommandRequest):
    """
    执行命令的API端点，支持普通命令和PowerShell命令
    """
    try:
        # 记录命令执行请求
        logger.info(f"API请求 - 执行命令: {request.command} (PowerShell: {request.is_powershell})")
        
        # 检查命令是否包含危险操作
        dangerous_commands = ['format', 'deltree', 'rd /s', 'rmdir /s', 'del /f', 'del /q']
        for cmd in dangerous_commands:
            if cmd.lower() in request.command.lower():
                error_msg = f"命令包含危险操作: {cmd}"
                logger.warning(f"API安全检查失败: {error_msg} - 原命令: {request.command}")
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": error_msg,
                        "output": "",
                        "returncode": -1
                    }
                )
        
        if request.is_powershell:
            # 执行PowerShell命令
            command = f"powershell.exe -ExecutionPolicy Bypass -Command \"{request.command}\""
            logger.info(f"执行PowerShell命令: {command}")
        else:
            # 执行普通命令
            command = request.command
            logger.info(f"执行普通命令: {command}")

        # 执行命令并捕获输出
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60  # 增加超时时间
        )

        response_data = {
            "output": result.stdout or "命令执行成功，无输出",
            "error": result.stderr,
            "returncode": result.returncode
        }
        
        logger.info(f"API命令执行成功: {request.command}")
        return response_data
        
    except subprocess.TimeoutExpired:
        error_msg = "命令执行超时（60秒）"
        logger.error(f"API命令执行超时: {request.command}")
        raise HTTPException(
            status_code=408,
            detail={"error": error_msg, "output": "", "returncode": -1}
        )
    except subprocess.CalledProcessError as e:
        error_msg = f"执行失败: {e}"
        logger.error(f"API命令执行失败: {request.command} - 错误: {error_msg}")
        raise HTTPException(
            status_code=400,
            detail={
                "error": error_msg,
                "output": e.stderr,
                "returncode": e.returncode
            }
        )
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        error_msg = f"系统错误: {str(e)}"
        logger.error(f"API命令执行异常: {request.command} - 错误: {error_msg}")
        logger.error(f"异常详情: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": error_msg,
                "output": "",
                "returncode": -1
            }
        )
# 关机API
@app.post("/shutdown")
async def shutdown():
    result = shutdown_windows()
    if not result.get("success", True):
        raise HTTPException(
            status_code=500,
            detail=result
        )
    return JSONResponse(content=result)


# 定时关机API
@app.post("/shutdown/{seconds}")
async def shutdown_with_delay(seconds: int):
    result = shutdown_windows(delay=seconds)
    if not result.get("success", True):
        raise HTTPException(
            status_code=500,
            detail=result
        )
    return JSONResponse(content=result)


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
    result = reboot_windows()
    if not result.get("success", True):
        raise HTTPException(
            status_code=500,
            detail=result
        )
    return JSONResponse(content=result)

# 系统监控API
@app.get("/api/system/info")
async def get_system_info():
    """获取系统基本信息"""
    logger.info("API请求 - 获取系统信息")
    
    try:
        # CPU信息
        logger.debug("获取CPU信息")
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        
        # 内存信息
        logger.debug("获取内存信息")
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # 磁盘信息
        logger.debug("获取磁盘信息")
        disk_partitions = []
        for partition in psutil.disk_partitions():
            try:
                partition_usage = psutil.disk_usage(partition.mountpoint)
                disk_partitions.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "total": partition_usage.total,
                    "used": partition_usage.used,
                    "free": partition_usage.free,
                    "percent": round((partition_usage.used / partition_usage.total) * 100, 2)
                })
            except PermissionError as e:
                logger.warning(f"无权限访问磁盘分区 {partition.device}: {str(e)}")
                continue
            except Exception as e:
                logger.error(f"获取磁盘分区信息失败 {partition.device}: {str(e)}")
                continue
        
        # 网络信息
        logger.debug("获取网络信息")
        network_io = psutil.net_io_counters()
        network_interfaces = []
        for interface, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == socket.AF_INET:
                    network_interfaces.append({
                        "interface": interface,
                        "ip": addr.address,
                        "netmask": addr.netmask
                    })
        
        system_info = {
            "timestamp": datetime.now().isoformat(),
            "cpu": {
                "percent": cpu_percent,
                "count": cpu_count,
                "frequency": {
                    "current": cpu_freq.current if cpu_freq else None,
                    "min": cpu_freq.min if cpu_freq else None,
                    "max": cpu_freq.max if cpu_freq else None
                }
            },
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "percent": memory.percent,
                "swap_total": swap.total,
                "swap_used": swap.used,
                "swap_percent": swap.percent
            },
            "disk": disk_partitions,
            "network": {
                "io": {
                    "bytes_sent": network_io.bytes_sent,
                    "bytes_recv": network_io.bytes_recv,
                    "packets_sent": network_io.packets_sent,
                    "packets_recv": network_io.packets_recv
                },
                "interfaces": network_interfaces
            }
        }
        
        logger.info("系统信息获取成功")
        return system_info
        
    except Exception as e:
        error_msg = f"获取系统信息失败: {str(e)}"
        logger.error(f"API获取系统信息异常: {error_msg}")
        logger.error(f"异常详情: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/api/system/processes")
async def get_processes():
    """获取进程列表"""
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status', 'create_time']):
            try:
                proc_info = proc.info
                # 限制CPU百分比在合理范围内（0-100%）
                cpu_percent = proc_info['cpu_percent'] or 0
                cpu_percent = max(0, min(cpu_percent, 100))  # 确保在0-100%范围内
                
                processes.append({
                    "pid": proc_info['pid'],
                    "name": proc_info['name'],
                    "cpu_percent": round(cpu_percent, 2),
                    "memory_percent": round(proc_info['memory_percent'] or 0, 2),
                    "status": proc_info['status'],
                    "create_time": datetime.fromtimestamp(proc_info['create_time']).isoformat()
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # 按CPU使用率排序
        processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
        return {"processes": processes[:100]}  # 返回前100个进程
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取进程列表失败: {str(e)}")

@app.post("/api/system/kill-process")
async def kill_process(request: ProcessKillRequest):
    """结束进程"""
    try:
        proc = psutil.Process(request.pid)
        proc_name = proc.name()
        
        if request.force:
            proc.kill()  # 强制结束
        else:
            proc.terminate()  # 正常结束
        
        # 等待进程结束
        try:
            proc.wait(timeout=5)
        except psutil.TimeoutExpired:
            if not request.force:
                proc.kill()  # 如果正常结束失败，强制结束
                proc.wait(timeout=3)
        
        return {
            "success": True,
            "message": f"进程 {proc_name} (PID: {request.pid}) 已结束"
        }
    except psutil.NoSuchProcess:
        raise HTTPException(status_code=404, detail="进程不存在")
    except psutil.AccessDenied:
        raise HTTPException(status_code=403, detail="权限不足，无法结束该进程")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"结束进程失败: {str(e)}")

# 文件管理相关的数据模型
class FileOperationRequest(BaseModel):
    path: str
    new_name: str = None
    target_path: str = None
    operation: str  # rename, delete, copy, move

class FileContentRequest(BaseModel):
    path: str
    content: str = None

@app.get("/api/files/drives")
async def get_drives():
    """获取所有磁盘驱动器"""
    try:
        drives = []
        if os.name == 'nt':  # Windows
            import string
            for letter in string.ascii_uppercase:
                drive = f"{letter}:\\"
                if os.path.exists(drive):
                    try:
                        usage = psutil.disk_usage(drive)
                        drives.append({
                            "name": f"{letter}盘",
                            "path": drive,
                            "total": usage.total,
                            "used": usage.used,
                            "free": usage.free,
                            "type": "drive"
                        })
                    except:
                        continue
        else:  # Linux/Mac
            drives.append({
                "name": "根目录",
                "path": "/",
                "type": "drive"
            })
        return {"success": True, "drives": drives}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取驱动器失败: {str(e)}")

@app.get("/api/files/list")
async def list_files(path: str = "/"):
    """获取指定目录下的文件和文件夹列表"""
    try:
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="路径不存在")
        
        if not os.path.isdir(path):
            raise HTTPException(status_code=400, detail="路径不是目录")
        
        items = []
        try:
            for item_name in os.listdir(path):
                item_path = os.path.join(path, item_name)
                try:
                    stat = os.stat(item_path)
                    is_dir = os.path.isdir(item_path)
                    
                    # 获取文件扩展名
                    ext = os.path.splitext(item_name)[1].lower() if not is_dir else ""
                    
                    # 判断文件类型
                    file_type = "directory" if is_dir else get_file_type(ext)
                    
                    items.append({
                        "name": item_name,
                        "path": item_path,
                        "type": file_type,
                        "size": stat.st_size if not is_dir else 0,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "is_directory": is_dir,
                        "extension": ext,
                        "permissions": oct(stat.st_mode)[-3:]
                    })
                except (PermissionError, OSError):
                    continue
        except PermissionError:
            raise HTTPException(status_code=403, detail="权限不足")
        
        # 排序：目录在前，然后按名称排序
        items.sort(key=lambda x: (not x["is_directory"], x["name"].lower()))
        
        return {
            "success": True,
            "path": path,
            "items": items,
            "parent": os.path.dirname(path) if path != os.path.dirname(path) else None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文件列表失败: {str(e)}")

def get_file_type(extension):
    """根据文件扩展名判断文件类型"""
    image_exts = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"}
    video_exts = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"}
    audio_exts = {".mp3", ".wav", ".flac", ".aac", ".ogg"}
    text_exts = {".txt", ".md", ".py", ".js", ".html", ".css", ".json", ".xml", ".yml", ".yaml"}
    executable_exts = {".exe", ".msi", ".bat", ".cmd", ".sh"}
    
    if extension in image_exts:
        return "image"
    elif extension in video_exts:
        return "video"
    elif extension in audio_exts:
        return "audio"
    elif extension in text_exts:
        return "text"
    elif extension in executable_exts:
        return "executable"
    else:
        return "file"

@app.get("/api/files/content")
async def get_file_content(path: str):
    """获取文件内容（仅限文本文件）"""
    try:
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="文件不存在")
        
        if os.path.isdir(path):
            raise HTTPException(status_code=400, detail="路径是目录，不是文件")
        
        # 检查文件大小（限制为10MB）
        file_size = os.path.getsize(path)
        if file_size > 10 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="文件过大，无法编辑")
        
        # 尝试读取文件内容
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(path, 'r', encoding='gbk') as f:
                    content = f.read()
            except UnicodeDecodeError:
                raise HTTPException(status_code=400, detail="文件不是文本文件或编码不支持")
        
        return {
            "success": True,
            "content": content,
            "size": file_size,
            "encoding": "utf-8"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取文件失败: {str(e)}")

@app.post("/api/files/content")
async def save_file_content(request: FileContentRequest):
    """保存文件内容"""
    try:
        # 创建目录（如果不存在）
        os.makedirs(os.path.dirname(request.path), exist_ok=True)
        
        # 保存文件
        with open(request.path, 'w', encoding='utf-8') as f:
            f.write(request.content)
        
        return {
            "success": True,
            "message": "文件保存成功",
            "size": len(request.content.encode('utf-8'))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存文件失败: {str(e)}")

@app.post("/api/files/operation")
async def file_operation(request: FileOperationRequest):
    """文件操作（重命名、删除、复制、移动）"""
    try:
        if not os.path.exists(request.path):
            raise HTTPException(status_code=404, detail="文件或目录不存在")
        
        if request.operation == "delete":
            if os.path.isdir(request.path):
                import shutil
                shutil.rmtree(request.path)
            else:
                os.remove(request.path)
            return {"success": True, "message": "删除成功"}
        
        elif request.operation == "rename":
            if not request.new_name:
                raise HTTPException(status_code=400, detail="新名称不能为空")
            
            new_path = os.path.join(os.path.dirname(request.path), request.new_name)
            os.rename(request.path, new_path)
            return {"success": True, "message": "重命名成功", "new_path": new_path}
        
        elif request.operation == "copy":
            if not request.target_path:
                raise HTTPException(status_code=400, detail="目标路径不能为空")
            
            import shutil
            if os.path.isdir(request.path):
                shutil.copytree(request.path, request.target_path)
            else:
                shutil.copy2(request.path, request.target_path)
            return {"success": True, "message": "复制成功"}
        
        elif request.operation == "move":
            if not request.target_path:
                raise HTTPException(status_code=400, detail="目标路径不能为空")
            
            import shutil
            shutil.move(request.path, request.target_path)
            return {"success": True, "message": "移动成功"}
        
        else:
            raise HTTPException(status_code=400, detail="不支持的操作")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"操作失败: {str(e)}")

@app.post("/api/files/execute")
async def execute_file(request: dict):
    """执行文件"""
    try:
        file_path = request.get("path")
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 检查文件类型
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext in {".exe", ".msi", ".bat", ".cmd"}:
            # 执行可执行文件
            subprocess.Popen([file_path], shell=True)
            return {"success": True, "message": "程序已启动"}
        elif ext == ".lnk":  # 快捷方式
            try:
                # 使用win32com解析快捷方式
                import win32com.client
                shell = win32com.client.Dispatch("WScript.Shell")
                shortcut = shell.CreateShortCut(file_path)
                target_path = shortcut.Targetpath
                arguments = shortcut.Arguments
                working_directory = shortcut.WorkingDirectory
                
                if target_path and os.path.exists(target_path):
                    # 构建完整的命令
                    cmd = [target_path]
                    if arguments:
                        # 简单的参数分割，可能需要更复杂的解析
                        cmd.extend(arguments.split())
                    
                    # 设置工作目录
                    cwd = working_directory if working_directory and os.path.exists(working_directory) else os.path.dirname(target_path)
                    
                    # 执行目标程序
                    subprocess.Popen(cmd, shell=True, cwd=cwd)
                    return {"success": True, "message": f"快捷方式已执行: {os.path.basename(target_path)}"}
                else:
                    # 如果无法解析目标，尝试直接启动快捷方式
                    os.startfile(file_path)
                    return {"success": True, "message": "快捷方式已执行"}
            except ImportError:
                # 如果没有win32com，回退到os.startfile
                logger.warning("缺少win32com库，使用系统默认方式打开快捷方式")
                os.startfile(file_path)
                return {"success": True, "message": "快捷方式已执行"}
            except Exception as lnk_error:
                logger.warning(f"解析快捷方式失败: {lnk_error}，尝试直接启动")
                os.startfile(file_path)
                return {"success": True, "message": "快捷方式已执行"}
        else:
            raise HTTPException(status_code=400, detail="文件类型不支持执行")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"执行文件失败: {str(e)}")

@app.get("/api/files/download")
async def download_file(path: str):
    """下载文件"""
    try:
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="文件不存在")
        
        if os.path.isdir(path):
            raise HTTPException(status_code=400, detail="不能下载目录")
        
        return FileResponse(
            path=path,
            filename=os.path.basename(path),
            media_type='application/octet-stream'
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载文件失败: {str(e)}")

@app.post("/api/files/upload")
async def upload_file(file: UploadFile = File(...), path: str = Form(...)):
    """上传文件到指定路径"""
    try:
        # 确保目标路径存在
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="目标路径不存在")
        
        if not os.path.isdir(path):
            raise HTTPException(status_code=400, detail="目标路径不是目录")
        
        # 构建完整的文件路径
        file_path = os.path.join(path, file.filename)
        
        # 检查文件是否已存在
        if os.path.exists(file_path):
            # 生成新的文件名
            base_name, ext = os.path.splitext(file.filename)
            counter = 1
            while os.path.exists(file_path):
                new_filename = f"{base_name}({counter}){ext}"
                file_path = os.path.join(path, new_filename)
                counter += 1
        
        # 保存文件
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # 获取文件信息
        file_size = os.path.getsize(file_path)
        
        logger.info(f"文件上传成功: {file_path}, 大小: {file_size} bytes")
        
        return {
            "success": True,
            "message": "文件上传成功",
            "filename": os.path.basename(file_path),
            "path": file_path,
            "size": file_size
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")

@app.get("/api/files/open")
async def open_file(path: str):
    """打开文件"""
    try:
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="文件不存在")
        
        if os.path.isdir(path):
            raise HTTPException(status_code=400, detail="不能打开目录")
        
        # 检查文件是否为二进制文件
        def is_binary_file(file_path):
            try:
                with open(file_path, 'rb') as f:
                    chunk = f.read(1024)
                    # 检查是否包含空字节（二进制文件的特征）
                    return b'\0' in chunk
            except Exception:
                return True
        
        # 检查文件大小（限制为10MB）
        file_size = os.path.getsize(path)
        if file_size > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(status_code=400, detail="文件过大，无法打开（限制10MB）")
        
        # 检查是否为二进制文件
        if is_binary_file(path):
            raise HTTPException(status_code=400, detail="二进制文件无法打开")
        
        # 尝试读取文件内容
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            encoding = 'utf-8'
        except UnicodeDecodeError:
            try:
                with open(path, 'r', encoding='gbk') as f:
                    content = f.read()
                encoding = 'gbk'
            except UnicodeDecodeError:
                try:
                    with open(path, 'r', encoding='latin-1') as f:
                        content = f.read()
                    encoding = 'latin-1'
                except Exception:
                    raise HTTPException(status_code=400, detail="无法解码文件内容")
        
        return JSONResponse({
            "success": True,
            "content": content,
            "encoding": encoding,
            "filename": os.path.basename(path),
            "size": file_size
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"打开文件失败: {str(e)}")


@app.get("/api/files/icon")
async def get_file_icon(path: str):
    """获取文件图标"""
    try:
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 检查文件扩展名
        file_ext = os.path.splitext(path)[1].lower()
        
        # 支持的可执行文件和快捷方式
        if file_ext in ['.exe', '.lnk']:
            try:
                import win32gui
                import win32api
                import win32con
                import win32ui
                from PIL import Image
                import io
                import base64
                
                # 获取文件图标
                if file_ext == '.lnk':
                    # 处理快捷方式
                    try:
                        import win32com.client
                        shell = win32com.client.Dispatch("WScript.Shell")
                        shortcut = shell.CreateShortCut(path)
                        target_path = shortcut.Targetpath
                        if target_path and os.path.exists(target_path):
                            path = target_path
                            file_ext = os.path.splitext(target_path)[1].lower()
                        else:
                            # 如果目标不存在，使用默认快捷方式图标
                            return JSONResponse({
                                "success": True,
                                "icon_type": "emoji",
                                "icon": "🔗"
                            })
                    except Exception as lnk_error:
                        logger.warning(f"解析快捷方式失败: {lnk_error}")
                        return JSONResponse({
                            "success": True,
                            "icon_type": "emoji",
                            "icon": "🔗"
                        })
                
                # 提取exe文件图标
                try:
                    # 使用更简单的方法获取图标
                    ico_x = win32api.GetSystemMetrics(win32con.SM_CXICON)
                    ico_y = win32api.GetSystemMetrics(win32con.SM_CYICON)
                    
                    large, small = win32gui.ExtractIconEx(path, 0)
                    if large and len(large) > 0:
                        hicon = large[0]
                        
                        # 创建设备上下文
                        hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
                        hbmp = win32ui.CreateBitmap()
                        hbmp.CreateCompatibleBitmap(hdc, ico_x, ico_y)
                        hdc = hdc.CreateCompatibleDC()
                        
                        hdc.SelectObject(hbmp)
                        # 绘制图标到位图
                        win32gui.DrawIconEx(hdc.GetHandleOutput(), 0, 0, hicon, ico_x, ico_y, 0, None, win32con.DI_NORMAL)
                        
                        # 获取位图数据
                        bmpstr = hbmp.GetBitmapBits(True)
                        img = Image.frombuffer('RGB', (ico_x, ico_y), bmpstr, 'raw', 'BGRX', 0, 1)
                        
                        # 转换为base64
                        buffer = io.BytesIO()
                        img.save(buffer, format='PNG')
                        icon_base64 = base64.b64encode(buffer.getvalue()).decode()
                        
                        # 清理资源
                        win32gui.DestroyIcon(hicon)
                        hdc.DeleteDC()
                        win32gui.ReleaseDC(0, hdc.GetHandleOutput())
                        
                        return JSONResponse({
                            "success": True,
                            "icon_type": "base64",
                            "icon": f"data:image/png;base64,{icon_base64}"
                        })
                    else:
                        # 没有图标，返回默认
                        default_icon = "⚙️" if file_ext == '.exe' else "🔗"
                        return JSONResponse({
                            "success": True,
                            "icon_type": "emoji",
                            "icon": default_icon
                        })
                    
                except Exception as icon_error:
                    logger.warning(f"提取图标失败: {icon_error}")
                    # 如果提取失败，返回默认图标
                    default_icon = "⚙️" if file_ext == '.exe' else "🔗"
                    return JSONResponse({
                        "success": True,
                        "icon_type": "emoji",
                        "icon": default_icon
                    })
                    
            except ImportError as import_error:
                logger.warning(f"缺少win32相关库，无法提取图标: {import_error}")
                # 返回默认图标
                default_icon = "⚙️" if file_ext == '.exe' else "🔗"
                return JSONResponse({
                    "success": True,
                    "icon_type": "emoji",
                    "icon": default_icon
                })
        
        # 其他文件类型返回默认图标
        return JSONResponse({
            "success": True,
            "icon_type": "emoji",
            "icon": "📄"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文件图标失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取文件图标失败: {str(e)}")

@log_exceptions
def run_server():
    """启动FastAPI服务"""
    logger.info("启动FastAPI服务器")
    
    try:
        logger.info("FastAPI服务器配置完成，开始运行")
        server.run()
    except Exception as e:
        logger.error(f"FastAPI服务器启动失败: {str(e)}")
        logger.error(f"异常详情: {traceback.format_exc()}")
        raise



def on_exit(icon, item):
    """退出应用程序"""
    logger.info("用户请求退出应用程序")
    
    try:
        logger.info("停止系统托盘图标")
        icon.stop()
        
        logger.info("应用程序正常退出")
        os._exit(0)
        
    except Exception as e:
        logger.error(f"退出应用程序时出错: {str(e)}")
        logger.error(f"异常详情: {traceback.format_exc()}")
        # 强制退出
        os._exit(1)

def on_restart(icon, item):
    """重启服务"""
    logger.info("用户请求重启服务")
    
    try:
        # 停止当前服务器
        global server
        if server:
            logger.info("停止当前服务器")
            server.should_exit = True
            
        # 等待服务器完全关闭
        logger.debug("等待服务器关闭")
        time.sleep(2)
        
        # 重新启动服务器
        logger.info("正在重启服务...")
        threading.Thread(target=run_server, daemon=True).start()
        
        # 更新托盘图标提示
        try:
            ip = get_lan_ip()
            icon.title = f"AtlantisWatcher\n本机IP: {ip}\n服务已重启"
            logger.debug(f"更新托盘图标标题: {ip}")
        except Exception as e:
            logger.warning(f"更新托盘图标标题时出错: {str(e)}")
        
        # 显示通知
        try:
            if hasattr(icon, 'notify'):
                icon.notify("服务已成功重启")
                logger.debug("已发送重启成功通知")
        except Exception as e:
            logger.warning(f"发送重启通知时出错: {str(e)}")
            
        logger.info("服务重启完成")
        
    except Exception as e:
        logger.error(f"重启服务时出错: {str(e)}")
        logger.error(f"异常详情: {traceback.format_exc()}")
        
        try:
            if hasattr(icon, 'notify'):
                icon.notify(f"重启服务失败: {str(e)}")
        except Exception as notify_error:
            logger.warning(f"发送错误通知时出错: {str(notify_error)}")


@log_exceptions
def get_lan_ip():
    """获取本机局域网IP（192.168开头）"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('192.168.255.255', 1))
        ip = s.getsockname()[0]
        s.close()
        if ip.startswith('192.168.'):
            logger.debug(f"获取到局域网IP: {ip}")
            return ip
        else:
            logger.warning("未检测到192.168网段")
            return '未检测到192.168网段'
    except Exception as e:
        logger.warning(f"获取局域网IP失败: {str(e)}")
        return '获取IP失败'

@log_exceptions
def setup_tray_icon():
    """创建系统托盘图标"""
    logger.info("初始化系统托盘图标")
    
    try:
        ip = get_lan_ip()
        
        # 尝试加载图标，如果找不到则创建一个默认图标
        try:
            # 首先尝试在当前目录查找图标
            if os.path.exists("icon.ico"):
                logger.info("使用当前目录的icon.ico")
                image = Image.open("icon.ico")
            # 然后尝试在脚本所在目录查找图标
            elif os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")):
                icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
                logger.info(f"使用脚本目录的图标: {icon_path}")
                image = Image.open(icon_path)
            # 如果都找不到，创建一个默认图标
            else:
                logger.info("未找到图标文件，创建默认图标")
                # 创建一个蓝色背景的图标
                image = Image.new('RGB', (64, 64), (0, 120, 212))
        except Exception as e:
            logger.warning(f"加载图标时出错: {str(e)}，使用默认图标")
            image = Image.new('RGB', (64, 64), (0, 120, 212))
        
        # 创建菜单项
        logger.debug("创建系统托盘菜单")
        menu = pystray.Menu(
            pystray.MenuItem('重启服务', on_restart),
            pystray.MenuItem(f"本机IP: {ip}", lambda icon, item: None),
            pystray.MenuItem('刷新IP', lambda icon, item: refresh_ip(icon)),
            pystray.MenuItem('退出', on_exit)
        )
        
        # 创建图标
        icon = pystray.Icon("AtlantisWatcher", image, f"AtlantisWatcher\n本机IP: {ip}\n服务运行中", menu)
        logger.info("系统托盘图标创建成功")
        
        # 运行图标
        try:
            logger.info("启动系统托盘图标")
            icon.run()
        except Exception as e:
            logger.error(f"运行系统托盘图标时出错: {str(e)}")
            logger.error(f"异常详情: {traceback.format_exc()}")
            
    except Exception as e:
        logger.error(f"设置系统托盘图标失败: {str(e)}")
        logger.error(f"异常详情: {traceback.format_exc()}")
        raise

@log_exceptions
def refresh_ip(icon):
    """刷新IP地址并更新托盘图标"""
    logger.info("开始刷新IP地址")
    
    try:
        ip = get_lan_ip()
        logger.debug(f"获取到新IP地址: {ip}")
        
        # 更新图标标题
        icon.title = f"AtlantisWatcher\n本机IP: {ip}\n服务运行中"
        
        # 更新菜单项
        try:
            for item in icon.menu:
                if "本机IP:" in str(item):
                    # 由于pystray不支持直接更新菜单项文本，我们需要重新创建菜单
                    new_menu = pystray.Menu(
                        pystray.MenuItem('重启服务', on_restart),
                        pystray.MenuItem(f"本机IP: {ip}", lambda icon, item: None),
                        pystray.MenuItem('刷新IP', lambda icon, item: refresh_ip(icon)),
                        pystray.MenuItem('退出', on_exit)
                    )
                    icon.menu = new_menu
                    logger.debug("系统托盘菜单已更新")
                    break
        except Exception as e:
            logger.warning(f"更新菜单时出错: {str(e)}")
        
        # 显示通知
        try:
            if hasattr(icon, 'notify'):
                icon.notify(f"IP已刷新: {ip}")
                logger.debug("已发送IP刷新通知")
        except Exception as e:
            logger.warning(f"发送通知时出错: {str(e)}")
            
        logger.info(f"IP已刷新: {ip}")
        
    except Exception as e:
        logger.error(f"刷新IP时出错: {str(e)}")
        logger.error(f"异常详情: {traceback.format_exc()}")
        
        try:
            if hasattr(icon, 'notify'):
                icon.notify(f"刷新IP失败: {str(e)}")
        except Exception as notify_error:
            logger.warning(f"发送错误通知时出错: {str(notify_error)}")

@app.websocket("/ws/monitor")
@async_log_exceptions
async def monitor_websocket(websocket: WebSocket):
    """系统监控WebSocket端点"""
    await websocket.accept()
    logger.info("系统监控WebSocket连接已建立")
    
    try:
        # 存储上一次的网络IO数据用于计算速度
        last_network_io = psutil.net_io_counters()
        last_time = time.time()
        
        while True:
            try:
                # 检查是否有来自客户端的消息
                try:
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=0.01)
                    if data == "ping":
                        await websocket.send_text("pong")
                        continue
                except asyncio.TimeoutError:
                    pass
                
                # 获取当前系统信息
                current_time = time.time()
                current_network_io = psutil.net_io_counters()
                time_diff = current_time - last_time
                
                # 计算网络速度
                upload_speed = (current_network_io.bytes_sent - last_network_io.bytes_sent) / time_diff if time_diff > 0 else 0
                download_speed = (current_network_io.bytes_recv - last_network_io.bytes_recv) / time_diff if time_diff > 0 else 0
                
                # 获取系统监控数据
                monitor_data = {
                    "timestamp": datetime.now().isoformat(),
                    "cpu_percent": psutil.cpu_percent(),
                    "memory": {
                        "percent": psutil.virtual_memory().percent,
                        "used": psutil.virtual_memory().used,
                        "total": psutil.virtual_memory().total
                    },
                    "network": {
                        "upload_speed": upload_speed,
                        "download_speed": download_speed,
                        "total_sent": current_network_io.bytes_sent,
                        "total_recv": current_network_io.bytes_recv
                    }
                }
                
                # 发送监控数据
                await websocket.send_text(json.dumps(monitor_data))
                
                # 更新上一次的数据
                last_network_io = current_network_io
                last_time = current_time
                
                # 等待2秒后发送下一次数据
                await asyncio.sleep(2)
                
            except asyncio.CancelledError:
                logger.info("监控WebSocket任务被取消")
                break
            except Exception as e:
                logger.error(f"发送监控数据错误: {str(e)}")
                # 尝试发送错误信息给客户端
                try:
                    error_data = {
                        "error": True,
                        "message": f"数据获取失败: {str(e)}",
                        "timestamp": datetime.now().isoformat()
                    }
                    await websocket.send_text(json.dumps(error_data))
                except:
                    # 如果发送失败，说明连接已断开
                    break
                
                await asyncio.sleep(2)
                
    except Exception as e:
        logger.error(f"监控WebSocket连接错误: {str(e)}")
        logger.error(f"异常详情: {traceback.format_exc()}")
    finally:
        logger.info("系统监控WebSocket连接已关闭")
        try:
            await websocket.close()
        except Exception as e:
            logger.warning(f"关闭WebSocket连接时出错: {str(e)}")

@app.websocket("/ws/screen")
@async_log_exceptions
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    last_activity = time.time()
    client_alive = True
    last_screenshot_time = 0
    target_fps = 15  # 目标帧率
    frame_interval = 1.0 / target_fps  # 帧间隔时间
    jpeg_quality = 70  # JPEG质量，更高的值意味着更好的质量但更大的文件大小
    
    logger.info(f"屏幕共享WebSocket连接已建立，目标帧率: {target_fps} FPS，图像质量: {jpeg_quality}%")
    
    # 创建心跳检测任务
    async def heartbeat():
        nonlocal client_alive
        try:
            while True:
                # 检查客户端是否超过60秒没有活动
                if time.time() - last_activity > 60:
                    logger.info("客户端超过60秒没有活动，关闭连接")
                    client_alive = False
                    break
                await asyncio.sleep(30)  # 每30秒检查一次
        except asyncio.CancelledError:
            logger.info("心跳检测任务被取消")
        except Exception as e:
            logger.error(f"心跳检测任务异常: {str(e)}")
            client_alive = False
    
    # 启动心跳检测任务
    heartbeat_task = asyncio.create_task(heartbeat())
    
    try:
        # 主循环发送屏幕截图
        while client_alive:
            try:
                # 检查是否有来自客户端的消息（非阻塞）
                data = await asyncio.wait_for(websocket.receive_text(), timeout=0.01)
                if data == "ping":
                    # 收到心跳包，更新最后活动时间
                    last_activity = time.time()
                    await websocket.send_text("pong")
                    continue
            except asyncio.TimeoutError:
                # 没有收到消息，继续发送屏幕截图
                pass
            except Exception as e:
                # 接收消息出错，可能是连接已关闭
                logger.warning(f"屏幕共享WebSocket接收消息错误: {str(e)}")
                break
            
            # 控制帧率
            current_time = time.time()
            elapsed = current_time - last_screenshot_time
            if elapsed < frame_interval:
                # 如果距离上一帧的时间不够，等待一下
                await asyncio.sleep(frame_interval - elapsed)
                continue
            
            # 发送屏幕截图
            try:
                # 更新截图时间
                last_screenshot_time = time.time()
                
                # 获取屏幕截图
                img = pyautogui.screenshot()
                frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                
                # 压缩图像
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])
                
                # 发送图像
                await websocket.send_bytes(buffer.tobytes())
                
                # 更新最后活动时间
                last_activity = time.time()
                
                # 动态调整帧率，根据处理时间调整
                processing_time = time.time() - last_screenshot_time
                if processing_time > frame_interval * 1.2:  # 如果处理时间超过预期的120%
                    # 降低目标帧率
                    target_fps = max(5, target_fps - 1)  # 不低于5 FPS
                    frame_interval = 1.0 / target_fps
                    logger.info(f"性能调整: 降低帧率至 {target_fps} FPS")
                elif processing_time < frame_interval * 0.5 and target_fps < 20:  # 如果处理时间少于预期的50%
                    # 提高目标帧率
                    target_fps = min(120, target_fps + 1)  # 不高于20 FPS
                    frame_interval = 1.0 / target_fps
                    logger.info(f"性能调整: 提高帧率至 {target_fps} FPS")
            except Exception as e:
                logger.error(f"发送屏幕截图错误: {str(e)}")
                logger.error(f"异常详情: {traceback.format_exc()}")
                break
    except Exception as e:
        logger.error(f"屏幕共享WebSocket连接错误: {str(e)}")
        logger.error(f"异常详情: {traceback.format_exc()}")
    finally:
        # 取消心跳检测任务
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            logger.debug("心跳检测任务已取消")
        except Exception as e:
            logger.warning(f"取消心跳检测任务时出错: {str(e)}")
        
        logger.info("屏幕共享WebSocket连接已关闭")
        
    # 确保连接已关闭
    try:
        await websocket.close()
    except Exception as e:
        logger.warning(f"关闭屏幕共享WebSocket连接时出错: {str(e)}")

@log_exceptions
def lock_screen_windows():
    """使用Windows API锁定屏幕"""
    logger.info("执行锁屏操作")
    try:
        # 使用ctypes调用Windows API
        import ctypes
        from ctypes import wintypes
        
        # 加载user32.dll
        user32 = ctypes.windll.user32
        
        # 调用LockWorkStation函数
        result = user32.LockWorkStation()
        
        if result:
            logger.info("锁屏命令执行成功")
            return {
                "output": "屏幕已锁定",
                "error": "",
                "returncode": 0,
                "success": True
            }
        else:
            # 获取错误代码
            error_code = ctypes.get_last_error()
            error_msg = f"锁屏失败，错误代码: {error_code}"
            logger.error(error_msg)
            return {
                "output": "",
                "error": error_msg,
                "returncode": error_code,
                "success": False
            }
    except Exception as e:
        error_msg = f"锁屏异常: {str(e)}"
        logger.error(error_msg)
        logger.error(f"异常详情: {traceback.format_exc()}")
        return {
            "output": "",
            "error": error_msg,
            "returncode": -1,
            "success": False
        }

@app.post("/lock", status_code=status.HTTP_200_OK)
async def lock_screen():
    """锁定屏幕API"""
    logger.info("API请求 - 锁定屏幕")
    
    try:
        result = lock_screen_windows()
        
        if result["success"]:
            logger.info("屏幕锁定成功")
            return JSONResponse(content=result)
        else:
            logger.warning(f"屏幕锁定失败: {result['error']}")
            raise HTTPException(
                status_code=500,
                detail=result
            )
            
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"系统错误: {str(e)}"
        logger.error(f"API锁屏操作异常: {error_msg}")
        logger.error(f"异常详情: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail={"error": error_msg, "output": "", "returncode": -1, "success": False}
        )

@app.post("/logout", status_code=status.HTTP_200_OK)
async def logout():
    logger.info("API请求 - 用户注销")
    
    try:
        result = subprocess.run(
            ["shutdown", "/l"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        response_data = {
            "success": result.returncode == 0,
            "output": result.stdout.strip() or "注销命令已发送",
            "error": result.stderr,
            "returncode": result.returncode
        }
        
        if response_data["success"]:
            logger.info("用户注销成功")
        else:
            logger.warning(f"用户注销失败 - 返回码: {result.returncode}, 错误: {result.stderr}")
            raise HTTPException(
                status_code=500,
                detail=response_data
            )
        return JSONResponse(content=response_data)
        
    except subprocess.TimeoutExpired:
        error_msg = "注销命令执行超时"
        logger.error(f"API注销操作超时")
        raise HTTPException(
            status_code=408,
            detail={"error": error_msg, "output": "", "returncode": -1, "success": False}
        )
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"系统错误: {str(e)}"
        logger.error(f"API注销操作异常: {error_msg}")
        logger.error(f"异常详情: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail={"error": error_msg, "output": "", "returncode": -1, "success": False}
        )
@log_exceptions
def add_to_startup():
    """添加到开机启动"""
    logger.info("尝试添加到开机启动")
    
    try:
        import win32com.client
        startup_path = os.path.join(
            os.environ["APPDATA"],
            r"Microsoft\Windows\Start Menu\Programs\Startup"
        )
        exe_path = sys.executable
        shortcut_path = os.path.join(startup_path, "AtlantisWatcher.lnk")
        
        if not os.path.exists(shortcut_path):
            logger.info(f"创建开机启动快捷方式: {shortcut_path}")
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.Targetpath = exe_path
            shortcut.WorkingDirectory = os.path.dirname(exe_path)
            shortcut.IconLocation = exe_path
            shortcut.save()
            logger.info("开机启动快捷方式创建成功")
        else:
            logger.info("开机启动快捷方式已存在")
            
    except ImportError as e:
        logger.error(f"缺少win32com模块，无法创建开机启动: {str(e)}")
    except Exception as e:
        logger.error(f"添加开机启动失败: {str(e)}")
        logger.error(f"异常详情: {traceback.format_exc()}")

@log_exceptions
def is_admin():
    """检查当前是否具有管理员权限"""
    try:
        result = ctypes.windll.shell32.IsUserAnAdmin()
        logger.info(f"管理员权限检查结果: {result}")
        return result
    except Exception as e:
        logger.error(f"检查管理员权限失败: {str(e)}")
        return False

@log_exceptions
def main():
    """主函数"""
    logger.info("=== Atlantis Watcher 主程序启动 ===")
    
    try:
        # 添加到开机启动
        add_to_startup()
        
        # 检查管理员权限
        if not is_admin():
            logger.info("当前没有管理员权限，尝试以管理员权限重新启动")
            try:
                ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", sys.executable, " ".join(sys.argv), None, 1
                )
                logger.info("已请求管理员权限，程序退出")
                sys.exit()
            except Exception as e:
                logger.error(f"请求管理员权限失败: {str(e)}")
                logger.warning("将以普通用户权限继续运行")
        else:
            logger.info("已获得管理员权限")
        
        # 启动服务线程
        logger.info("启动FastAPI服务线程")
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        # 启动系统托盘
        logger.info("启动系统托盘")
        setup_tray_icon()
        
    except KeyboardInterrupt:
        logger.info("收到键盘中断信号，程序退出")
    except Exception as e:
        logger.error(f"主程序运行异常: {str(e)}")
        logger.error(f"异常详情: {traceback.format_exc()}")
        raise
    finally:
        logger.info("=== Atlantis Watcher 程序结束 ===")

if __name__ == "__main__":
    main()