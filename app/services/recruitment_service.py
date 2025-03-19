import re
import json
from uuid import uuid1
from quart import current_app
from azure.cosmos import PartitionKey
from langchain_community.document_loaders import WebBaseLoader
from sqlalchemy import desc
from sqlalchemy.future import select
from app.extensions import get_openai_client, get_cosmos_client
from app.database import get_db_session, db_transaction
from app.models import recruitment as recruitment_models
from app.constants import COMPANY_CONTAINER, JOBINFO_CONTAINER


class RecruitmentService():

    def __init__(self):
        self.openai_client = get_openai_client()
        cosmos_db = get_cosmos_client().create_database_if_not_exists(
            id=current_app.config["COSMOSDB_DATABASE"])
        self.company_cosmos = cosmos_db.create_container_if_not_exists(id=COMPANY_CONTAINER,
                                                                       partition_key=PartitionKey(path="/type"))
        self.job_info_cosmos = cosmos_db.create_container_if_not_exists(id=JOBINFO_CONTAINER,
                                                                        partition_key=PartitionKey(path="/type"))

    async def __companyInfoExtraction(self, data):
        completion = await self.openai_client.beta.chat.completions.parse(
            model=current_app.config['OPENAI_MODEL']["gpt-4o"],
            messages=[
                {"role": "system", "content": """Extract the information to output JSON.json schemas:{"type": "object","properties": {"company_name": {"type": "string"},"headquarters_location": {"type": "string"},"capital": {"type": "string"},"sales": {"type": "string"},"number_of_employees": {"type": "string"},"establishment_date": {"type": "string"},"listing_status": {"type": "string"},"industry": {"type": "string"}},"required": [],"additionalProperties": false}"""},
                {"role": "user", "content": data},
            ],
            response_format={"type": "json_object"},
        )
        company_info = completion.choices[0].message.content
        return json.loads(company_info)

    async def __jobInfoExtraction(self, data):
        completion = await self.openai_client.beta.chat.completions.parse(
            model=current_app.config['OPENAI_MODEL']["gpt-4o"],
            messages=[
                {"role": "system",
                    "content": """Extract the information to output JSON. json schemas:{"title":"JobInfo","type":"object","properties":{"recruitment_features":{"title":"求人特徴","type":"string"},"recruitment_position":{"title":"募集職種","type":"string"},"position":{"title":"ポジション","type":"string"},"english_usage_scenes":{"title":"英語利用場面","type":"string"},"applicable_qualifications":{"title":"活かせる資格","type":"string"},"selection_process":{"title":"選考過程","type":"string"},"organization_structure":{"title":"組織構成","type":"string"},"application_requirements":{"title":"応募要件","type":"string"},"employment_type":{"title":"雇用形態","type":"string"},"probation_period":{"title":"試用期間","type":"string"},"changes_in_working_conditions":{"title":"労働条件変更点","type":"string"},"work_location":{"title":"勤務地","type":"string"},"nearest_station":{"title":"最寄駅","type":"string"},"annual_income":{"title":"年収","type":"string"},"wage_form":{"title":"賃金形態","type":"string"},"overtime_allowance":{"title":"残業代","type":"string"},"fixed_overtime_hours":{"title":"固定残業時間","type":"string"},"base_salary_excluding_fixed_overtime":{"title":"固定残業代を除いた基本給","type":"string"},"salary_system_notes":{"title":"給与制度備考","type":"string"},"working_hours":{"title":"勤務時間","type":"string"},"break_time_minutes":{"title":"休憩時間(分)","type":"integer"},"working_hours_notes":{"title":"勤務時間備考","type":"string"},"overtime_hours_in_normal_time":{"title":"残業時間(通常時)","type":"string"},"discretionary_labor_system":{"title":"裁量労働有無","type":"string"},"holidays_and_vacations":{"title":"休日・休暇","type":"string"},"welfare_benefits":{"title":"福利厚生","type":"string"},"measures_against_passive_smoking":{"title":"受動喫煙防止措置に関する事項","type":"string"}}}"""},
                {"role": "user", "content": data},
            ],
            response_format={"type": "json_object"},
        )

        job_Info = completion.choices[0].message.content
        return json.loads(job_Info)

    @classmethod
    async def dataExtraction(self, url) -> str:
        loader = WebBaseLoader(url)
        loader.requests_kwargs = {'verify': False}
        docs = loader.load()
        cleaned_data = re.sub(r'\n+', "\n", docs[0].page_content)
        cleaned_data = re.sub(r'\t+', '\t', cleaned_data)
        company_info = await self.__companyInfoExtraction(cleaned_data)
        job_info = await self.__jobInfoExtraction(cleaned_data)

        return {"company": company_info, "job_info": job_info}

    @classmethod
    async def checkDataName(self, name) -> bool:
        async with get_db_session() as session:
            stmt = select(recruitment_models.Recruitment).where(
                recruitment_models.Recruitment.name == name)
            result = await session.execute(stmt)
            db_file = result.scalars().first()
            if db_file:
                return True
            else:
                return False

    @classmethod
    async def getRecruitmentList(self):
        async with get_db_session() as session:
            stmt = select(recruitment_models.Recruitment).order_by(desc(
                recruitment_models.Recruitment.updated_at))
            result = await session.execute(stmt)
            db_file = result.scalars().all()
            res = [recruitment.json for recruitment in db_file]
            return res
        
    async def saveRecruitment(self, name: str, company_info: str, job_info: str) -> bool:
        company_id = str(uuid1())
        company_info = {"id": company_id, "type": "company", **company_info}
        self.company_cosmos.create_item(company_info)
        job_info_id = str(uuid1())
        job_info = {"id": job_info_id, "type": "recruitment", **job_info}
        self.job_info_cosmos.create_item(job_info)
        db_recruitment = recruitment_models.Recruitment(id=str(
            uuid1()), name=name, company_id=company_id, job_info_id=job_info_id, created_by="create_user", updated_by="update_user")
        async with db_transaction() as session:
            session.add(db_recruitment)
        return True
