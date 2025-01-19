import time
from ..rpc_server import RobotRPCServer
from ..rpc_client import RPCClient

def run_async_example():
    """运行异步RPC示例"""
    
    # 服务器配置
    server_config = {
        'host': 'localhost',
        'port': 8081,
        'task_queue': {
            'worker_count': 4,
            'default_timeout': 60.0
        }
    }
    
    # 客户端配置
    client_config = {
        'host': 'localhost',
        'port': 8081,
        'timeout': 5.0
    }
    
    # 创建服务器
    server = RobotRPCServer(server_config)
    server.start()
    
    try:
        # 创建客户端
        client = RPCClient(client_config)
        
        # 异步调用
        task_ids = []
        
        # 设置多个舵机角度
        for i in range(3):
            task_id = client.call_async('set_servo_angle', {
                'servo_id': f'servo_{i}',
                'angle': i * 30.0
            })
            task_ids.append(task_id)
            
        # 执行动作组
        task_id = client.call_async('execute_action_group', {
            'group_name': 'wave',
            'parallel': True
        })
        task_ids.append(task_id)
        
        # 等待所有任务完成
        for task_id in task_ids:
            result = client.get_task_result(task_id)
            print(f"任务 {task_id} 结果:", result)
            
        # 获取任务队列统计
        stats = server.task_queue.get_stats()
        print("任务统计:", stats)
        
    finally:
        server.stop()

if __name__ == '__main__':
    run_async_example() 