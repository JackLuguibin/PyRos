from typing import Dict, Optional, Callable, List
import logging
import time
from threading import Lock, Event
from queue import Queue, Empty
from collections import defaultdict

class MessageBroker:
    """消息代理
    
    负责系统内部组件间的消息传递和事件分发
    """
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger('MessageBroker')
        self.config = config
        
        # 消息队列
        self.message_queues: Dict[str, Queue] = defaultdict(
            lambda: Queue(maxsize=config.get('queue_size', 1000))
        )
        
        # 消息处理器
        self.handlers: Dict[str, List[Callable]] = defaultdict(list)
        self.handler_lock = Lock()
        
        # 消息统计
        self.message_stats = {
            'published': 0,
            'delivered': 0,
            'dropped': 0,
            'latency': []
        }
        self.stats_lock = Lock()
        
        # 运行状态
        self.running = Event()
        self.max_latency = config.get('max_latency', 0.1)  # 100ms
        self.cleanup_interval = config.get('cleanup_interval', 60)  # 60s
        self.last_cleanup = time.time()
        
    def initialize(self):
        """初始化消息代理"""
        self.running.set()
        self.logger.info("消息代理初始化完成")
        
    def stop(self):
        """停止消息代理"""
        self.running.clear()
        self._cleanup_queues()
        self.logger.info("消息代理已停止")
        
    def register_handler(self, topic: str, handler: Callable):
        """注册消息处理器"""
        with self.handler_lock:
            if handler not in self.handlers[topic]:
                self.handlers[topic].append(handler)
                self.logger.debug(f"注册处理器: {topic} -> {handler.__name__}")
                
    def unregister_handler(self, topic: str, handler: Callable):
        """注销消息处理器"""
        with self.handler_lock:
            if handler in self.handlers[topic]:
                self.handlers[topic].remove(handler)
                self.logger.debug(f"注销处理器: {topic} -> {handler.__name__}")
                
    def publish(self, topic: str, message: Dict) -> bool:
        """发布消息"""
        if not self.running.is_set():
            return False
            
        try:
            # 添加时间戳
            message['timestamp'] = time.time()
            
            # 放入队列
            queue = self.message_queues[topic]
            if queue.full():
                # 队列满时丢弃最旧的消息
                try:
                    queue.get_nowait()
                    with self.stats_lock:
                        self.message_stats['dropped'] += 1
                except Empty:
                    pass
                    
            queue.put_nowait(message)
            
            # 更新统计
            with self.stats_lock:
                self.message_stats['published'] += 1
                
            # 触发处理器
            self._trigger_handlers(topic, message)
            
            return True
            
        except Exception as e:
            self.logger.error(f"发布消息失败: {str(e)}")
            return False
            
    def get_message(self, topic: str, timeout: float = 0.0) -> Optional[Dict]:
        """获取消息"""
        if not self.running.is_set():
            return None
            
        try:
            queue = self.message_queues[topic]
            message = queue.get(timeout=timeout) if timeout > 0 else queue.get_nowait()
            
            # 检查消息延迟
            latency = time.time() - message['timestamp']
            if latency > self.max_latency:
                self.logger.warning(f"消息延迟过高: {latency:.3f}s > {self.max_latency}s")
                
            # 更新统计
            with self.stats_lock:
                self.message_stats['delivered'] += 1
                self.message_stats['latency'].append(latency)
                
            # 定期清理
            current_time = time.time()
            if current_time - self.last_cleanup > self.cleanup_interval:
                self._cleanup_queues()
                self.last_cleanup = current_time
                
            return message
            
        except Empty:
            return None
        except Exception as e:
            self.logger.error(f"获取消息失败: {str(e)}")
            return None
            
    def _trigger_handlers(self, topic: str, message: Dict):
        """触发消息处理器"""
        with self.handler_lock:
            handlers = self.handlers[topic].copy()
            
        for handler in handlers:
            try:
                handler(message)
            except Exception as e:
                self.logger.error(f"处理器错误: {str(e)}")
                
    def _cleanup_queues(self):
        """清理消息队列"""
        try:
            # 清理过期消息
            current_time = time.time()
            for topic, queue in self.message_queues.items():
                cleaned = 0
                while not queue.empty():
                    message = queue.get_nowait()
                    if current_time - message['timestamp'] <= self.max_latency:
                        queue.put_nowait(message)
                        break
                    cleaned += 1
                    
                if cleaned > 0:
                    self.logger.info(f"清理过期消息: {topic} -> {cleaned}条")
                    
            # 清理统计数据
            with self.stats_lock:
                if len(self.message_stats['latency']) > 1000:
                    self.message_stats['latency'] = \
                        self.message_stats['latency'][-1000:]
                        
        except Exception as e:
            self.logger.error(f"清理队列失败: {str(e)}")
            
    def get_stats(self) -> Dict:
        """获取统计信息"""
        with self.stats_lock:
            stats = self.message_stats.copy()
            if stats['latency']:
                stats['avg_latency'] = sum(stats['latency']) / len(stats['latency'])
                stats['max_latency'] = max(stats['latency'])
            else:
                stats['avg_latency'] = 0
                stats['max_latency'] = 0
            return stats 