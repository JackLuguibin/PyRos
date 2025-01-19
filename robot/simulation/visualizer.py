from typing import Dict, List, Optional, Tuple
import numpy as np
from dataclasses import dataclass
import logging
import time
import threading
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from ..core.transform import Transform

@dataclass
class VisualizerConfig:
    """可视化配置"""
    update_rate: float = 30.0  # 更新频率(Hz)
    window_size: Tuple[int, int] = (800, 600)  # 窗口大小
    background_color: str = 'white'  # 背景颜色
    link_color: str = 'blue'  # 连杆颜色
    joint_color: str = 'red'  # 关节颜色

class RobotVisualizer:
    """机器人可视化器"""
    
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        """初始化可视化器
        
        Args:
            config: 可视化配置
            logger: 日志记录器
        """
        self.logger = logger or logging.getLogger('RobotVisualizer')
        self.config = VisualizerConfig(**config)
        
        # 可视化状态
        self.fig = None
        self.ax = None
        self.links = {}
        self.joints = {}
        
        # 更新线程
        self.running = False
        self.update_thread = None
        self.vis_lock = threading.Lock()
        
        # 初始化图形
        self._init_figure()
        
    def start(self):
        """启动可视化"""
        if self.running:
            return
            
        self.running = True
        self.update_thread = threading.Thread(
            target=self._update_loop,
            daemon=True
        )
        self.update_thread.start()
        plt.show(block=False)
        self.logger.info("可视化器已启动")
        
    def stop(self):
        """停止可视化"""
        self.running = False
        if self.update_thread:
            self.update_thread.join()
        plt.close(self.fig)
        self.logger.info("可视化器已停止")
        
    def update_robot_state(self, link_transforms: Dict[str, Transform]):
        """更新机器人状态
        
        Args:
            link_transforms: 连杆变换{name: transform}
        """
        with self.vis_lock:
            for name, transform in link_transforms.items():
                if name in self.links:
                    self._update_link(name, transform)
                    
    def _init_figure(self):
        """初始化图形"""
        try:
            self.fig = plt.figure(figsize=(
                self.config.window_size[0]/100,
                self.config.window_size[1]/100
            ))
            self.ax = self.fig.add_subplot(111, projection='3d')
            
            # 设置坐标轴
            self.ax.set_xlabel('X')
            self.ax.set_ylabel('Y')
            self.ax.set_zlabel('Z')
            
            # 设置视角
            self.ax.view_init(elev=30, azim=45)
            
            # 设置背景
            self.ax.set_facecolor(self.config.background_color)
            
        except Exception as e:
            self.logger.error(f"初始化图形失败: {str(e)}")
            
    def _update_loop(self):
        """更新循环"""
        dt = 1.0 / self.config.update_rate
        
        while self.running:
            try:
                start_time = time.time()
                
                # 更新图形
                with self.vis_lock:
                    self.fig.canvas.draw()
                    self.fig.canvas.flush_events()
                    
                # 等待下一个周期
                elapsed = time.time() - start_time
                if elapsed < dt:
                    time.sleep(dt - elapsed)
                    
            except Exception as e:
                self.logger.error(f"更新循环错误: {str(e)}")
                
    def _update_link(self, name: str, transform: Transform):
        """更新连杆显示"""
        try:
            # 获取连杆端点
            start = transform.translation
            end = transform.apply(np.array([0.1, 0, 0]))  # 假设连杆长0.1m
            
            # 更新或创建连杆线段
            if name in self.links:
                line = self.links[name]
                line.set_data([start[0], end[0]], [start[1], end[1]])
                line.set_3d_properties([start[2], end[2]])
            else:
                line = self.ax.plot(
                    [start[0], end[0]],
                    [start[1], end[1]],
                    [start[2], end[2]],
                    color=self.config.link_color
                )[0]
                self.links[name] = line
                
        except Exception as e:
            self.logger.error(f"更新连杆显示失败: {str(e)}") 