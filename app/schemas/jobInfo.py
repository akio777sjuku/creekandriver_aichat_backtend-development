from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class JobInfoBase(BaseModel):
    recruitment_features: Optional[str] = Field(None, title="求人特徴")
    recruitment_position: Optional[str] = Field(None, title="募集職種")
    position: Optional[str] = Field(None, title="ポジション")
    english_usage_scenes: Optional[str] = Field(None, title="英語利用場面")
    applicable_qualifications: Optional[str] = Field(None, title="活かせる資格")
    selection_process: Optional[str] = Field(None, title="選考過程")
    organization_structure: Optional[str] = Field(None, title="組織構成")
    application_requirements: Optional[str] = Field(None, title="応募要件")
    employment_type: Optional[str] = Field(None, title="雇用形態")
    probation_period: Optional[str] = Field(None, title="試用期間")
    changes_in_working_conditions: Optional[str] = Field(None, title="労働条件変更点")
    work_location: Optional[str] = Field(None, title="勤務地")
    nearest_station: Optional[str] = Field(None, title="最寄駅")
    annual_income: Optional[str] = Field(None, title="年収")
    wage_form: Optional[str] = Field(None, title="賃金形態")
    overtime_allowance: Optional[str] = Field(None, title="残業代")
    fixed_overtime_hours: Optional[str] = Field(None, title="固定残業時間")
    base_salary_excluding_fixed_overtime: Optional[str] = Field(None, title="固定残業代を除いた基本給")
    salary_system_notes: Optional[str] = Field(None, title="給与制度備考")
    working_hours: Optional[str] = Field(None, title="勤務時間")
    break_time_minutes: Optional[int] = Field(None, title="休憩時間(分)")
    working_hours_notes: Optional[str] = Field(None, title="勤務時間備考")
    overtime_hours_in_normal_time: Optional[str] = Field(None, title="残業時間(通常時)")
    discretionary_labor_system: Optional[str] = Field(None, title="裁量労働有無")
    holidays_and_vacations: Optional[str] = Field(None, title="休日・休暇")
    welfare_benefits: Optional[str] = Field(None, title="福利厚生")
    measures_against_passive_smoking: Optional[str] = Field(None, title="受動喫煙防止措置に関する事項")


class JobInfo(JobInfoBase):
    id: str
    job_description: Optional[str] = Field(None, title="業務内容")

    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.strftime('%Y-%m-%d %H:%M:%S') if v else None
        }
