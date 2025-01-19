from robot.core.manager import RobotManager
from robot.network.rpc_server import RobotRPCServer
import signal
import sys

def signal_handler(signum, frame):
    """处理退出信号"""
    print("\n正在关闭系统...")
    if hasattr(signal_handler, "robot"):
        signal_handler.robot.shutdown()
    if hasattr(signal_handler, "rpc_server"):
        signal_handler.rpc_server.stop()
    sys.exit(0)

def main():
    # 创建机器人管理器
    robot = RobotManager()
    signal_handler.robot = robot
    
    # 初始化系统
    robot.initialize()
    
    # 创建并启动RPC服务器
    rpc_server = RobotRPCServer(robot)
    signal_handler.rpc_server = rpc_server
    rpc_server.start()
    
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 保持主程序运行
        print("机器人系统已启动，按Ctrl+C退出...")
        signal.pause()
    except KeyboardInterrupt:
        pass
    finally:
        # 确保正确关闭系统
        robot.shutdown()
        rpc_server.stop()

if __name__ == "__main__":
    main() 