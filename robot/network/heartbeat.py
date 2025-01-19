from typing import Dict, Optional, Callable
import logging
import threading
import time
from dataclasses import dataclass

@dataclass
class HeartbeatConfig:
    """心跳配置"""
    interval: float = 5.0  # 心跳间隔(秒)
    timeout: float = 15.0  # 超时时间(秒)
    max_missed: int = 3  # 最大丢失次数

class HeartbeatMonitor:
    """心跳监控器"""
    
    def __init__(self, config: Dict, on_timeout: Callable = None,
                 logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger('HeartbeatMonitor')
        self.config = HeartbeatConfig(**config)
        self.on_timeout = on_timeout
        
        self.last_beat = time.time()
        self.missed_count = 0
        self.running = False
        self.monitor_thread = None
        
    def start(self):
        """启动监控"""
        self.running = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True
        )
        self.monitor_thread.start()
        self.logger.info("心跳监控启动")
        
    def stop(self):
        """停止监控"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join()
        self.logger.info("心跳监控停止")
        
    def beat(self):
        """接收心跳"""
        self.last_beat = time.time()
        self.missed_count = 0
        
    def _monitor_loop(self):
        """监控循环"""
        while self.running:
            try:
                time.sleep(self.config.interval)
                
                # 检查超时
                if time.time() - self.last_beat > self.config.timeout:
                    self.missed_count += 1
                    self.logger.warning(
                        f"心跳超时，已丢失 {self.missed_count} 次"
                    )
                    
                    # 触发超时回调
                    if (self.missed_count >= self.config.max_missed and 
                        self.on_timeout):
                        self.on_timeout()
                        
            except Exception as e:
                self.logger.error(f"心跳监控错误: {str(e)}") 