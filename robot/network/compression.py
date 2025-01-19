from typing import Dict, Optional
import zlib
import lz4.frame
import snappy
from dataclasses import dataclass
from enum import Enum

class CompressionType(Enum):
    """压缩类型"""
    NONE = 'none'      # 不压缩
    ZLIB = 'zlib'      # ZLIB压缩
    LZ4 = 'lz4'        # LZ4压缩
    SNAPPY = 'snappy'  # Snappy压缩

@dataclass
class CompressionConfig:
    """压缩配置"""
    type: CompressionType = CompressionType.NONE  # 压缩类型
    level: int = 6  # 压缩级别(仅ZLIB)
    min_size: int = 1024  # 最小压缩大小(字节)

class CompressionManager:
    """压缩管理器"""
    
    def __init__(self, config: Dict):
        self.config = CompressionConfig(**config)
        
    def compress(self, data: bytes) -> bytes:
        """压缩数据"""
        if len(data) < self.config.min_size:
            return data
            
        try:
            if self.config.type == CompressionType.ZLIB:
                return zlib.compress(data, self.config.level)
            elif self.config.type == CompressionType.LZ4:
                return lz4.frame.compress(data)
            elif self.config.type == CompressionType.SNAPPY:
                return snappy.compress(data)
            else:
                return data
                
        except Exception:
            return data
            
    def decompress(self, data: bytes) -> bytes:
        """解压数据"""
        try:
            if self.config.type == CompressionType.ZLIB:
                return zlib.decompress(data)
            elif self.config.type == CompressionType.LZ4:
                return lz4.frame.decompress(data)
            elif self.config.type == CompressionType.SNAPPY:
                return snappy.decompress(data)
            else:
                return data
                
        except Exception:
            return data 