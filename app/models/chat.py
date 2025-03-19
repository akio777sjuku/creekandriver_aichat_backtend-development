from dataclasses import dataclass
from sqlalchemy import Column, String
from json import dumps, loads
from app.models.base import MixinColumn
from app.database import Base
from app.utils.jsonEncoder import CustomJSONEncoder


@dataclass
class Chat(Base, MixinColumn):
    __tablename__ = "chats"
    __table_args__ = {
        'comment': 'チャットテーブル'
    }
    id = Column(String(255), unique=True, primary_key=True,
                index=True, comment="チャットID")
    type = Column(String(20), comment="チャットタイプ")
    name = Column(String(255), comment="チャット名")
    openai_model = Column(String(20), comment="OpenAIモデル名")

    @property
    def json(self):
        data = data = {k: v for k, v in self.__dict__.items()
                       if not k.startswith('_')}
        return loads(dumps(data, cls=CustomJSONEncoder))
