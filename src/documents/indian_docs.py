"""Known Indian document type patterns with multilingual keywords."""

from __future__ import annotations

INDIAN_DOC_PATTERNS: dict[str, list[str]] = {
    "aadhaar_card": [
        "aadhaar", "aadhar", "uid", "unique identification",
        "unique identity", "uidai", "आधार", "विशिष्ट पहचान",
        "enrollment no", "vid",
    ],
    "pan_card": [
        "permanent account number", "income tax", "pan",
        "पैन", "पैन कार्ड", "आयकर विभाग",
        "income tax department", "govt of india",
    ],
    "passport": [
        "passport", "republic of india", "पासपोर्ट",
        "ministry of external affairs", "nationality", "place of birth",
        "date of expiry", "passport no",
    ],
    "voter_id": [
        "election commission", "voter", "electoral", "मतदाता",
        "मतदाता पहचान पत्र", "epic", "electors photo identity card",
        "chief electoral officer",
    ],
    "driving_license": [
        "driving licence", "driving license", "transport",
        "ड्राइविंग", "ड्राइविंग लाइसेंस", "motor vehicles act",
        "dl no", "rto", "regional transport",
    ],
    "bank_statement": [
        "statement of account", "transaction", "balance",
        "बैंक", "बैंक स्टेटमेंट", "account number",
        "ifsc", "credit", "debit", "closing balance",
        "opening balance", "account statement",
    ],
    "salary_slip": [
        "salary", "payslip", "pay slip", "earnings", "deductions",
        "वेतन", "वेतन पर्ची", "basic pay", "hra",
        "provident fund", "pf", "tds", "net pay",
        "gross salary", "ctc", "employee id",
    ],
    "itr": [
        "income tax return", "itr", "assessment year",
        "आयकर", "आयकर रिटर्न", "taxpayer", "tax liability",
        "gross total income", "schedule", "acknowledgement",
        "return of income", "form itr",
    ],
    "form_16": [
        "form 16", "tds certificate", "employer",
        "certificate of deduction", "tax deducted at source",
        "annual statement", "financial year",
    ],
    "marksheet": [
        "mark sheet", "marksheet", "result", "examination",
        "university", "अंकपत्र", "गुणपत्रिका", "board",
        "roll number", "subject", "marks obtained",
        "total marks", "percentage", "grade",
    ],
    "insurance": [
        "insurance", "policy", "premium", "बीमा",
        "sum assured", "maturity", "nominee", "insured",
        "policyholder", "life insurance", "health insurance",
        "motor insurance",
    ],
    "rental_agreement": [
        "rent agreement", "rental agreement", "tenant", "landlord",
        "किरायानामा", "भाड़ा अनुबंध", "lease deed", "lessor",
        "lessee", "monthly rent", "security deposit",
        "notice period",
    ],
}
