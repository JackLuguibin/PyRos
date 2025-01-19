import time
from ..rpc_server import RPCServer
from ..rpc_client import RPCClient

def run_rpc_example():
    """运行RPC示例"""
    
    # 服务器配置
    server_config = {
        'host': 'localhost',
        'port': 8081,
        'max_clients': 5
    }
    
    # 客户端配置
    client_config = {
        'host': 'localhost',
        'port': 8081,
        'timeout': 5.0
    }
    
    # 创建服务器
    server = RPCServer(server_config)
    
    # 注册方法
    def add(a: float, b: float) -> float:
        return a + b
        
    def get_status() -> dict:
        return {
            'time': time.time(),
            'status': 'running'
        }
        
    server.register_method('add', add)
    server.register_method('get_status', get_status)
    
    # 启动服务器
    server.start()
    
    try:
        # 创建客户端
        client = RPCClient(client_config)
        
        # 调用方法
        result = client.call('add', {'a': 1.0, 'b': 2.0})
        print("1.0 + 2.0 =", result)
        
        status = client.call('get_status')
        print("状态:", status)
        
        # 运行一段时间
        time.sleep(10.0)
        
    finally:
        server.stop()

if __name__ == '__main__':
    run_rpc_example() 