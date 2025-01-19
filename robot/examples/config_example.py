from robot.config.config_manager import ConfigManager

def run_config_example():
    """运行配置示例"""
    
    # 创建配置管理器
    config_manager = ConfigManager('config/robot_config.yaml')
    
    # 加载配置
    if not config_manager.load_config():
        return
        
    # 获取网络配置
    network_config = config_manager.get_config('network')
    print("网络配置:", network_config)
    
    # 更新控制器配置
    new_gains = {
        'gains': {
            'kp': [200.0, 200.0],
            'kd': [40.0, 40.0]
        }
    }
    config_manager.update_config('controller', new_gains)
    
    # 保存配置
    config_manager.save_config()

if __name__ == '__main__':
    run_config_example() 