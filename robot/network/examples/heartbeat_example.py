import time
from ..rpc_server import RPCServer
from ..rpc_client import RPCClient

def run_heartbeat_example():
    """运行心跳示例"""
    
    # 服务器配置
    server_config = {
        'host': 'localhost',
        'port': 8081,
        'heartbeat': {
            'interval': 1.0,
            'timeout': 3.0,
            'max_missed': 2
        }
    }
    
    # 客户端配置
    client_config = {
        'host': 'localhost',
        'port': 8081,
        'heartbeat': {
            'interval': 1.0,
            'timeout': 3.0
        }
    }
    
    # 创建服务器
    server = RPCServer(server_config)
    server.start()
    
    try:
        # 创建客户端
        client = RPCClient(client_config)
        client.connect()
        
        print("连接已建立，等待心跳...")
        time.sleep(5.0)
        
        # 模拟网络断开
        print("模拟网络断开...")
        client.socket.close()
        
        # 等待心跳超时
        time.sleep(5.0)
        
        print("客户端状态:", "已连接" if client.connected else "已断开")
        
    finally:
        server.stop()

if __name__ == '__main__':
    run_heartbeat_example() 