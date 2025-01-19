from typing import Dict, List, Optional
import numpy as np
import time
import logging
from dataclasses import dataclass
from threading import Thread, Lock

@dataclass
class PerformanceMetrics:
    """性能指标"""
    mse: float = 0.0
    mae: float = 0.0
    latency: float = 0.0
    throughput: float = 0.0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    network_usage: float = 0.0

class PerformanceMonitor:
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        """性能监控器"""
        self.logger = logger or logging.getLogger('PerformanceMonitor')
        self.config = config
        
        # 性能指标
        self.metrics = PerformanceMetrics()
        self.metrics_history: List[PerformanceMetrics] = []
        self.max_history = config.get('max_history', 1000)
        
        # 监控配置
        self.monitor_interval = config.get('monitor_interval', 1.0)
        self.alert_thresholds = config.get('alert_thresholds', {
            'mse': 10.0,
            'latency': 0.1,
            'cpu_usage': 80.0,
            'memory_usage': 80.0,
            'network_usage': 80.0
        })
        
        # 监控状态
        self.running = True
        self.metrics_lock = Lock()
        
        # 启动监控线程
        self.monitor_thread = Thread(target=self._monitor_loop)
        self.monitor_thread.start()
        
    def update_metrics(self, metrics: Dict):
        """更新性能指标"""
        with self.metrics_lock:
            if 'mse' in metrics:
                self.metrics.mse = metrics['mse']
            if 'mae' in metrics:
                self.metrics.mae = metrics['mae']
            if 'latency' in metrics:
                self.metrics.latency = metrics['latency']
                
        # 保存历史记录
        self.metrics_history.append(copy.deepcopy(self.metrics))
        if len(self.metrics_history) > self.max_history:
            self.metrics_history.pop(0)
            
    def get_metrics(self) -> Dict:
        """获取性能指标"""
        with self.metrics_lock:
            return {
                'current': dataclasses.asdict(self.metrics),
                'average': self._compute_average_metrics(),
                'alerts': self._check_alerts()
            }
            
    def _monitor_loop(self):
        """监控循环"""
        while self.running:
            try:
                # 更新系统指标
                self._update_system_metrics()
                
                # 检查告警
                alerts = self._check_alerts()
                if alerts:
                    self._handle_alerts(alerts)
                    
                time.sleep(self.monitor_interval)
                
            except Exception as e:
                self.logger.error(f"监控错误: {str(e)}")
                
    def _update_system_metrics(self):
        """更新系统指标"""
        with self.metrics_lock:
            # CPU使用率
            self.metrics.cpu_usage = psutil.cpu_percent()
            
            # 内存使用率
            memory = psutil.virtual_memory()
            self.metrics.memory_usage = memory.percent
            
            # 网络使用率
            network = psutil.net_io_counters()
            self.metrics.network_usage = (network.bytes_sent + network.bytes_recv) / 1024 / 1024
            
    def _compute_average_metrics(self) -> Dict:
        """计算平均指标"""
        if not self.metrics_history:
            return {}
            
        metrics_dict = [dataclasses.asdict(m) for m in self.metrics_history]
        avg_metrics = {}
        
        for key in metrics_dict[0]:
            values = [m[key] for m in metrics_dict]
            avg_metrics[key] = np.mean(values)
            
        return avg_metrics
        
    def _check_alerts(self) -> List[Dict]:
        """检查告警"""
        alerts = []
        
        with self.metrics_lock:
            metrics_dict = dataclasses.asdict(self.metrics)
            
            for metric, threshold in self.alert_thresholds.items():
                if metric in metrics_dict:
                    value = metrics_dict[metric]
                    if value > threshold:
                        alerts.append({
                            'metric': metric,
                            'value': value,
                            'threshold': threshold,
                            'timestamp': time.time()
                        })
                        
        return alerts
        
    def _handle_alerts(self, alerts: List[Dict]):
        """处理告警"""
        for alert in alerts:
            self.logger.warning(
                f"性能告警: {alert['metric']} = {alert['value']:.2f} "
                f"(阈值: {alert['threshold']:.2f})"
            )
            
    def __del__(self):
        """清理资源"""
        self.running = False
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join() 