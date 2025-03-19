from dataclasses import dataclass
from json import dumps, loads
from sqlalchemy import Column, String, Integer, DateTime
from app.models.base import MixinColumn
from app.database import Base
from app.utils.jsonEncoder import CustomJSONEncoder


@dataclass
class LoginHistory(Base, MixinColumn):
    __tablename__ = "login_history"
    __table_args__ = {
        'comment': 'ログイン履歴'
    }
    id = Column(Integer, unique=True, primary_key=True,
                autoincrement=True, index=True)
    user_id = Column(String(255), index=True, comment="ユーザーID")
    user_name = Column(String(255), comment="ユーザー名")
    login_time = Column(DateTime, comment="ログイン時刻")

    @property
    def json(self):
        data = data = {k: v for k, v in self.__dict__.items()
                       if not k.startswith('_')}
        return loads(dumps(data, cls=CustomJSONEncoder))
