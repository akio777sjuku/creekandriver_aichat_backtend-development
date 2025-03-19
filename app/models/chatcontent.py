from dataclasses import dataclass, asdict
from typing import List
from json import dumps, loads


@dataclass
class ChatContent():
    id: str
    type: str
    chat_id: str
    index: int
    question: str
    answer: str
    data_points: List[str]
    thoughts: str

    @property
    def __dict__(self):
        return asdict(self)

    @property
    def json(self):
        return loads(dumps(self.__dict__))
