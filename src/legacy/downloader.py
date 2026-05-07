import requests
import json
from datetime import datetime, timedelta
import S000 as s0
from abc import ABC, abstractmethod
from typing import Union, List, Dict, Any,Optional,Protocol

DateTime = datetime
JsonType = Union[Dict[str, Any], List[Any]]
printLog = s0.printLog

class BaseDownloader(Protocol):
    # 用户登录
    def logIn(self, username: str, password: str) -> None:...

    # 确定登录状态
    def isLogIn(self, **kwargs) -> bool:...
    
    # 获取设备分组列表
    def getDeviceGroups(self, **kwargs) -> JsonType:...
    
    # 获取某分组下设备列表
    def getDevicesInGroup(self, group_id: str = "", **kwargs) -> JsonType:...
    
    # 获取设备软件参数
    def getDeviceSoftwareParams(self, device_key: str, **kwargs) -> JsonType:...
    
    # 获取历史传感器数据
    def getHistoricalSensorData(self, device_key:str,begin_time:DateTime,end_time:DateTime) -> JsonType:...
    
class Downloader(BaseDownloader):
    def __init__(self, server_ip:str = "192.168.1.100" , server_port:str = "9001"):
        self.server_ip = server_ip
        self.server_port = server_port     
        self.username = None     
        self.userid = None

    def logIn(self,username:str,password:str) -> None:
        printLog(f"正在登录服务器")
        self.username = username
        self.userid =  getUserId(self.server_ip,self.server_port,self.username,password)
        if (self.userid):
            printLog(f"登录成功")
        else:    
            printLog(f"登录失败")

    # 获取用户设备分组列表
    def getDeviceGroups(self) -> JsonType:
        if (self.isLogIn() == False):
            printLog("获取用户设备分组列表时，尚未登录")
            return []

        printLog(f"正在获取用户设备分组列表下设备")
        base_url = f"http://{self.server_ip}:{self.server_port}"
        headers = {"userId": self.userid}
        try:
            response = requests.get(
                f"{base_url}/app/GetUserDeviceGroups",
                headers=headers,
                timeout=10
            )
            result = response.json()
            
            if result.get('code') == 1000:
                groups = result.get('data', [])
                log_mes = "获取用户设备分组列表成功，如下\n"
                for g in groups:
                    log_mes += f"groupName:{g['groupName']} groupId {g['groupId']}\n"
                printLog(log_mes)
                return groups
            else:
                printLog(f"获取用户设备分组列表失败: {result.get('message')}")
                return []
                
        except Exception as e:
            printLog(f"获取用户设备分组列表异常: {e}")
            return []

    # 获取分组中的设备列表，group_id = "" 表示全部设备
    def getDevicesInGroup(self, group_id:str = "") -> JsonType:
        if (self.isLogIn() == False):
            printLog("获取分组中的设备列表，尚未登录")
            return []

        try:
            printLog(f"正在获取 {group_id} 分组下设备")
            params = {"groupId": group_id}
            base_url = f"http://{self.server_ip}:{self.server_port}"
            headers = {"userId": self.userid}
            
            response = requests.get(
                f"{base_url}/app/GetDeviceData",
                headers=headers,
                params=params,
                timeout=10
            )
            result = response.json()
            
            if result.get('code') == 1000:
                devices = result.get('data', [])
                printLog(f"获取设备列表成功，共 {len(devices)} 个设备")
                return devices
            else:
                printLog(f"获取设备列表失败: {result.get('message')}")
                return []
                
        except Exception as e:
            printLog(f"获取设备列表异常: {e}")
            return []
    
    # 获取设备软件参数
    def getDeviceSoftwareParams(self, device_key:str) -> JsonType:
        if (self.isLogIn() == False):
            printLog("获取设备软件参数，尚未登录")
            return []

        try:
            printLog(f"正在获取设备软件参数")
            params = {"deviceKey": device_key}
            base_url = f"http://{self.server_ip}:{self.server_port}"
            headers = {"userId": self.userid}

            response = requests.get(
                f"{base_url}/app/GetDeviceSoftParam",
                headers=headers,
                params=params,
                timeout=10
            )
            result = response.json()
            
            if result.get('code') == 1000:
                printLog("获取设备参数成功")
                return result.get('data', {})
            else:
                printLog(f"获取设备参数失败: {result.get('message')}")
                return []
                
        except Exception as e:
            printLog(f"获取设备参数异常: {e}")
            return []

    # 获取历史传感器数据
    def getHistoricalSensorData(self, device_key:str,begin_time:DateTime,end_time:DateTime, node_id:int = -1) -> JsonType:
        if (self.isLogIn() == False):
            printLog("获取设备软件参数，尚未登录")
            return []

        try:
            printLog(f"正在获取历史传感器数据")
            
            params = {
                "deviceKey": device_key,
                "nodeId": node_id,  # -1 表示所有节点
                "beginTime": begin_time.strftime("%Y-%m-%d %H:%M:%S"),# (YYYY-MM-dd HH:mm:ss)
                "endTime": end_time.strftime("%Y-%m-%d %H:%M:%S"),# (YYYY-MM-dd HH:mm:ss)
                "isAlarmData": -1  # -1全部，0正常数据，1报警数据
            }
            base_url = f"http://{self.server_ip}:{self.server_port}"
            headers = {"userId": self.userid}

            response = requests.get(
                f"{base_url}/app/QueryHistoryList",
                headers=headers,
                params=params,
                timeout=30  # 历史数据查询可能较慢
            )
            result = response.json()
            
            if result.get('code') == 1000:
                history_data = result.get('data', [])
                printLog(f"获取历史数据成功，共 {len(history_data)} 条记录")
                return history_data
            else:
                printLog(f"获取历史数据失败: {result.get('message')}")
                return []
                
        except Exception as e:
            printLog(f"获取历史数据异常: {e}")
            return []

    def isLogIn(self) -> bool:
        b = bool(self.username and self.userid)
        return b

def getUserId(ip:str,port:str,username:str,password:str) -> Optional[str]:
    login_url = f"http://{ip}:{port}/app/Login"
    login_data = {
        "loginName": username,
        "password": password
    }
    
    try:
        # 发送POST请求
        response = requests.post(
            login_url,
            json=login_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        # 解析响应
        result = response.json()
        
        # 检查登录是否成功
        if result.get('code') == 1000:
            userid = result['data']['userId']
            user_name = result['data']['userName']
            printLog(f"登陆成功，用户名 {user_name}，uid {userid}，权限列表: {result['data'].get('authList', [])}")
            return userid
        else:
            error_msg = result.get('message', '未知错误')
            printLog(f"登录失败: {error_msg}")
            return None
            
    except requests.exceptions.RequestException as e:
        printLog(f"登录时 网络请求错误: {e}")
        return None
    except json.JSONDecodeError as e:
        printLog(f"登录时 JSON解析错误: {e}")
        return None
    except KeyError as e:
        printLog(f"登录时 响应数据格式错误，缺少字段: {e}")
        return None
