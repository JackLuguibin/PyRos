#!/usr/bin/env python3
import argparse
import signal
import sys
import os
from robot.core.manager import RobotManager
from robot.network.rpc_server import RobotRPCServer

class RobotApplication:
    def __init__(self):
        self.robot = None
        self.rpc_server = None
        self._setup_signal_handlers()
        
    def _setup_signal_handlers(self):
        """设置信号处理器"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """处理退出信号"""
        print("\n正在关闭机器人系统...")
        self.shutdown()
        sys.exit(0)
        
    def initialize(self, config_path: str, host: str = "0.0.0.0", port: int = 8000):
        """初始化机器人系统"""
        try:
            # 创建并初始化机器人管理器
            self.robot = RobotManager()
            
            # 如果指定了配置文件，更新配置路径
            if config_path:
                self.robot.config_manager.config_path = config_path
                
            # 初始化机器人系统
            self.robot.initialize()
            
            # 创建并启动RPC服务器
            self.rpc_server = RobotRPCServer(self.robot, host, port)
            self.rpc_server.start()
            
            print(f"""
机器人系统已启动:
- RPC服务器地址: http://{host}:{port}
- 配置文件: {os.path.abspath(config_path)}
- 日志目录: {os.path.abspath('logs')}

按Ctrl+C退出...
            """)
            
        except Exception as e:
            print(f"初始化失败: {e}")
            self.shutdown()
            sys.exit(1)
            
    def shutdown(self):
        """关闭机器人系统"""
        if self.rpc_server:
            self.rpc_server.stop()
        if self.robot:
            self.robot.shutdown()
            
    def run_forever(self):
        """保持程序运行"""
        try:
            signal.pause()
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='机器人控制系统')
    
    parser.add_argument(
        '-c', '--config',
        default='config.yaml',
        help='配置文件路径 (默认: config.yaml)'
    )
    
    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='RPC服务器主机地址 (默认: 0.0.0.0)'
    )
    
    parser.add_argument(
        '-p', '--port',
        type=int,
        default=8000,
        help='RPC服务器端口 (默认: 8000)'
    )
    
    return parser.parse_args()

def main():
    # 解析命令行参数
    args = parse_arguments()
    
    # 创建并运行应用
    app = RobotApplication()
    app.initialize(
        config_path=args.config,
        host=args.host,
        port=args.port
    )
    app.run_forever()

if __name__ == "__main__":
    main() 