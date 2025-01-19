from typing import Dict, Optional, List
import logging
import threading
import time
from queue import Queue, Empty
from dataclasses import dataclass
import socket

@dataclass
class PoolConfig:
    """连接池配置"""
    max_size: int = 10  # 最大连接数
    min_size: int = 2   # 最小连接数
    timeout: float = 30.0  # 连接超时时间
    max_idle: int = 300  # 最大空闲时间(秒)
    max_lifetime: int = 3600  # 最大生存时间(秒)

class Connection:
    """连接包装器"""
    def __init__(self, socket: socket.socket):
        self.socket = socket
        self.created_at = time.time()
        self.last_used_at = time.time()
        self.in_use = False
        
    def is_expired(self, max_lifetime: int) -> bool:
        """检查是否过期"""
        return time.time() - self.created_at > max_lifetime
        
    def is_idle(self, max_idle: int) -> bool:
        """检查是否空闲"""
        return not self.in_use and time.time() - self.last_used_at > max_idle

class ConnectionPool:
    """连接池"""
    
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger('ConnectionPool')
        self.config = PoolConfig(**config)
        
        self.connections: List[Connection] = []
        self.available = Queue()
        self.lock = threading.Lock()
        
        # 初始化连接
        self._initialize_pool()
        
        # 启动维护线程
        self.maintenance_thread = threading.Thread(
            target=self._maintenance_loop,
            daemon=True
        )
        self.maintenance_thread.start()
        
    def get_connection(self, timeout: float = None) -> Optional[Connection]:
        """获取连接"""
        try:
            # 尝试获取可用连接
            conn = self.available.get(timeout=timeout or self.config.timeout)
            conn.in_use = True
            conn.last_used_at = time.time()
            return conn
            
        except Empty:
            # 创建新连接
            with self.lock:
                if len(self.connections) < self.config.max_size:
                    conn = self._create_connection()
                    if conn:
                        conn.in_use = True
                        self.connections.append(conn)
                        return conn
            return None
            
    def release_connection(self, conn: Connection):
        """释放连接"""
        conn.in_use = False
        conn.last_used_at = time.time()
        self.available.put(conn)
        
    def close(self):
        """关闭连接池"""
        with self.lock:
            for conn in self.connections:
                try:
                    conn.socket.close()
                except Exception:
                    pass
            self.connections.clear()
            while not self.available.empty():
                self.available.get_nowait()
                
    def _initialize_pool(self):
        """初始化连接池"""
        for _ in range(self.config.min_size):
            conn = self._create_connection()
            if conn:
                self.connections.append(conn)
                self.available.put(conn)
                
    def _create_connection(self) -> Optional[Connection]:
        """创建新连接"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            return Connection(sock)
        except Exception as e:
            self.logger.error(f"创建连接失败: {str(e)}")
            return None
            
    def _maintenance_loop(self):
        """维护循环"""
        while True:
            try:
                time.sleep(60)  # 每分钟检查一次
                
                with self.lock:
                    # 移除过期连接
                    self.connections = [
                        conn for conn in self.connections
                        if not conn.is_expired(self.config.max_lifetime)
                    ]
                    
                    # 关闭空闲连接
                    idle_conns = [
                        conn for conn in self.connections
                        if conn.is_idle(self.config.max_idle)
                    ]
                    for conn in idle_conns:
                        self.connections.remove(conn)
                        try:
                            conn.socket.close()
                        except Exception:
                            pass
                            
                    # 补充连接
                    current_size = len(self.connections)
                    if current_size < self.config.min_size:
                        for _ in range(self.config.min_size - current_size):
                            conn = self._create_connection()
                            if conn:
                                self.connections.append(conn)
                                self.available.put(conn)
                                
            except Exception as e:
                self.logger.error(f"维护循环错误: {str(e)}") 