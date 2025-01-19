from typing import Dict, List, Optional
import logging
import random
import time
from dataclasses import dataclass
from threading import Lock

@dataclass
class ServerNode:
    """服务器节点"""
    host: str  # 主机地址
    port: int  # 端口号
    weight: int = 1  # 权重
    active: bool = True  # 是否活跃
    last_check: float = 0.0  # 最后检查时间
    fail_count: int = 0  # 失败次数

class LoadBalancer:
    """负载均衡器"""
    
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger('LoadBalancer')
        self.config = config
        
        # 服务器节点
        self.nodes: List[ServerNode] = []
        self.node_lock = Lock()
        
        # 负载均衡参数
        self.check_interval = config.get('check_interval', 30)  # 检查间隔(秒)
        self.fail_timeout = config.get('fail_timeout', 30)  # 失败超时(秒)
        self.max_fails = config.get('max_fails', 3)  # 最大失败次数
        
        # 初始化节点
        self._init_nodes(config.get('nodes', []))
        
    def get_server(self) -> Optional[ServerNode]:
        """获取服务器节点(轮询算法)"""
        with self.node_lock:
            active_nodes = [
                node for node in self.nodes
                if node.active
            ]
            if not active_nodes:
                return None
                
            # 按权重选择节点
            total_weight = sum(node.weight for node in active_nodes)
            if total_weight <= 0:
                return random.choice(active_nodes)
                
            r = random.uniform(0, total_weight)
            for node in active_nodes:
                r -= node.weight
                if r <= 0:
                    return node
                    
            return active_nodes[-1]
            
    def mark_down(self, node: ServerNode):
        """标记节点故障"""
        with self.node_lock:
            node.fail_count += 1
            node.last_check = time.time()
            
            if node.fail_count >= self.max_fails:
                node.active = False
                self.logger.warning(f"节点已下线: {node.host}:{node.port}")
                
    def check_nodes(self):
        """检查节点状态"""
        current_time = time.time()
        
        with self.node_lock:
            for node in self.nodes:
                # 跳过活跃节点
                if node.active:
                    continue
                    
                # 检查是否可以重试
                if current_time - node.last_check > self.fail_timeout:
                    node.active = True
                    node.fail_count = 0
                    self.logger.info(f"节点已恢复: {node.host}:{node.port}")
                    
    def _init_nodes(self, node_configs: List[Dict]):
        """初始化节点"""
        for config in node_configs:
            node = ServerNode(
                host=config['host'],
                port=config['port'],
                weight=config.get('weight', 1)
            )
            self.nodes.append(node) 