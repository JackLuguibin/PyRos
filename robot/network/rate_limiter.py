from typing import Dict, Optional
import time
import threading
from dataclasses import dataclass

@dataclass
class RateLimitConfig:
    """流量限制配置"""
    max_requests: int = 100  # 最大请求数/秒
    window_size: int = 60  # 时间窗口(秒)
    burst_size: int = 10  # 突发大小

class TokenBucket:
    """令牌桶"""
    def __init__(self, rate: float, capacity: int):
        self.rate = rate  # 令牌生成速率
        self.capacity = capacity  # 桶容量
        self.tokens = capacity  # 当前令牌数
        self.last_time = time.time()
        self.lock = threading.Lock()
        
    def consume(self, tokens: int = 1) -> bool:
        """消费令牌"""
        with self.lock:
            now = time.time()
            # 添加令牌
            elapsed = now - self.last_time
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.rate
            )
            self.last_time = now
            
            # 消费令牌
            if tokens <= self.tokens:
                self.tokens -= tokens
                return True
            return False

class RateLimiter:
    """流量限制器"""
    
    def __init__(self, config: Dict):
        self.config = RateLimitConfig(**config)
        
        # 创建令牌桶
        self.bucket = TokenBucket(
            rate=self.config.max_requests / self.config.window_size,
            capacity=self.config.burst_size
        )
        
    def allow(self) -> bool:
        """检查是否允许请求"""
        return self.bucket.consume() 