from abc import ABC, abstractmethod
from typing import Any
import json
import logging
from dataclasses import dataclass, asdict
import os
from datetime import datetime

T001 = False
logName = "kissan_dost.log"

def setupLogging():
    global T001
    if not T001:
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
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(dictionary, f, ensure_ascii=ensure_ascii, indent=indent)
        printLog(f"JSON文件写入成功: {file_path}")
        return True
    except Exception as e:
        printLog(f"JSON文件写入失败: {e}")
        return False

def json_file_to_dict(file_path):
    try:
        if not os.path.exists(file_path):
            printLog(f"文件不存在: {file_path}")
            return None
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        printLog(f"JSON文件读取成功: {file_path}")
        return data
    except Exception as e:
        printLog(f"JSON文件读取失败: {e}")
        return None

class BaseModel(ABC):
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.model = None
    
    @abstractmethod
    def train(self, train_data: Any, **kwargs) -> None:
        pass
    
    @abstractmethod
    def predict(self, input_data: Any, **kwargs) -> Any:
        pass
    
    def saveModel(self, model_path: str) -> None:
        try:
            dict_to_json_file(self.__dict__, model_path)
            printLog(f"模型已保存到: {model_path}")
        except Exception as e:
            printLog(f"模型保存失败: {e}")
    
    def loadModel(self, model_path: str) -> None:
        try:
            model_dict = json_file_to_dict(model_path)
            if model_dict:
                for key, value in model_dict.items():
                    setattr(self, key, value)
                printLog(f"模型已从 {model_path} 加载")
            else:
                printLog(f"模型文件为空或损坏: {model_path}")
        except Exception as e:
            printLog(f"模型加载失败: {e}")

@dataclass
class SensorReading:
    sensor_id: str
    location: str
    timestamp: str
    temperature: float
    humidity: float
    soil_moisture: float
    soil_ph: float
    npk_nitrogen: float
    npk_phosphorus: float
    npk_potassium: float
    
    def to_dict(self):
        return asdict(self)

@dataclass
class AgricultureAdvice:
    advice_id: str
    sensor_reading: SensorReading
    recommendation: str
    confidence: float
    urgency: str
    actions: list
    
    def to_dict(self):
        return asdict(self)