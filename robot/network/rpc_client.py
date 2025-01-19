from typing import Dict, Any, Optional
import logging
import socket
import json
import uuid
import time
import threading
from .protocol import Message, CommandMessage, StateMessage, ErrorMessage
from .heartbeat import HeartbeatMonitor

class RPCClient:
    """RPC客户端"""
    
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger('RPCClient')
        self.config = config
        
        # 客户端配置
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 8081)
        self.timeout = config.get('timeout', 5.0)
        self.retry_interval = config.get('retry_interval', 1.0)
        self.max_retries = config.get('max_retries', 3)
        
        # 连接状态
        self.socket = None
        self.connected = False
        
        # 心跳监控
        self.heartbeat = HeartbeatMonitor(
            config.get('heartbeat', {}),
            on_timeout=self._handle_timeout
        )
        
    def connect(self) -> bool:
        """连接服务器"""
        try:
            # 创建套接字
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            
            # 连接服务器
            self.socket.connect((self.host, self.port))
            self.connected = True
            
            self.logger.info(f"已连接到 {self.host}:{self.port}")
            
            # 启动心跳
            self.heartbeat.start()
            # 启动心跳发送线程
            self._start_heartbeat()
            return True
            
        except Exception as e:
            self.logger.error(f"连接失败: {str(e)}")
            self.socket = None
            self.connected = False
            return False
            
    def disconnect(self):
        """断开连接"""
        if self.socket:
            self.socket.close()
            self.socket = None
        self.connected = False
        
        # 停止心跳
        self.heartbeat.stop()
        
    def _start_heartbeat(self):
        """启动心跳发送"""
        def send_heartbeat():
            while self.connected:
                try:
                    self.call('heartbeat')
                    time.sleep(self.heartbeat.config.interval)
                except Exception:
                    break
                    
        thread = threading.Thread(target=send_heartbeat, daemon=True)
        thread.start()
        
    def _handle_timeout(self):
        """处理心跳超时"""
        self.logger.warning("心跳超时，断开连接")
        self.disconnect()
        
    def call(self, method: str, params: Dict = None) -> Any:
        """调用远程方法
        
        Args:
            method: 方法名
            params: 参数字典
            
        Returns:
            调用结果
        """
        if not self.connected and not self.connect():
            raise ConnectionError("未连接到服务器")
            
        # 生成请求ID
        request_id = str(uuid.uuid4())
        
        # 构造请求
        request = {
            'method': method,
            'params': params or {},
            'id': request_id
        }
        
        # 发送请求
        retries = 0
        while retries < self.max_retries:
            try:
                # 发送数据
                data = json.dumps(request).encode()
                self.socket.sendall(data)
                
                # 接收响应
                response_data = self.socket.recv(4096)
                if not response_data:
                    raise ConnectionError("连接已断开")
                    
                # 解析响应
                response = json.loads(response_data.decode())
                
                # 检查错误
                if response.get('error'):
                    raise RuntimeError(response['error'])
                    
                return response.get('result')
                
            except Exception as e:
                self.logger.error(f"调用失败: {str(e)}")
                self.disconnect()
                
                retries += 1
                if retries < self.max_retries:
                    time.sleep(self.retry_interval)
                    if not self.connect():
                        continue
                        
        raise RuntimeError(f"调用失败，已重试 {self.max_retries} 次")
        
    def call_async(self, method: str, params: Dict = None) -> str:
        """异步调用远程方法
        
        Args:
            method: 方法名
            params: 参数字典
            
        Returns:
            任务ID
        """
        result = self.call(method, params)
        return result.get('task_id')
        
    def get_task_result(self, task_id: str, timeout: float = None) -> Any:
        """获取任务结果
        
        Args:
            task_id: 任务ID
            timeout: 等待超时时间
            
        Returns:
            任务结果
        """
        result = self.call('get_task_result', {'task_id': task_id})
        if not result:
            return None
            
        if not result.get('success'):
            raise RuntimeError(result.get('error'))
            
        return result.get('result') 