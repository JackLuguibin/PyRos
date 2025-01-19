from typing import Dict, Any
import threading
import time
import logging

class RobotStateManager:
    def __init__(self, logger: logging.Logger = None):
        self.logger = logger
        self._state = {
            'servos': {},      # 舵机状态
            'sensors': {},     # 传感器数据
            'attitude': {},    # 姿态数据
            'actions': {},     # 动作状态
            'system': {        # 系统状态
                'is_running': False,
                'error': None,
                'battery': 100,
                'temperature': 25
            }
        }
        self._lock = threading.Lock()
        
    def update_state(self, category: str, key: str, value: Any):
        """更新状态值"""
        with self._lock:
            if category in self._state:
                self._state[category][key] = value
                if self.logger:
                    self.logger.debug(f"状态更新: {category}.{key} = {value}")
                    
    def get_state(self, category: str, key: str = None) -> Any:
        """获取状态值"""
        with self._lock:
            if category in self._state:
                if key is None:
                    return self._state[category].copy()
                return self._state[category].get(key)
            return None
            
    def get_full_state(self) -> Dict:
        """获取完整状态"""
        with self._lock:
            return self._state.copy() 