from dataclasses import dataclass
from json import dumps, loads
from sqlalchemy import Column, String, SmallInteger
from app.database import Base
from app.models.base import MixinColumn
from app.utils.jsonEncoder import CustomJSONEncoder


@dataclass
class Recruitment(Base, MixinColumn):
    __tablename__ = "recruitment"
    __table_args__ = {
        'comment': '求人情報テーブル'
    }
    id = Column(String(255), unique=True, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, comment="データ名")
    company_id = Column(String(255), nullable=False, comment="企業情報ID")
    job_info_id = Column(String(255), nullable=False, comment="求人情報ID")
    employment_type = Column(SmallInteger, comment="雇用形態")

    @property
    def json(self):
        data = data = {k: v for k, v in self.__dict__.items()
                       if not k.startswith('_')}
        return loads(dumps(data, cls=CustomJSONEncoder))
