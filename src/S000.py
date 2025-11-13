from abc import ABC, abstractmethod
from typing import Any
import json
import logging
from dataclasses import dataclass, asdict
import os
from datetime import datetime

# ===========================================
# 基础功能与数据结构定义
# ===========================================
__T001__ = False
logName = "SXXX.log"
DEMO = True

def setupLogging():
    global __T001__
    if not __T001__:
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
    default_model_folder_path = ""
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.model_path = None
    
    @abstractmethod
    def train(self, train_data: Any, **kwargs) -> None:
        pass
    
    @abstractmethod
    def predict(self, input_data: Any, **kwargs) -> Any:
        pass
    
    '''
        模型数据 存储 路径可由 saveModel(path) 指定
        若无指定，尝试使用 self.model_path 路径，若仍无定义，则会使用默认路径
        默认路径 = BaseModel.default_model_folder_path + model_name
    '''
    def getModelFilePath() -> str:
        if self.model_path == None:
            return default_model_folder_path + "\\" + model_name + ".json"
        else:
            return self.model_path

    def hasModel(self, model_path: str = "") -> None:
        # 查找是否存在某模型
        if (model_path == ""):
            model_path = getModelFilePath()
        if not os.path.exists(model_path):
            printLog(f"尝试查找模型文件:{model_path} 不存在")
            return False
        else:
            printLog(f"尝试查找模型文件:{model_path} 存在")
            return True

    def delModel(self, model_path: str = "") -> None:
        # 删除保存好的模型文件
        if (model_path == ""):
            model_path = getModelFilePath()
        
        if os.path.isfile(model_path):
            try:
                os.remove(model_path)
                printLog(f"删除模型文件: {model_path}成功")
            except Exception as e:
                printLog(f"删除模型文件: {model_path}时出错: {e}")

    def saveModel(self, model_path: str = "") -> None:
        try:
            if (model_path == ""):
                model_path = getModelFilePath()
            dict_to_json_file(self.__dict__, model_path)
            printLog(f"模型已保存到: {model_path}")
        except Exception as e:
            printLog(f"模型保存失败: {e}")
    
    def loadModel(self, model_path: str = "") -> None:
        try:
            if (model_path == ""):
                model_path = getModelFilePath()
            model_dict = json_file_to_dict(model_path)
            if model_dict:
                for key, value in model_dict.items():
                    setattr(self, key, value)
                printLog(f"模型已从 {model_path} 加载")
            else:
                printLog(f"模型文件为空或损坏: {model_path}")
        except Exception as e:
            printLog(f"模型加载失败: {e}")
