from pydantic import BaseModel
from typing import Dict

class UserQuery(BaseModel):
    query: str
    chat_history: list
    language: str
    
class InputDirPath(BaseModel):
    input_path: str