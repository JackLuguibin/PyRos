from typing import Dict, List, Optional
import numpy as np
import time
import logging
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import seaborn as sns
from threading import Thread, Lock
import queue
from dataclasses import dataclass

@dataclass
class VisualizationData:
    """可视化数据"""
    timestamp: float
    metrics: Dict
    state: Dict
    control: Dict

class VisualizationMonitor:
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        """可视化监控器"""
        self.logger = logger or logging.getLogger('VisualizationMonitor')
        self.config = config
        
        # 数据缓存
        self.data_queue = queue.Queue(maxsize=1000)
        self.data_lock = Lock()
        self.data_history: List[VisualizationData] = []
        self.max_history = config.get('max_history', 1000)
        
        # 图表配置
        self.plot_config = {
            'metrics': {
                'mse': {'color': 'red', 'label': 'MSE'},
                'mae': {'color': 'blue', 'label': 'MAE'},
                'latency': {'color': 'green', 'label': 'Latency'}
            },
            'state': {
                'position': {'color': 'purple', 'label': 'Position'},
                'velocity': {'color': 'orange', 'label': 'Velocity'},
                'acceleration': {'color': 'brown', 'label': 'Acceleration'}
            },
            'control': {
                'output': {'color': 'black', 'label': 'Control Output'},
                'target': {'color': 'gray', 'label': 'Target'}
            }
        }
        
        # 添加更多图表类型
        self.plot_types = {
            'time_series': self._plot_time_series,
            'distribution': self._plot_distribution,
            'correlation': self._plot_correlation,
            'phase_space': self._plot_phase_space,
            'control_surface': self._plot_control_surface
        }
        
        # 交互控件
        self.interactive_controls = {
            'time_window': {'value': 100, 'min': 10, 'max': 1000},
            'update_interval': {'value': 100, 'min': 50, 'max': 1000},
            'plot_type': {'value': 'time_series', 'options': list(self.plot_types.keys())}
        }
        
        # 创建子图布局
        self.fig = plt.figure(figsize=(15, 10))
        gs = self.fig.add_gridspec(3, 2)
        self.axes = {
            'main': self.fig.add_subplot(gs[:2, :]),
            'metrics': self.fig.add_subplot(gs[2, 0]),
            'distribution': self.fig.add_subplot(gs[2, 1])
        }
        
        # 启动更新线程
        self.running = True
        self.update_thread = Thread(target=self._update_loop)
        self.update_thread.start()
        
        # 启动动画
        self.ani = FuncAnimation(
            self.fig,
            self._animate,
            interval=config.get('update_interval', 100),
            blit=True
        )
        
        # 添加交互控件
        self._setup_interactive_controls()
        
    def _setup_interactive_controls(self):
        """设置交互控件"""
        from matplotlib.widgets import Slider, Button, RadioButtons
        
        # 时间窗口滑块
        ax_time = plt.axes([0.1, 0.02, 0.3, 0.02])
        self.time_slider = Slider(
            ax_time, 'Time Window',
            self.interactive_controls['time_window']['min'],
            self.interactive_controls['time_window']['max'],
            valinit=self.interactive_controls['time_window']['value']
        )
        self.time_slider.on_changed(self._update_time_window)
        
        # 更新间隔滑块
        ax_interval = plt.axes([0.5, 0.02, 0.3, 0.02])
        self.interval_slider = Slider(
            ax_interval, 'Update Interval',
            self.interactive_controls['update_interval']['min'],
            self.interactive_controls['update_interval']['max'],
            valinit=self.interactive_controls['update_interval']['value']
        )
        self.interval_slider.on_changed(self._update_interval)
        
        # 图表类型选择器
        ax_radio = plt.axes([0.85, 0.1, 0.1, 0.2])
        self.plot_radio = RadioButtons(
            ax_radio,
            self.interactive_controls['plot_type']['options']
        )
        self.plot_radio.on_clicked(self._update_plot_type)
        
    def _plot_time_series(self, ax, data):
        """绘制时间序列"""
        ax.clear()
        timestamps = [d.timestamp for d in data]
        
        # 绘制多个指标
        for key, config in self.plot_config['metrics'].items():
            values = [d.metrics.get(key, 0) for d in data]
            ax.plot(timestamps, values,
                   color=config['color'],
                   label=config['label'])
            
        ax.set_title('Time Series Analysis')
        ax.legend()
        
    def _plot_distribution(self, ax, data):
        """绘制分布图"""
        ax.clear()
        
        # 提取所有指标数据
        metrics_data = {}
        for key in self.plot_config['metrics']:
            metrics_data[key] = [d.metrics.get(key, 0) for d in data]
            
        # 使用seaborn绘制分布
        for key, values in metrics_data.items():
            sns.kdeplot(data=values,
                       label=self.plot_config['metrics'][key]['label'],
                       ax=ax)
            
        ax.set_title('Metrics Distribution')
        ax.legend()
        
    def _plot_correlation(self, ax, data):
        """绘制相关性图"""
        ax.clear()
        
        # 构建相关性矩阵
        metrics_data = {}
        for key in self.plot_config['metrics']:
            metrics_data[key] = [d.metrics.get(key, 0) for d in data]
            
        corr_matrix = np.corrcoef(list(metrics_data.values()))
        
        # 使用seaborn绘制热图
        sns.heatmap(corr_matrix,
                   xticklabels=list(metrics_data.keys()),
                   yticklabels=list(metrics_data.keys()),
                   annot=True,
                   cmap='coolwarm',
                   ax=ax)
        
        ax.set_title('Metrics Correlation')
        
    def _plot_phase_space(self, ax, data):
        """绘制相空间图"""
        ax.clear()
        
        # 提取状态变量
        position = [d.state.get('position', 0) for d in data]
        velocity = [d.state.get('velocity', 0) for d in data]
        
        # 绘制相轨迹
        ax.plot(position, velocity, 'b-', alpha=0.5)
        ax.scatter(position[-1], velocity[-1], c='r', marker='o')
        
        ax.set_xlabel('Position')
        ax.set_ylabel('Velocity')
        ax.set_title('Phase Space')
        
    def _plot_control_surface(self, ax, data):
        """绘制控制曲面"""
        ax.clear()
        
        # 提取控制数据
        error = np.linspace(-1, 1, 20)
        error_rate = np.linspace(-1, 1, 20)
        X, Y = np.meshgrid(error, error_rate)
        
        # 计算控制输出
        Z = np.zeros_like(X)
        for i in range(X.shape[0]):
            for j in range(X.shape[1]):
                Z[i,j] = self._compute_control_output(X[i,j], Y[i,j])
                
        # 绘制3D曲面
        ax.plot_surface(X, Y, Z, cmap='viridis')
        ax.set_xlabel('Error')
        ax.set_ylabel('Error Rate')
        ax.set_zlabel('Control Output')
        ax.set_title('Control Surface')
        
    def _compute_control_output(self, error: float, error_rate: float) -> float:
        """计算控制输出（示例）"""
        kp = 1.0
        kd = 0.1
        return kp * error + kd * error_rate
        
    def _update_time_window(self, value):
        """更新时间窗口"""
        self.interactive_controls['time_window']['value'] = int(value)
        
    def _update_interval(self, value):
        """更新更新间隔"""
        self.interactive_controls['update_interval']['value'] = int(value)
        self.ani.event_source.interval = int(value)
        
    def _update_plot_type(self, label):
        """更新图表类型"""
        self.interactive_controls['plot_type']['value'] = label
        
    def update_data(self, metrics: Dict, state: Dict, control: Dict):
        """更新数据"""
        data = VisualizationData(
            timestamp=time.time(),
            metrics=metrics,
            state=state,
            control=control
        )
        
        try:
            self.data_queue.put_nowait(data)
        except queue.Full:
            self.data_queue.get()  # 移除最旧的数据
            self.data_queue.put(data)
            
    def _update_loop(self):
        """更新循环"""
        while self.running:
            try:
                data = self.data_queue.get(timeout=1.0)
                with self.data_lock:
                    self.data_history.append(data)
                    if len(self.data_history) > self.max_history:
                        self.data_history.pop(0)
            except queue.Empty:
                continue
                
    def _animate(self, frame):
        """动画更新"""
        with self.data_lock:
            if not self.data_history:
                return []
                
            # 获取时间窗口数据
            window_size = self.interactive_controls['time_window']['value']
            data = self.data_history[-window_size:]
            
            # 根据选择的图表类型更新
            plot_type = self.interactive_controls['plot_type']['value']
            plot_func = self.plot_types[plot_type]
            
            # 更新主图
            plot_func(self.axes['main'], data)
            
            # 更新指标图
            self._plot_metrics(self.axes['metrics'], data)
            
            # 更新分布图
            self._plot_distribution(self.axes['distribution'], data)
            
        # 调整布局
        plt.tight_layout()
        
        return self.axes.values()
        
    def show(self):
        """显示图表"""
        plt.show()
        
    def __del__(self):
        """清理资源"""
        self.running = False
        if hasattr(self, 'update_thread'):
            self.update_thread.join() 