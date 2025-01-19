from typing import Dict, Any
from dataclasses import dataclass
import json
import time

@dataclass
class Message:
    """消息基类"""
    type: str  # 消息类型
    timestamp: float = None  # 时间戳
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
            
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'type': self.type,
            'timestamp': self.timestamp
        }
        
    def to_json(self) -> str:
        """转换为JSON"""
        return json.dumps(self.to_dict())
        
    @classmethod
    def from_dict(cls, data: Dict) -> 'Message':
        """从字典创建"""
        return cls(**data)
        
    @classmethod
    def from_json(cls, data: str) -> 'Message':
        """从JSON创建"""
        return cls.from_dict(json.loads(data))

@dataclass
class CommandMessage(Message):
    """命令消息"""
    command: str  # 命令
    params: Dict = None  # 参数
    
    def to_dict(self) -> Dict:
        data = super().to_dict()
        data.update({
            'command': self.command,
            'params': self.params or {}
        })
        return data

@dataclass
class StateMessage(Message):
    """状态消息"""
    state: Dict  # 状态数据
    
    def to_dict(self) -> Dict:
        data = super().to_dict()
        data['state'] = self.state
        return data

@dataclass
class ErrorMessage(Message):
    """错误消息"""
    error: str  # 错误信息
    code: int = None  # 错误代码
    
    def to_dict(self) -> Dict:
        data = super().to_dict()
        data.update({
            'error': self.error,
            'code': self.code
        })
        return data 