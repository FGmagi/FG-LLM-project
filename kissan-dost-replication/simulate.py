import requests
import time
from datetime import datetime
import random
from S001 import IoTDataCollector

class AgricultureSensorSimulator:
    def __init__(self, backend_url="http://localhost:8000"):
        self.backend_url = backend_url
        self.collector = IoTDataCollector()
        self.setup_sensors()
        
    def setup_sensors(self):
        sensor_configs = [
            {'type': 'soil_moisture', 'id': 'moisture_001'},
            {'type': 'temperature', 'id': 'temp_001'},
            {'type': 'humidity', 'id': 'humidity_001'},
            {'type': 'ph_sensor', 'id': 'ph_001'},
            {'type': 'npk_sensor', 'id': 'npk_001'}
        ]
        for config in sensor_configs:
            self.collector.add_sensor(config['type'], config['id'], config)
    
    def generate_realistic_sensor_data(self):
        current_hour = datetime.now().hour
        if 6 <= current_hour <= 18:
            base_temp = 25
            temp_variation = 10
        else:
            base_temp = 18
            temp_variation = 5
        
        return {
            "sensor_id": f"sensor_{random.randint(1000, 9999)}",
            "location": "field_3", 
            "timestamp": datetime.now().isoformat(),
            "readings": {
                "soil_moisture": max(20, min(60, 40 + random.uniform(-5, 5))),
                "temperature": max(15, min(40, base_temp + random.uniform(-temp_variation, temp_variation))),
                "humidity": max(30, min(90, 60 + random.uniform(-15, 15))),
                "npk": {
                    "nitrogen": max(20, min(80, 50 + random.uniform(-10, 10))),
                    "phosphorus": max(15, min(70, 40 + random.uniform(-8, 8))),
                    "potassium": max(25, min(75, 45 + random.uniform(-8, 8)))
                },
                "ph": round(6.0 + random.uniform(-0.5, 0.5), 1)
            },
            "metadata": {
                "crop_type": "citrus",
                "growth_stage": "flowering",
                "data_quality": "high",
                "simulation": True
            }
        }
    
    def send_to_backend(self, data):
        try:
            response = requests.post(
                f"{self.backend_url}/api/v1/ingest",
                json=data,
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            if response.status_code == 200:
                return True, "数据发送成功"
            else:
                return False, f"HTTP错误: {response.status_code}"
        except Exception as e:
            return False, f"发送数据时出错: {e}"
    
    def test_backend_connection(self):
        try:
            response = requests.get(f"{self.backend_url}/health", timeout=5)
            if response.status_code == 200:
                return True, "后端服务正常"
            else:
                return False, f"后端服务异常: {response.status_code}"
        except Exception as e:
            return False, f"无法连接到后端: {e}"
    
    def start_simulation(self, interval=30):
        print("🚀 启动Kissan-Dost传感器数据模拟器...")
        print("=" * 50)
        
        connection_ok, connection_msg = self.test_backend_connection()
        print(f"🔗 后端连接: {connection_msg}")
        
        if not connection_ok:
            print("❌ 无法连接到后端服务，请确保后端服务正在运行")
            return
        
        print(f"📡 数据发送到: {self.backend_url}/api/v1/ingest")
        print(f"⏱️  发送间隔: {interval}秒")
        print("=" * 50)
        print("按 Ctrl+C 停止模拟")
        
        try:
            message_count = 0
            while True:
                data = self.generate_realistic_sensor_data()
                message_count += 1
                success, message = self.send_to_backend(data)
                
                if success:
                    print(f"✅ [{message_count}] 数据发送成功: {data['timestamp']}")
                else:
                    print(f"❌ [{message_count}] 数据发送失败: {message}")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n🛑 模拟器已停止")
            print(f"📊 总共发送了 {message_count} 条数据")

if __name__ == "__main__":
    simulator = AgricultureSensorSimulator()
    simulator.start_simulation(interval=30)