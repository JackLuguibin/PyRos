from typing import Dict, Any, Optional
import time
import threading
from dataclasses import dataclass
from cachetools import TTLCache, LRUCache

@dataclass
class CacheConfig:
    """缓存配置"""
    type: str = 'ttl'  # 缓存类型(ttl/lru)
    max_size: int = 1000  # 最大缓存数量
    ttl: int = 300  # 缓存时间(秒)

class CacheManager:
    """缓存管理器"""
    
    def __init__(self, config: Dict):
        self.config = CacheConfig(**config)
        
        # 创建缓存
        if self.config.type == 'ttl':
            self.cache = TTLCache(
                maxsize=self.config.max_size,
                ttl=self.config.ttl
            )
        else:
            self.cache = LRUCache(maxsize=self.config.max_size)
            
        self.lock = threading.Lock()
        
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        with self.lock:
            return self.cache.get(key)
            
    def set(self, key: str, value: Any):
        """设置缓存"""
        with self.lock:
            self.cache[key] = value
            
    def delete(self, key: str):
        """删除缓存"""
        with self.lock:
            self.cache.pop(key, None)
            
    def clear(self):
        """清空缓存"""
        with self.lock:
            self.cache.clear() 