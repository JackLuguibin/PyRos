from typing import Dict, Any, Optional
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
import time

@dataclass
class SensorConfig:
    """传感器配置"""
    sample_rate: float = 100.0  # 采样率(Hz)
    timeout: float = 1.0  # 超时时间(秒)
    filter_window: int = 5  # 滤波窗口大小

class BaseSensor(ABC):
    """传感器基类"""
    
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        """初始化传感器
        
        Args:
            config: 传感器配置
            logger: 日志记录器
        """
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.config = SensorConfig(**config)
        self.last_read_time = 0.0
        self.is_connected = False
        
    @abstractmethod
    def connect(self) -> bool:
        """连接传感器"""
        pass
        
    @abstractmethod
    def disconnect(self):
        """断开连接"""
        pass
        
    @abstractmethod
    def read(self) -> Dict[str, Any]:
        """读取数据"""
        pass
        
    def read_safe(self) -> Optional[Dict[str, Any]]:
        """安全读取数据"""
        try:
            # 检查连接状态
            if not self.is_connected:
                if not self.connect():
                    return None
                    
            # 检查采样间隔
            current_time = time.time()
            if current_time - self.last_read_time < 1.0 / self.config.sample_rate:
                return None
                
            # 读取数据
            data = self.read()
            if data is not None:
                self.last_read_time = current_time
                
            return data
            
        except Exception as e:
            self.logger.error(f"读取数据失败: {str(e)}")
            return None
            
    def check_timeout(self) -> bool:
        """检查超时"""
        return time.time() - self.last_read_time > self.config.timeout 