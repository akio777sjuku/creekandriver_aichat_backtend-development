from dataclasses import dataclass, asdict
from datetime import datetime
from json import dumps, loads


@dataclass
class Recruitment():
    url: str
    industry: str
    occupation: str
    location: str
    salary_type: str
    salary: str
    employment_type: str
    benefits: str
    point: str

    @property
    def __dict__(self):
        return asdict(self)

    @property
    def json(self):
        return loads(dumps(self.__dict__))


@dataclass
class RecruitmentInfo():
    id: str
    type: str
    recruitment: Recruitment
    catch_copy:str
    recruit_equirements:str
    openai_model: str
    created_user: str
    create_date: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @property
    def __dict__(self):
        return asdict(self)

    @property
    def json(self):
        return loads(dumps(self.__dict__))
