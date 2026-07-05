"""
Pydantic request/response models for the HaqDar FastAPI backend.

Keeping these separate from agents/state.py on purpose: HaqDarState is the
internal LangGraph state shape (drives graph execution), while these models
are the external API contract (drive validation of what untrusted clients
are allowed to send us). The two are related but should be allowed to drift —
e.g. we can tighten a field's validation here without touching the graph.
"""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


class UserDetails(BaseModel):
    """Consumer's own sender-block details. All optional — any left blank
    renders as a [PLACEHOLDER] in the letter, same behavior as before."""

    user_name: Optional[str] = Field(default="", max_length=120)
    user_address: Optional[str] = Field(default="", max_length=300)
    user_city_postal: Optional[str] = Field(default="", max_length=120)
    user_email: Optional[str] = Field(default="", max_length=120)
    user_phone: Optional[str] = Field(default="", max_length=40)

    @field_validator("user_email")
    @classmethod
    def _validate_email_if_present(cls, v):
        if not v:
            return v
        # Lightweight check rather than strict EmailStr — this field is
        # allowed to be blank, and we don't want to hard-fail the whole
        # letter draft over a slightly malformed personal email.
        if "@" not in v or " " in v:
            raise ValueError("user_email doesn't look like a valid email address")
        return v


class AnalyzeComplaintRequest(UserDetails):
    complaint_text: str = Field(..., min_length=1, max_length=4000)


class CitedSection(BaseModel):
    section_no: str
    source: str
    title: str


class LocationInfo(BaseModel):
    found: bool = False
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    maps_link: Optional[str] = None
    reason: Optional[str] = None


class AuthorityInfo(BaseModel):
    forum: Optional[str] = None
    process: Optional[str] = None
    pre_requisite: Optional[str] = None
    location: Optional[LocationInfo] = None


class AnalyzeComplaintResponse(BaseModel):
    clarifying_question: Optional[str] = None
    issue_type: Optional[str] = None
    cited_sections: list[CitedSection] = []
    authority: Optional[AuthorityInfo] = None
    letter_draft: Optional[str] = None
    letter_body: Optional[str] = None


class CompanyLookupRequest(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=200)
    city: Optional[str] = Field(default=None, max_length=80)


class AddressInfo(BaseModel):
    found: bool = False
    address: Optional[str] = None
    source: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    reason: Optional[str] = None


class CompanyLookupResponse(BaseModel):
    company_name: str
    website: Optional[str] = None
    candidate_emails: list[str] = []
    address: AddressInfo
    note: Optional[str] = None
    search_error: Optional[str] = None
    error: Optional[str] = None


class SendLetterRequest(UserDetails):
    letter_body: str = Field(..., min_length=1, max_length=6000)
    issue_type: Optional[str] = Field(default="consumer_complaint", max_length=80)
    shop_name: str = Field(..., min_length=1, max_length=200)
    shop_address: Optional[str] = Field(default="", max_length=300)
    shop_contact: EmailStr


class SendLetterResponse(BaseModel):
    sent: bool
    to: Optional[str] = None
    reason: Optional[str] = None
    final_letter: str


class ErrorResponse(BaseModel):
    detail: str
