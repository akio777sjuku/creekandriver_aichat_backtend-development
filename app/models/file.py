from dataclasses import dataclass
from json import dumps, loads
from sqlalchemy import Column, String, Integer, SmallInteger, DECIMAL
from app.models.base import MixinColumn
from app.database import Base
from app.utils.jsonEncoder import CustomJSONEncoder


@dataclass
class File(Base, MixinColumn):
    __tablename__ = "files"
    __table_args__ = {
        'comment': 'ファイル情報'
    }
    id = Column(String(255), unique=True, primary_key=True,
                index=True, comment="ファイルID")
    name = Column(String(255), comment="ファイル名")
    chat_id = Column(String(255), index=True, comment="チャットID")
    chat_type = Column(String(20), index=True, comment="チャットタイプ")
    file_url = Column(String(255), comment="保存場所")
    file_size_mb = Column(DECIMAL(10, 2), comment="ファイルサイズ(MB)")
    status = Column(
        SmallInteger, comment="ファイル状態 0:アップロード中 1:アップロード成功 2:アップロード失敗")
    folder_id = Column(Integer, index=True, comment="フォルダーID")
    category = Column(String(20), comment="カテゴリ")

    @property
    def json(self):
        data = data = {k: v for k, v in self.__dict__.items()
                       if not k.startswith('_')}
        return loads(dumps(data, cls=CustomJSONEncoder))
