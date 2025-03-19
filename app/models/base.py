from sqlalchemy import Column, DateTime, String
from sqlalchemy.ext.declarative import declared_attr
from datetime import datetime


class MixinColumn(object):
    @declared_attr
    def created_by(cls):
        return Column(String(225), nullable=False, comment="作成者")

    @declared_attr
    def updated_by(cls):
        return Column(String(225), nullable=False, comment="更新者")

    @declared_attr
    def created_at(cls):
        def default_datetime():
            return datetime.now()
        return Column(DateTime, default=default_datetime, nullable=False, comment="作成日付")

    @declared_attr
    def updated_at(cls):
        def default_datetime():
            return datetime.now()
        return Column(
            DateTime, default=default_datetime, onupdate=default_datetime, nullable=False, comment="更新日付"
        )
