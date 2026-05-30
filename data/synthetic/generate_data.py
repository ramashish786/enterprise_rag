#!/usr/bin/env python3
# data/synthetic/generate_data.py
# Generates synthetic enterprise datasets for all data source types

import json
import csv
import os
import random
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent
random.seed(42)


# ─── Finance Reports ──────────────────────────────────────────────────────────

def generate_finance_report():
    content = """ACME Corp — Q1 2024 Financial Report
Prepared by: Finance Department | Confidential

EXECUTIVE SUMMARY
Total Revenue: $48.7M (+12% YoY)
Operating Expenses: $31.2M
EBITDA: $17.5M (36% margin)
Net Profit: $11.8M

REVENUE BREAKDOWN
- Product Sales: $29.1M (59.7%)
- Professional Services: $12.4M (25.5%)
- Licensing & Subscriptions: $7.2M (14.8%)

EXPENSE CATEGORIES
- R&D: $9.8M (31% of OpEx)
- Sales & Marketing: $8.4M (27%)
- General & Administrative: $6.5M (21%)
- Infrastructure & Cloud: $6.5M (21%)

BUDGET VARIANCE
Q1 revenue exceeded forecast by $2.3M (5% positive variance).
Cloud infrastructure costs were $0.8M over budget due to increased compute usage.
Hiring in engineering department is 2 months behind plan (cost savings: $1.1M).

FORECAST Q2 2024
Projected Revenue: $51.2M
Key risks: enterprise deal slippage, FX headwinds in EMEA.

CASH POSITION
Cash & Equivalents: $84.3M
Accounts Receivable: $18.7M (DSO: 47 days)
Accounts Payable: $9.2M
"""
    with open(OUTPUT_DIR / "q1_2024_finance_report.txt", "w") as f:
        f.write(content)
    print("  ✓ q1_2024_finance_report.txt")


def generate_finance_csv():
    rows = [
        ["Department", "Budget_USD", "Actual_USD", "Variance_USD", "Status"],
        ["Engineering", 12000000, 11400000, 600000, "Under Budget"],
        ["Sales", 8500000, 8900000, -400000, "Over Budget"],
        ["Marketing", 4200000, 3980000, 220000, "Under Budget"],
        ["HR", 2100000, 2050000, 50000, "On Track"],
        ["Legal", 1800000, 1760000, 40000, "On Track"],
        ["Infrastructure", 6500000, 7300000, -800000, "Over Budget"],
        ["Finance", 1200000, 1180000, 20000, "On Track"],
        ["Operations", 3000000, 2950000, 50000, "On Track"],
    ]
    with open(OUTPUT_DIR / "department_budgets_q1_2024.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    print("  ✓ department_budgets_q1_2024.csv")


# ─── HR Records ───────────────────────────────────────────────────────────────

def generate_hr_records():
    employees = []
    depts = ["Engineering", "Sales", "Finance", "HR", "Legal", "Marketing", "Operations"]
    levels = ["L1", "L2", "L3", "L4", "L5"]
    statuses = ["Active", "Active", "Active", "On Leave", "Probation"]
    names = [
        "James Li", "Maria Garcia", "David Okonkwo", "Priya Patel", "Tom Andersen",
        "Fatima Al-Hassan", "Chris Wong", "Anna Kowalski", "Raj Kumar", "Sarah O'Brien",
        "Michael Cho", "Elena Rossi", "Samuel Adeyemi", "Yuki Tanaka", "Laura Dubois",
    ]
    for i, name in enumerate(names, 1):
        employees.append({
            "employee_id": f"EMP{1000+i}",
            "name": name,
            "department": depts[i % len(depts)],
            "level": levels[i % len(levels)],
            "annual_salary_usd": random.randint(70, 180) * 1000,
            "start_date": f"202{random.randint(0,3)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
            "status": statuses[i % len(statuses)],
            "performance_rating": round(random.uniform(2.5, 5.0), 1),
            "annual_leave_days_remaining": random.randint(0, 25),
        })
    with open(OUTPUT_DIR / "employee_records.json", "w") as f:
        json.dump(employees, f, indent=2)
    print("  ✓ employee_records.json")


def generate_hr_policy():
    content = """ACME Corp Human Resources Policy Manual
Version 3.2 | Effective: January 2024 | Confidential

LEAVE POLICY
Annual Leave: All full-time employees receive 25 days per calendar year.
Sick Leave: 10 days per year, no carry-forward.
Parental Leave: 16 weeks primary caregiver, 6 weeks secondary caregiver.
Carry-forward: Maximum 10 days may be carried into the following year.

PERFORMANCE REVIEW CYCLE
Reviews occur bi-annually: June and December.
Rating scale: 1.0 (Needs Improvement) to 5.0 (Exceptional).
Employees rated below 2.5 enter a 90-day Performance Improvement Plan (PIP).
Promotions require rating of 4.0+ for two consecutive cycles.

COMPENSATION BANDS (2024)
L1: $65,000 – $85,000
L2: $85,000 – $110,000
L3: $110,000 – $145,000
L4: $145,000 – $190,000
L5: $190,000 – $250,000

ONBOARDING PROCESS
Week 1: IT setup, security training, HR orientation.
Week 2-4: Role-specific onboarding with assigned buddy.
Day 90: First check-in with manager and HR business partner.

DISCIPLINARY PROCEDURE
Step 1: Verbal warning (documented).
Step 2: Written warning.
Step 3: Final written warning with PIP.
Step 4: Termination with cause.

REMOTE WORK POLICY
Employees may work remotely up to 3 days per week with manager approval.
Fully remote roles require VP sign-off and quarterly in-office visits.
"""
    with open(OUTPUT_DIR / "hr_policy_manual.txt", "w") as f:
        f.write(content)
    print("  ✓ hr_policy_manual.txt")


# ─── Engineering Docs ─────────────────────────────────────────────────────────

def generate_engineering_docs():
    content = """ACME Platform Architecture — Internal Engineering Documentation
Version 2.1 | Owner: Platform Team | Last Updated: March 2024

SYSTEM OVERVIEW
The ACME platform is built on a microservices architecture deployed on AWS EKS.
Core services communicate over gRPC internally and expose REST APIs externally.

SERVICES INVENTORY
- auth-service: OAuth2/JWT token issuance, 99.95% SLA
- user-service: User profile management, PostgreSQL backend
- payment-service: Stripe integration, PCI-DSS compliant
- notification-service: Email/SMS via SendGrid/Twilio
- analytics-service: ClickHouse OLAP backend, real-time dashboards
- rag-service: Internal document Q&A (this system)

INFRASTRUCTURE
Cloud: AWS (primary), GCP (ML workloads)
Orchestration: Kubernetes 1.29, Helm 3
CI/CD: GitHub Actions → ArgoCD
Observability: Datadog APM, PagerDuty alerts
Databases: PostgreSQL 15, Redis 7, ClickHouse 23.8

DEPLOYMENT PROCEDURE
1. PR merged to main → GitHub Actions runs tests (unit, integration, e2e)
2. Docker image built and pushed to ECR with SHA tag
3. Helm values updated in gitops-repo → ArgoCD syncs within 5 min
4. Smoke tests run automatically post-deploy
5. Rollback: `kubectl rollout undo deployment/<name>` or ArgoCD UI

KNOWN ISSUES (Q1 2024)
- auth-service memory leak under sustained 2000+ RPS (P1, ETA fix: 2024-04-15)
- analytics-service query timeout at >10M row scans (workaround: add date filter)
- notification-service: SendGrid rate limit at 100k emails/hr (mitigation: queue)

API RATE LIMITS (External)
- Standard tier: 100 req/min
- Professional tier: 1000 req/min
- Enterprise tier: Custom (contact sales)

SECURITY
All inter-service communication uses mTLS.
Secrets managed via AWS Secrets Manager.
Penetration test last conducted: December 2023 (no critical findings).
"""
    with open(OUTPUT_DIR / "platform_architecture.txt", "w") as f:
        f.write(content)
    print("  ✓ platform_architecture.txt")


# ─── JSON Logs / Audit Trail ──────────────────────────────────────────────────

def generate_audit_logs():
    log_types = ["LOGIN", "QUERY", "DOCUMENT_ACCESS", "PERMISSION_CHANGE", "DATA_EXPORT"]
    users = ["alice", "bob", "carol", "dave", "eve", "frank"]
    logs = []
    for i in range(50):
        logs.append({
            "event_id": f"EVT{10000+i}",
            "timestamp": f"2024-03-{random.randint(1,31):02d}T{random.randint(0,23):02d}:{random.randint(0,59):02d}:00Z",
            "event_type": random.choice(log_types),
            "user": random.choice(users),
            "ip_address": f"192.168.{random.randint(1,5)}.{random.randint(1,254)}",
            "resource": random.choice(["finance_reports", "hr_records", "engineering_docs", "legal_contracts"]),
            "status": random.choice(["SUCCESS", "SUCCESS", "SUCCESS", "DENIED", "FAILED"]),
            "details": f"Action performed on resource",
        })
    with open(OUTPUT_DIR / "audit_trail.json", "w") as f:
        json.dump(logs, f, indent=2)
    print("  ✓ audit_trail.json")


# ─── Legal Contracts ──────────────────────────────────────────────────────────

def generate_legal_doc():
    content = """MASTER SERVICE AGREEMENT — ACME Corp & Nexus Ventures Ltd
Contract ID: MSA-2024-0042 | Effective: 1 January 2024 | Confidential

PARTIES
This Master Service Agreement ("Agreement") is entered into between ACME Corp
("Service Provider") and Nexus Ventures Ltd ("Client").

SCOPE OF SERVICES
Service Provider agrees to deliver software platform services as described in
the applicable Statement of Work (SOW). Initial SOW covers:
- Access to ACME SaaS platform (Professional tier)
- Up to 500 user seats
- Standard API access (1000 req/min)
- 99.9% uptime SLA with 1-hour RTO

PAYMENT TERMS
Annual contract value: $240,000 USD
Payment schedule: Quarterly in advance ($60,000 per quarter)
Late payment interest: 1.5% per month on outstanding balance
Currency: USD; international wire transfers accepted.

LIABILITY AND INDEMNIFICATION
Service Provider liability is capped at 12 months of fees paid.
Client indemnifies Service Provider against claims arising from Client data.
Neither party liable for indirect, consequential, or punitive damages.

DATA PROTECTION
Service Provider is GDPR compliant (EU Standard Contractual Clauses attached).
Data Processing Agreement (DPA) incorporated by reference (Exhibit B).
Client data retained for 90 days post-termination then permanently deleted.

TERMINATION
Either party may terminate with 90 days written notice.
Service Provider may terminate immediately for material breach not cured within 30 days.
Client data export available for 30 days post-termination.

GOVERNING LAW
This Agreement is governed by the laws of the State of Delaware, USA.
Disputes resolved by binding arbitration under AAA Commercial Rules.

CONFIDENTIALITY
Both parties agree to keep terms confidential for 3 years post-termination.
"""
    with open(OUTPUT_DIR / "msa_nexus_ventures_2024.txt", "w") as f:
        f.write(content)
    print("  ✓ msa_nexus_ventures_2024.txt")


# ─── Sales Data ───────────────────────────────────────────────────────────────

def generate_sales_data():
    rows = [
        ["Deal_ID", "Account", "ACV_USD", "Stage", "Close_Date", "Owner", "Probability_Pct"],
        ["DL-001", "TechGiant Corp", 480000, "Negotiation", "2024-03-31", "Eve Thompson", 75],
        ["DL-002", "GlobalBank Ltd", 220000, "Proposal", "2024-04-15", "Eve Thompson", 50],
        ["DL-003", "HealthSys Inc", 95000, "Discovery", "2024-05-30", "Mark Johnson", 25],
        ["DL-004", "RetailMax Co", 360000, "Closed Won", "2024-02-28", "Eve Thompson", 100],
        ["DL-005", "StartupX", 42000, "Proposal", "2024-04-01", "Anna Lee", 60],
        ["DL-006", "MegaCorp", 1200000, "Negotiation", "2024-06-30", "Eve Thompson", 65],
        ["DL-007", "EduTech Ltd", 78000, "Closed Won", "2024-01-15", "Mark Johnson", 100],
        ["DL-008", "FinancePro", 540000, "Discovery", "2024-07-31", "Anna Lee", 20],
        ["DL-009", "GovSector Agency", 290000, "Proposal", "2024-05-15", "Mark Johnson", 45],
        ["DL-010", "InsuranceCo", 175000, "Closed Lost", "2024-02-01", "Anna Lee", 0],
    ]
    with open(OUTPUT_DIR / "sales_pipeline_q1_2024.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    print("  ✓ sales_pipeline_q1_2024.csv")


# ─── Compliance / Public ──────────────────────────────────────────────────────

def generate_compliance_doc():
    content = """ACME Corp — Data Governance & Compliance Policy
Version 1.5 | Effective: Q1 2024 | Classification: Internal

GDPR COMPLIANCE
ACME Corp processes personal data of EU residents under GDPR (Regulation 2016/679).
Legal basis for processing: Contract performance, Legitimate interests, Consent.
Data Protection Officer (DPO): legal-dpo@acmecorp.com
Annual DPIA (Data Protection Impact Assessment) completed: January 2024.

SOX COMPLIANCE
As a publicly traded entity, ACME Corp complies with Sarbanes-Oxley Act Section 404.
Internal controls reviewed quarterly by Finance and Internal Audit.
External audit performed annually by Grant & Partners LLP.
Audit findings Q1 2024: No material weaknesses identified.

DATA RETENTION SCHEDULE
Customer PII: 7 years post-contract end
Financial records: 10 years (IRS requirement)
HR records: 7 years post-employment
System logs: 12 months (security), 36 months (audit)
Legal holds: Indefinite until hold released

INCIDENT RESPONSE
P0 (Critical breach): 1-hour response, 72-hour GDPR notification obligation.
P1 (High): 4-hour response, internal stakeholder notification within 24 hours.
P2 (Medium): 24-hour response.
Security contact: security@acmecorp.com | +1-555-0199 (24/7 hotline)

ACCESS CONTROL POLICY
Principle of least privilege enforced across all systems.
Privileged access reviews conducted quarterly.
MFA mandatory for all employees with system access.
Third-party vendor access reviewed annually.
"""
    with open(OUTPUT_DIR / "compliance_policy.txt", "w") as f:
        f.write(content)
    print("  ✓ compliance_policy.txt")


def generate_pdf_report():
    """Generate a real PDF financial report."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
    except ImportError:
        print("  ⚠ reportlab not installed; skipping PDF")
        return

    pdf_path = OUTPUT_DIR / "annual_report_2023.pdf"
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("<b>ACME Corp Annual Report 2023</b>", styles["Title"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Filed with SEC | Confidential Distribution", styles["Italic"]))
    story.append(Spacer(1, 20))

    sections = [
        ("Executive Summary",
         "ACME Corp delivered record results in fiscal year 2023, achieving total revenue of "
         "$182.4M, representing 24% year-over-year growth. EBITDA margins improved to 34%, "
         "driven by operational leverage and disciplined cost management. The company exited "
         "2023 with $84.3M in cash, no debt, and a robust pipeline entering 2024."),
        ("Revenue Breakdown",
         "Product Sales contributed $108.7M (60%), Professional Services $46.5M (25%), and "
         "Licensing $27.2M (15%). EMEA revenue grew 38% YoY, outpacing AMER at 19%. The top "
         "10 customers represent 28% of total revenue, down from 34% in 2022, indicating "
         "healthy customer diversification."),
        ("Operating Expenses",
         "Total OpEx was $120.5M. R&D investment increased 31% to $38.2M, reflecting "
         "commitment to platform innovation. Sales & Marketing was $32.8M, with CAC payback "
         "improving to 14 months. G&A held flat at $24.1M despite headcount growth, "
         "demonstrating operating efficiency."),
        ("Risk Factors",
         "Key risks include foreign exchange exposure in EMEA, dependency on cloud providers "
         "(AWS represents 78% of infrastructure spend), and ongoing regulatory scrutiny under "
         "GDPR and emerging AI legislation. Management has implemented hedging strategies and "
         "multi-cloud initiatives to mitigate these exposures."),
        ("Outlook 2024",
         "Management expects revenue between $215M-$230M (18-26% growth), with EBITDA margin "
         "expansion to 36-38%. Capital expenditure plans of $14M support infrastructure scale, "
         "and we expect to add 120 net new employees, primarily in engineering and customer "
         "success roles."),
    ]
    for heading, body in sections:
        story.append(Paragraph(f"<b>{heading}</b>", styles["Heading2"]))
        story.append(Paragraph(body, styles["BodyText"]))
        story.append(Spacer(1, 12))

    doc.build(story)
    print("  ✓ annual_report_2023.pdf")


def generate_access_policies():
    """Metadata + access policy file (JSON)."""
    policies = {
        "policy_version": "2024.Q1",
        "last_updated": "2024-03-15",
        "data_classification": {
            "finance_reports": {
                "classification": "Confidential",
                "encryption_required": True,
                "retention_years": 7,
                "allowed_roles": ["admin", "finance"],
                "owner": "CFO Office",
            },
            "hr_records": {
                "classification": "Highly Confidential - PII",
                "encryption_required": True,
                "retention_years": 7,
                "allowed_roles": ["admin", "hr", "legal"],
                "owner": "Head of People",
            },
            "engineering_docs": {
                "classification": "Internal",
                "encryption_required": False,
                "retention_years": 5,
                "allowed_roles": ["admin", "engineering"],
                "owner": "VP Engineering",
            },
            "legal_contracts": {
                "classification": "Highly Confidential",
                "encryption_required": True,
                "retention_years": 10,
                "allowed_roles": ["admin", "legal"],
                "owner": "General Counsel",
            },
            "sales_data": {
                "classification": "Confidential",
                "encryption_required": True,
                "retention_years": 5,
                "allowed_roles": ["admin", "sales"],
                "owner": "CRO Office",
            },
            "compliance": {
                "classification": "Internal",
                "encryption_required": False,
                "retention_years": 10,
                "allowed_roles": ["admin", "finance", "hr", "legal"],
                "owner": "Compliance Team",
            },
            "operational": {
                "classification": "Internal",
                "encryption_required": False,
                "retention_years": 3,
                "allowed_roles": ["admin", "finance", "engineering", "sales"],
                "owner": "COO Office",
            },
            "public": {
                "classification": "Public",
                "encryption_required": False,
                "retention_years": 2,
                "allowed_roles": ["admin", "finance", "hr", "engineering", "legal", "sales", "viewer"],
                "owner": "Marketing",
            },
        },
    }
    with open(OUTPUT_DIR / "access_policies.json", "w") as f:
        json.dump(policies, f, indent=2)
    print("  ✓ access_policies.json")


def generate_user_role_mappings():
    """User-role mapping CSV."""
    rows = [
        ["username", "full_name", "role", "department", "join_date", "status"],
        ["alice", "Alice Chen", "finance", "Finance", "2021-03-15", "active"],
        ["bob", "Bob Martinez", "hr", "People", "2020-08-01", "active"],
        ["carol", "Carol Singh", "engineering", "Platform", "2022-01-10", "active"],
        ["dave", "Dave Kim", "legal", "Legal", "2019-11-20", "active"],
        ["eve", "Eve Thompson", "sales", "Revenue", "2023-04-05", "active"],
        ["frank", "Frank Admin", "admin", "IT Operations", "2018-06-01", "active"],
        ["guest", "Guest User", "viewer", "External", "2024-01-01", "active"],
    ]
    with open(OUTPUT_DIR / "user_role_mappings.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    print("  ✓ user_role_mappings.csv")


if __name__ == "__main__":
    print("Generating synthetic enterprise datasets...")
    generate_finance_report()
    generate_finance_csv()
    generate_hr_records()
    generate_hr_policy()
    generate_engineering_docs()
    generate_audit_logs()
    generate_legal_doc()
    generate_sales_data()
    generate_compliance_doc()
    generate_pdf_report()
    generate_access_policies()
    generate_user_role_mappings()
    print("\n✅ All synthetic datasets generated in:", OUTPUT_DIR)
    print("\nNext step: run  python scripts/ingest_all.py  to index everything.")
