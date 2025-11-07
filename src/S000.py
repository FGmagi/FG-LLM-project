from abc import ABC, abstractmethod
from typing import Any
import pickle
import json
import pandas as pd
import logging
from dataclasses import dataclass, asdict
from typing import Any
import os
from datetime import datetime

T001 = False
logName = "SXXX.log"

def setupLogging():
    """配置日志系统"""
    global T001
    if (T001 == False):
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        
        file_handler = logging.FileHandler(logName, mode='a', encoding='utf-8')
        
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        logger.addHandler(file_handler)
        
        T001 = True

def printLog(message, level="INFO"):
    setupLogging()
    level = level.upper()
    if level == "DEBUG":
        logging.debug(message)
    elif level == "INFO":
        logging.info(message)
    elif level == "WARNING":
        logging.warning(message)
    elif level == "ERROR":
        logging.error(message)
    elif level == "CRITICAL":
        logging.critical(message)
    else:
        logging.info(message)

def dict_to_json_file(dictionary, file_path, ensure_ascii=False, indent=4):
    try:
        # 添加时间戳
        data_with_timestamp = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
            'data': dictionary
        }
        
        # 读取现有数据（如果文件存在）
        existing_data = []
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                # 确保existing_data是列表
                if not isinstance(existing_data, list):
                    existing_data = [existing_data]
            except (json.JSONDecodeError, IOError):
                existing_data = []
        
        # 追加新数据
        existing_data.append(data_with_timestamp)
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=ensure_ascii, indent=indent)
        
        printLog(f"JSON文件追加写入成功: {file_path} (时间戳: {data_with_timestamp['timestamp']})")
        return True
        
    except (TypeError, ValueError, IOError) as e:
        printLog(f"JSON文件写入失败: {e}")
        return False

def json_file_to_dict(file_path, get_latest=True):
    try:
        if not os.path.exists(file_path):
            printLog(f"文件不存在: {file_path}")
            return None
            
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 如果数据是列表格式（包含多个带时间戳的条目）
        if isinstance(data, list) and len(data) > 0:
            if get_latest:
                # 获取最后时间添加的数据（列表最后一个元素）
                latest_entry = data[-1]
                printLog(f"JSON文件读取成功: {file_path} (最后时间: {latest_entry.get('timestamp', '无时间戳')})")
                return latest_entry.get('data', latest_entry)
            else:
                # 返回所有数据
                printLog(f"JSON文件读取成功: {file_path} (共{len(data)}条记录)")
                return data
        else:
            # 如果是单个字典或空列表
            printLog(f"JSON文件读取成功: {file_path}")
            return data if not get_latest or not isinstance(data, list) else None
            
    except (json.JSONDecodeError, IOError) as e:
        printLog(f"JSON文件读取失败: {e}")
        return None

class BaseModel(ABC):
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.model = None
    
    @abstractmethod
    def train(self, train_data: Any, **kwargs) -> None:
        """训练模型"""
        pass
    
    @abstractmethod
    def predict(self, input_data: Any, **kwargs) -> Any:
        """模型预测"""
        pass
    
    def saveModel(self, model_path: str) -> None:
        """保存训练好的模型"""
        model_dict = self.__dict__.copy()
        dict_to_json_file(model_dict,model_path)
        printLog(f"模型已保存到: {model_path}")
    
    def loadModel(self, model_path: str) -> None:
        """加载已训练的模型"""
        model_dict = json_file_to_dict(model_path)
        for key, value in model_dict.items():
            setattr(self, key, value)
        printLog(f"模型已从 {model_path} 加载")