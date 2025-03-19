from pydantic import BaseModel, Field
from typing import Optional

class CompanyInfo(BaseModel):
    company_name: str = Field(..., title="会社名")
    headquarters_location: str = Field(..., title="本社所在地")
    capital: Optional[str] = Field(None, title="資本金")
    sales: Optional[str] = Field(None, title="売上高")
    number_of_employees: Optional[int] = Field(None, title="従業員数")
    establishment_date: Optional[str] = Field(None, title="設立")
    listing_status: Optional[str] = Field(None, title="上場区分")
    industry: Optional[str] = Field(None, title="業種")
    business_description: Optional[str] = Field(None, title="事業内容")
    recruitment_features: Optional[str] = Field(None, title="求人特徴")
    recruitment_position: Optional[str] = Field(None, title="募集職種")
    position: Optional[str] = Field(None, title="ポジション")
    english_usage_scenes: Optional[str] = Field(None, title="英語利用場面")
    applicable_qualifications: Optional[str] = Field(None, title="活かせる資格")
    selection_process: Optional[str] = Field(None, title="選考過程")
    job_description: Optional[str] = Field(None, title="業務内容")
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

    class Config:
        schema_extra = {
            "example": {
                "company_name": "株式会社Example",
                "headquarters_location": "東京都渋谷区",
                "capital": "1億円",
                "sales": "100億円",
                "number_of_employees": 500,
                "establishment_date": "2000年4月1日",
                "listing_status": "上場",
                "industry": "IT",
                "business_description": "ソフトウェア開発",
                "recruitment_features": "スキルアップできる環境",
                "recruitment_position": "エンジニア",
                "position": "リーダー",
                "english_usage_scenes": "日常業務で使用",
                "applicable_qualifications": "TOEIC 800点以上",
                "selection_process": "書類選考、面接",
                "job_description": "ソフトウェア開発全般",
                "organization_structure": "技術部門",
                "application_requirements": "3年以上の経験",
                "employment_type": "正社員",
                "probation_period": "3ヶ月",
                "changes_in_working_conditions": "なし",
                "work_location": "東京",
                "nearest_station": "渋谷駅",
                "annual_income": "600万円",
                "wage_form": "月給制",
                "overtime_allowance": "あり",
                "fixed_overtime_hours": "20時間",
                "base_salary_excluding_fixed_overtime": "基本給30万円",
                "salary_system_notes": "賞与年2回",
                "working_hours": "9:00-18:00",
                "break_time_minutes": 60,
                "working_hours_notes": "フレックスタイム制度あり",
                "overtime_hours_in_normal_time": "月平均10時間",
                "discretionary_labor_system": "あり",
                "holidays_and_vacations": "土日祝日",
                "welfare_benefits": "健康保険、厚生年金",
                "measures_against_passive_smoking": "屋内禁煙"
            }
        }
