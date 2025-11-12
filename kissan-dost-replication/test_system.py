# test_system.py
"""
系统测试脚本 - 验证AI模型训练和系统功能
"""
import sys
import os
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from S002 import AgricultureAISystem
from S001 import SensorDataModel, LanguageTranslationModel

def test_ai_model_training():
    """测试AI模型训练"""
    print("🧪 测试AI模型训练...")
    
    # 测试传感器数据模型
    print("1. 测试传感器数据模型训练...")
    sensor_model = SensorDataModel()
    training_data = [
        {'soil_moisture': 15, 'temperature': 35, 'soil_ph': 6.0, 'npk_nitrogen': 30, 'expected_output': 'needs_water'},
        {'soil_moisture': 45, 'temperature': 25, 'soil_ph': 6.5, 'npk_nitrogen': 50, 'expected_output': 'healthy'}
    ]
    sensor_model.train(training_data)
    
    print(f"   传感器模型训练状态: {'✅ 已训练' if sensor_model.is_trained else '❌ 未训练'}")
    
    # 测试语言翻译模型
    print("2. 测试语言翻译模型训练...")
    language_model = LanguageTranslationModel()
    language_model.train({})
    
    print(f"   语言模型训练状态: {'✅ 已训练' if language_model.is_trained else '❌ 未训练'}")
    
    return sensor_model.is_trained and language_model.is_trained

def test_ai_system_integration():
    """测试AI系统集成"""
    print("\n🔗 测试AI系统集成...")
    
    # 创建AI系统实例
    ai_system = AgricultureAISystem(use_real_data=False)
    
    # 检查训练状态
    status = ai_system.get_system_status()
    print(f"   系统状态: {status['status']}")
    print(f"   整体训练状态: {'✅ 已训练' if status['is_trained'] else '❌ 未训练'}")
    print(f"   传感器模型: {'✅ 已训练' if status['model_a_trained'] else '❌ 未训练'}")
    print(f"   语言模型: {'✅ 已训练' if status['model_b_trained'] else '❌ 未训练'}")
    
    # 测试推理
    print("3. 测试推理功能...")
    try:
        advice = ai_system.inference_pipeline()
        print(f"   ✅ 推理成功")
        print(f"   建议内容: {advice[:100]}...")
        return True
    except Exception as e:
        print(f"   ❌ 推理失败: {e}")
        return False

def test_chat_functionality():
    """测试聊天功能"""
    print("\n💬 测试聊天功能...")
    
    from S001 import LanguageTranslationModel
    
    # 创建语言模型
    language_model = LanguageTranslationModel()
    language_model.train({})
    
    # 测试各种问题
    test_questions = [
        "需要浇水吗？",
        "土壤太干了怎么办？",
        "如何施肥？",
        "温度怎么样？",
        "柑橘病虫害防治"
    ]
    
    success_count = 0
    for question in test_questions:
        try:
            response = language_model.predict("healthy", {}, question)
            print(f"   Q: {question}")
            print(f"   A: {response[:80]}...")
            success_count += 1
        except Exception as e:
            print(f"   ❌ 回答失败: {e}")
    
    print(f"   聊天测试: {success_count}/{len(test_questions)} 通过")
    return success_count == len(test_questions)

def test_sensor_data_processing():
    """测试传感器数据处理"""
    print("\n📊 测试传感器数据处理...")
    
    from S001 import IoTDataCollector
    
    collector = IoTDataCollector()
    
    # 添加传感器
    sensors = [
        {'type': 'soil_moisture', 'id': 'test_moisture'},
        {'type': 'temperature', 'id': 'test_temp'},
        {'type': 'npk_sensor', 'id': 'test_npk'}
    ]
    
    for sensor in sensors:
        collector.add_sensor(sensor['type'], sensor['id'], sensor)
    
    # 收集数据
    raw_data = collector.collect_data()
    print(f"   原始数据: {raw_data}")
    
    # 预处理数据
    processed_data = collector.preprocess_data(raw_data)
    print(f"   处理后的数据: {processed_data}")
    
    return len(processed_data) > 0

def run_comprehensive_test():
    """运行全面测试"""
    print("🚀 开始Kissan-Dost系统全面测试")
    print("=" * 60)
    
    test_results = []
    
    # 运行各项测试
    test_results.append(("AI模型训练", test_ai_model_training()))
    test_results.append(("系统集成", test_ai_system_integration()))
    test_results.append(("聊天功能", test_chat_functionality()))
    test_results.append(("传感器处理", test_sensor_data_processing()))
    
    print("\n" + "=" * 60)
    print("📋 测试结果汇总:")
    print("=" * 60)
    
    passed_count = 0
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {test_name}: {status}")
        if result:
            passed_count += 1
    
    print("=" * 60)
    if passed_count == len(test_results):
        print("🎉 所有测试通过！系统正常工作")
        return True
    else:
        print(f"⚠️  {passed_count}/{len(test_results)} 项测试通过")
        return False

if __name__ == "__main__":
    success = run_comprehensive_test()
    
    if success:
        print("\n💡 下一步: 运行完整系统")
        print("   执行: python start_dev.py")
    else:
        print("\n🔧 需要修复问题后再测试")
    
    sys.exit(0 if success else 1)