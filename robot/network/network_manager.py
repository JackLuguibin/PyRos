from typing import Dict, Optional, Callable, Any
import logging
import socket
import json
import threading
import time
from queue import Queue
from dataclasses import dataclass

@dataclass
class NetworkConfig:
    """网络配置"""
    host: str = 'localhost'  # 主机地址
    port: int = 8080  # 端口号
    buffer_size: int = 4096  # 缓冲区大小
    timeout: float = 1.0  # 超时时间(秒)
    reconnect_interval: float = 5.0  # 重连间隔(秒)
    max_retries: int = 3  # 最大重试次数

class NetworkManager:
    """网络管理器"""
    
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger('NetworkManager')
        self.config = NetworkConfig(**config.get('network', {}))
        
        # 网络状态
        self.connected = False
        self.socket = None
        self.stop_event = threading.Event()
        
        # 消息队列
        self.send_queue = Queue()
        self.receive_queue = Queue()
        
        # 消息处理器
        self.message_handlers: Dict[str, Callable] = {}
        self.handler_lock = threading.Lock()
        
        # 工作线程
        self.threads: Dict[str, threading.Thread] = {}
        
    def start(self):
        """启动网络管理器"""
        try:
            # 创建工作线程
            self.threads['receiver'] = threading.Thread(
                target=self._receive_loop,
                name="receiver"
            )
            self.threads['sender'] = threading.Thread(
                target=self._send_loop,
                name="sender"
            )
            self.threads['monitor'] = threading.Thread(
                target=self._monitor_loop,
                name="monitor"
            )
            
            # 启动线程
            self.stop_event.clear()
            for thread in self.threads.values():
                thread.start()
                
            self.logger.info("网络管理器启动")
            
        except Exception as e:
            self.logger.error(f"启动失败: {str(e)}")
            self.stop()
            
    def stop(self):
        """停止网络管理器"""
        try:
            # 停止线程
            self.stop_event.set()
            for thread in self.threads.values():
                thread.join()
                
            # 关闭连接
            if self.socket:
                self.socket.close()
                self.socket = None
                
            self.connected = False
            self.logger.info("网络管理器停止")
            
        except Exception as e:
            self.logger.error(f"停止失败: {str(e)}")
            
    def connect(self) -> bool:
        """建立连接"""
        try:
            # 创建套接字
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.config.timeout)
            
            # 连接服务器
            self.socket.connect((self.config.host, self.config.port))
            self.connected = True
            
            self.logger.info(f"已连接到 {self.config.host}:{self.config.port}")
            return True
            
        except Exception as e:
            self.logger.error(f"连接失败: {str(e)}")
            self.socket = None
            self.connected = False
            return False
            
    def send_message(self, message: Dict) -> bool:
        """发送消息
        
        Args:
            message: 消息字典
            
        Returns:
            是否发送成功
        """
        try:
            self.send_queue.put(message)
            return True
            
        except Exception as e:
            self.logger.error(f"发送消息失败: {str(e)}")
            return False
            
    def register_handler(self, message_type: str, handler: Callable):
        """注册消息处理器
        
        Args:
            message_type: 消息类型
            handler: 处理函数
        """
        with self.handler_lock:
            self.message_handlers[message_type] = handler
            
    def _receive_loop(self):
        """接收循环"""
        while not self.stop_event.is_set():
            try:
                if not self.connected:
                    time.sleep(0.1)
                    continue
                    
                # 接收数据
                data = self.socket.recv(self.config.buffer_size)
                if not data:
                    self.connected = False
                    continue
                    
                # 解析消息
                message = json.loads(data.decode())
                
                # 处理消息
                message_type = message.get('type')
                if message_type in self.message_handlers:
                    self.message_handlers[message_type](message)
                else:
                    self.receive_queue.put(message)
                    
            except socket.timeout:
                continue
            except Exception as e:
                self.logger.error(f"接收消息失败: {str(e)}")
                self.connected = False
                
    def _send_loop(self):
        """发送循环"""
        while not self.stop_event.is_set():
            try:
                if not self.connected:
                    time.sleep(0.1)
                    continue
                    
                # 获取消息
                message = self.send_queue.get(timeout=1.0)
                
                # 发送数据
                data = json.dumps(message).encode()
                self.socket.sendall(data)
                
            except socket.timeout:
                continue
            except Exception as e:
                self.logger.error(f"发送消息失败: {str(e)}")
                self.connected = False
                
    def _monitor_loop(self):
        """监控循环"""
        while not self.stop_event.is_set():
            try:
                if not self.connected:
                    # 重连
                    if self.connect():
                        continue
                        
                time.sleep(self.config.reconnect_interval)
                
            except Exception as e:
                self.logger.error(f"监控循环错误: {str(e)}")
                time.sleep(1.0) 