# app/core/rbac.py
# Role-Based Access Control definitions and enforcement

from enum import Enum
from typing import Optional
from pydantic import BaseModel


class Role(str, Enum):
    ADMIN = "admin"
    FINANCE = "finance"
    HR = "hr"
    ENGINEERING = "engineering"
    LEGAL = "legal"
    SALES = "sales"
    VIEWER = "viewer"


# Data source tags used when indexing documents
class DataSource(str, Enum):
    FINANCE_REPORTS = "finance_reports"
    HR_RECORDS = "hr_records"
    ENGINEERING_DOCS = "engineering_docs"
    LEGAL_CONTRACTS = "legal_contracts"
    SALES_DATA = "sales_data"
    COMPLIANCE = "compliance"
    OPERATIONAL = "operational"
    PUBLIC = "public"


# Which data sources each role can access
ROLE_PERMISSIONS: dict[str, list[str]] = {
    Role.ADMIN: [s.value for s in DataSource],  # full access
    Role.FINANCE: [
        DataSource.FINANCE_REPORTS.value,
        DataSource.COMPLIANCE.value,
        DataSource.OPERATIONAL.value,
        DataSource.PUBLIC.value,
    ],
    Role.HR: [
        DataSource.HR_RECORDS.value,
        DataSource.COMPLIANCE.value,
        DataSource.PUBLIC.value,
    ],
    Role.ENGINEERING: [
        DataSource.ENGINEERING_DOCS.value,
        DataSource.OPERATIONAL.value,
        DataSource.PUBLIC.value,
    ],
    Role.LEGAL: [
        DataSource.LEGAL_CONTRACTS.value,
        DataSource.COMPLIANCE.value,
        DataSource.HR_RECORDS.value,
        DataSource.PUBLIC.value,
    ],
    Role.SALES: [
        DataSource.SALES_DATA.value,
        DataSource.OPERATIONAL.value,
        DataSource.PUBLIC.value,
    ],
    Role.VIEWER: [DataSource.PUBLIC.value],
}


# Synthetic user registry (replace with real auth in production)
USERS: dict[str, dict] = {
    "alice": {"password": "alice123", "role": Role.FINANCE, "name": "Alice Chen"},
    "bob": {"password": "bob123", "role": Role.HR, "name": "Bob Martinez"},
    "carol": {"password": "carol123", "role": Role.ENGINEERING, "name": "Carol Singh"},
    "dave": {"password": "dave123", "role": Role.LEGAL, "name": "Dave Kim"},
    "eve": {"password": "eve123", "role": Role.SALES, "name": "Eve Thompson"},
    "frank": {"password": "frank123", "role": Role.ADMIN, "name": "Frank Admin"},
    "guest": {"password": "guest123", "role": Role.VIEWER, "name": "Guest User"},
}


class UserContext(BaseModel):
    username: str
    name: str
    role: Role
    allowed_sources: list[str]


def authenticate_user(username: str, password: str) -> Optional[UserContext]:
    user = USERS.get(username)
    if not user or user["password"] != password:
        return None
    role = user["role"]
    return UserContext(
        username=username,
        name=user["name"],
        role=role,
        allowed_sources=ROLE_PERMISSIONS.get(role, [DataSource.PUBLIC.value]),
    )


def get_allowed_sources(role: Role) -> list[str]:
    return ROLE_PERMISSIONS.get(role, [DataSource.PUBLIC.value])


def can_access_source(role: Role, source: str) -> bool:
    return source in ROLE_PERMISSIONS.get(role, [])
