from sqlalchemy import Column, String, DateTime, Integer, Boolean
from app.models.base import MixinColumn
from app.database import Base


class Authentication(Base, MixinColumn):
    __tablename__ = "authentication"
    __table_args__ = {
        'comment': '権限テーブル'
    }
    id = Column(Integer, unique=True, primary_key=True,
                autoincrement=True, index=True)
    user_id = Column(String(255), index=True, comment="ユーザーID")
    admin_role = Column(Boolean, default=False, comment="admin権限")
    upload_role = Column(Boolean, default=False, comment="アップロード権限")
