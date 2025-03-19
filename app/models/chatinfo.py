from dataclasses import dataclass, asdict
from datetime import datetime
from json import dumps, loads


@dataclass
class ChatInfo():
    id: str
    type: str
    chat_type: str
    chat_name: str
    openai_model:str
    created_user:str
    create_date: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @property
    def __dict__(self):
        return asdict(self)

    @property
    def json(self):
        return loads(dumps(self.__dict__))
