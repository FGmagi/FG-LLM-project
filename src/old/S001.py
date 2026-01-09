from S000 import *

# ===========================================
# 后端功能实现
# rele
# ===========================================

def releaseIO(input_text:str) -> str:
    pass

class DataModel(BaseModel):
    def __init__(self):
        super("DataModel")
    
    def train(self, train_data: Any, **kwargs) -> None:
        pass
    
    def predict(self, input_data: Any, **kwargs) -> Any:
        pass

class LanguageModel(BaseModel):
    def __init__(self):
        super("LanguageModel")
    
    def train(self, train_data: Any, **kwargs) -> None:
        pass
    
    def predict(self, input_data: Any, **kwargs) -> Any:
        pass
