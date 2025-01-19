import xmlrpc.client

class RobotClient:
    def __init__(self, host: str = "localhost", port: int = 8000):
        self.server = xmlrpc.client.ServerProxy(f"http://{host}:{port}")
        
    def execute_action_group(self, group_name: str) -> bool:
        """执行动作组"""
        return self.server.execute_action_group(group_name)
        
    def set_servo_angle(self, servo_id: str, angle: float) -> bool:
        """设置舵机角度"""
        return self.server.set_servo_angle(servo_id, angle)
        
    def get_sensor_data(self, sensor_id: str):
        """获取传感器数据"""
        return self.server.get_sensor_data(sensor_id)

def main():
    # 创建机器人客户端
    client = RobotClient()
    
    # 示例：执行预定义动作
    print("执行挥手动作...")
    if client.execute_action_group("wave"):
        print("执行成功")
    else:
        print("执行失败")
    
    # 示例：读取传感器数据
    distance = client.get_sensor_data("ultrasonic1")
    print(f"超声波传感器距离: {distance}cm")
    
    # 示例：直接控制舵机
    print("控制舵机1到45度...")
    if client.set_servo_angle("servo1", 45):
        print("设置成功")
    else:
        print("设置失败")

if __name__ == "__main__":
    main() 