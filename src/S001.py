from S000 import *
# ===========================================
# 后端功能实现
# rele
# ===========================================

reBuildModel = True
def releaseIO(input_text:str) -> str:
    dm = DataAnalyseModel()
    lm = LanguageModel()

    if (reBuildModel == True):
        dm.delModel()
        lm.delModel()
        dmTrain()
        lmTrain() 

    dm.loadModel()
    lm.loadModel()

    t1 = dm.predict(input_text)
    t2 = lm.predict(t1)
    return t2

def dmTrain() -> None:
    return DataAnalyseModel()
    pass

def lmTrain() -> None:
    return LanguageModel()
    pass

# 删除建好的本地模型
def clearModels():
    pass


class DataAnalyseModel(BaseModel):
    def __init__(self):
        super("DataAnalyseModel")
    
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
