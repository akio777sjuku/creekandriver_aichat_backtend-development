from sqlalchemy import Column, String, Integer
from app.models.base import MixinColumn
from app.database import Base


class Folder(Base, MixinColumn):
    __tablename__ = "folders"
    __table_args__ = {
        'comment': 'フォルダーテーブル'
    }
    id = Column(Integer, unique=True, primary_key=True,
                autoincrement=True, index=True)
    name = Column(String(255), nullable=False, index=True, comment="フォルダー名")
