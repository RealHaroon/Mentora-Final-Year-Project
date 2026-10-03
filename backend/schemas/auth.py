from enum import Enum

from pydantic import BaseModel, EmailStr, Field


class ExamGoal(str, Enum):
    sindh_university = "sindh_university"
    mehran_university = "mehran_university"
    lums = "lums"
    karachi_university = "karachi_university"
    iqra_university = "iqra_university"
    tando_jam_university = "tando_jam_university"
    mdcat = "mdcat"
    pms_spsc_ppsc = "pms_spsc_ppsc"
    issb = "issb"
    army_navy_paf = "army_navy_paf"


class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str = Field(min_length=8)
    confirm_password: str = Field(min_length=8)
    university: str
    exam_goal: ExamGoal


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    reset_code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")
    new_password: str = Field(min_length=8)
    confirm_password: str = Field(min_length=8)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)
    confirm_password: str = Field(min_length=8)
