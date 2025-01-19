from abc import ABC, abstractmethod

class SensorBase(ABC):
    def __init__(self, pin: int):
        self.pin = pin
        self._setup()
        
    @abstractmethod
    def _setup(self):
        """初始化传感器"""
        pass
        
    @abstractmethod
    def read(self):
        """读取传感器数据"""
        pass
        
    @abstractmethod
    def cleanup(self):
        """清理资源"""
        pass 