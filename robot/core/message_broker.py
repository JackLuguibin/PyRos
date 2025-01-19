from typing import Dict, Callable, List
import threading
import queue
import logging
import time

class MessageBroker:
    def __init__(self, logger: logging.Logger = None):
        self.logger = logger
        self.topics: Dict[str, List[Callable]] = {}
        self._lock = threading.Lock()
        self.message_queue = queue.Queue()
        self._running = True
        self._worker = threading.Thread(target=self._process_messages)
        self._worker.daemon = True
        self._worker.start()
        
    def publish(self, topic: str, message: any):
        """发布消息到指定主题"""
        self.message_queue.put((topic, message))
        
    def subscribe(self, topic: str, callback: Callable):
        """订阅主题"""
        with self._lock:
            if topic not in self.topics:
                self.topics[topic] = []
            self.topics[topic].append(callback)
            if self.logger:
                self.logger.debug(f"订阅主题: {topic}")
                
    def unsubscribe(self, topic: str, callback: Callable):
        """取消订阅"""
        with self._lock:
            if topic in self.topics and callback in self.topics[topic]:
                self.topics[topic].remove(callback)
                if self.logger:
                    self.logger.debug(f"取消订阅: {topic}")
                    
    def _process_messages(self):
        """消息处理循环"""
        while self._running:
            try:
                topic, message = self.message_queue.get(timeout=1.0)
                with self._lock:
                    if topic in self.topics:
                        for callback in self.topics[topic]:
                            try:
                                callback(message)
                            except Exception as e:
                                if self.logger:
                                    self.logger.error(f"处理消息失败: {e}")
            except queue.Empty:
                continue
                
    def cleanup(self):
        """清理资源"""
        self._running = False
        if self._worker.is_alive():
            self._worker.join() 