from dataclasses import dataclass, asdict
from datetime import datetime
from json import dumps, loads

@dataclass
class Attributes():
    tag: str
    source: str
    size: str
    
    @property
    def __dict__(self):
        return asdict(self)

    @property
    def json(self):
        return loads(dumps(self.__dict__))


@dataclass
class FileInfo():
    id: str
    type: str
    file_name: str
    file_status: str
    folder_id: str
    attributes: Attributes
    created_user: str
    created_date: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @property
    def __dict__(self):
        return asdict(self)

    @property
    def json(self):
        return loads(dumps(self.__dict__))
