from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, EmailStr, HttpUrl


class User(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None


class PageSection(BaseModel):
    name: str
    path: str


class JobStatus(BaseModel):
    job_id: str
    status: str
    tasks: List[Dict[str, Any]]


class JobSubmission(BaseModel):
    pageType: str
    companyName: str
    companyUrl: HttpUrl
    companyDescription: str
    seedKeywords: Union[str, List[str]]
    locations: Union[str, List[str]]
    pageUrl: HttpUrl
    pageTitle: str
    pageInfo: str
    pageUsp: str
    isNewPage: bool


class KeywordData(BaseModel):
    keyword: str
    search_volume: int
    cpc: float
    competition: float


class KeywordResponse(BaseModel):
    keywords: List[KeywordData]


# Add more models as needed for your specific application requirements
