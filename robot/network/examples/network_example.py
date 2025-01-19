import time
from ..network_manager import NetworkManager
from ..protocol import CommandMessage, StateMessage, ErrorMessage

def run_network_example():
    """运行网络示例"""
    
    # 配置
    config = {
        'network': {
            'host': 'localhost',
            'port': 8080,
            'buffer_size': 4096,
            'timeout': 1.0
        }
    }
    
    # 创建网络管理器
    network = NetworkManager(config)
    
    # 消息处理器
    def handle_command(message: dict):
        print(f"收到命令: {message}")
        
        # 发送状态回复
        state = {
            'position': [0.0, 0.0, 0.0],
            'velocity': [0.0, 0.0, 0.0]
        }
        network.send_message(
            StateMessage('robot_state', state=state).to_dict()
        )
        
    def handle_error(message: dict):
        print(f"收到错误: {message}")
        
    # 注册处理器
    network.register_handler('command', handle_command)
    network.register_handler('error', handle_error)
    
    # 启动网络
    network.start()
    
    try:
        # 发送命令
        command = CommandMessage(
            'move',
            command='joint',
            params={'position': [1.0, 0.0, 0.0]}
        )
        network.send_message(command.to_dict())
        
        # 运行一段时间
        time.sleep(10.0)
        
    finally:
        network.stop()

if __name__ == '__main__':
    run_network_example() 