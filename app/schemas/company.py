from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CompanyBase(BaseModel):
    company_name: Optional[str] = Field(..., title="会社名")
    headquarters_location: Optional[str] = Field(..., title="本社所在地")
    capital: Optional[str] = Field(None, title="資本金")
    sales: Optional[str] = Field(None, title="売上高")
    number_of_employees: Optional[str] = Field(None, title="従業員数")
    establishment_date: Optional[str] = Field(None, title="設立")
    listing_status: Optional[str] = Field(None, title="上場区分")
    industry: Optional[str] = Field(None, title="業種")


class Company(CompanyBase):
    id: int
    business_description: Optional[str] = Field(None, title="事業内容")

    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.strftime('%Y-%m-%d %H:%M:%S') if v else None
        }
