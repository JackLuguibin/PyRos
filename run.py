#!/usr/bin/env python3
from typing import Dict, Optional
import argparse
import logging
import yaml
import signal
import sys
import time
from pathlib import Path

from robot.model import RobotDynamics
from robot.servos import ServoManager
from robot.sensors import SensorManager
from robot.simulation import RobotSimulator, RobotVisualizer
from robot.core.message_broker import MessageBroker

class RobotSystem:
    """机器人系统"""
    
    def __init__(self, config_path: str, log_level: str = 'INFO'):
        """初始化机器人系统
        
        Args:
            config_path: 配置文件路径
            log_level: 日志级别
        """
        # 配置日志
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('RobotSystem')
        
        # 加载配置
        self.config = self._load_config(config_path)
        
        # 创建消息代理
        self.message_broker = MessageBroker(
            config=self.config.get('message_broker', {})
        )
        
        # 创建机器人模型
        self.dynamics = RobotDynamics(
            config=self.config.get('model', {}),
            logger=self.logger
        )
        
        # 创建舵机管理器
        self.servo_manager = ServoManager(
            config=self.config.get('servos', {}),
            logger=self.logger
        )
        
        # 创建传感器管理器
        self.sensor_manager = SensorManager(
            config=self.config.get('sensors', {}),
            logger=self.logger
        )
        
        # 创建仿真器
        self.simulator = RobotSimulator(
            config=self.config.get('simulation', {}),
            robot_dynamics=self.dynamics,
            logger=self.logger
        )
        
        # 创建可视化器
        if self.config.get('visualization', {}).get('enable', True):
            self.visualizer = RobotVisualizer(
                config=self.config.get('visualization', {}),
                logger=self.logger
            )
        else:
            self.visualizer = None
            
        # 注册信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.running = False
        
    def start(self):
        """启动系统"""
        try:
            self.logger.info("正在启动机器人系统...")
            
            # 启动消息代理
            self.message_broker.start()
            
            # 启动舵机管理器
            self.servo_manager.start()
            
            # 启动传感器管理器
            self.sensor_manager.start()
            
            # 启动仿真器
            self.simulator.start()
            
            # 启动可视化器
            if self.visualizer:
                self.visualizer.start()
                
            self.running = True
            self.logger.info("机器人系统已启动")
            
            # 主循环
            while self.running:
                try:
                    # 更新机器人状态
                    joint_states = self.sensor_manager.get_joint_states()
                    if joint_states:
                        self.simulator.set_joint_states(joint_states)
                        
                    # 更新可视化
                    if self.visualizer:
                        link_transforms = {
                            name: self.simulator.get_link_transform(name)
                            for name in self.config.get('links', [])
                        }
                        self.visualizer.update_robot_state(link_transforms)
                        
                    time.sleep(0.01)  # 100Hz更新频率
                    
                except Exception as e:
                    self.logger.error(f"主循环错误: {str(e)}")
                    
        except Exception as e:
            self.logger.error(f"启动系统失败: {str(e)}")
            self.stop()
            
    def stop(self):
        """停止系统"""
        self.logger.info("正在停止机器人系统...")
        self.running = False
        
        # 停止各个组件
        if self.visualizer:
            self.visualizer.stop()
        self.simulator.stop()
        self.sensor_manager.stop()
        self.servo_manager.stop()
        self.message_broker.stop()
        
        self.logger.info("机器人系统已停止")
        
    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            self.logger.info(f"已加载配置文件: {config_path}")
            return config
            
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {str(e)}")
            sys.exit(1)
            
    def _signal_handler(self, signum, frame):
        """信号处理"""
        self.logger.info(f"收到信号: {signum}")
        self.stop()
        sys.exit(0)

def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='启动机器人系统')
    parser.add_argument(
        '-c', '--config',
        type=str,
        default='config/robot_config.yaml',
        help='配置文件路径'
    )
    parser.add_argument(
        '-l', '--log-level',
        type=str,
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='日志级别'
    )
    args = parser.parse_args()
    
    # 检查配置文件
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"错误: 配置文件不存在: {config_path}")
        sys.exit(1)
        
    # 创建并启动系统
    robot = RobotSystem(
        config_path=str(config_path),
        log_level=args.log_level
    )
    robot.start()

if __name__ == '__main__':
    main() 