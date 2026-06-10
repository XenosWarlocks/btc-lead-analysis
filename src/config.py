"""Central configuration: domain lists, title taxonomies, scoring weights."""

# ---------------------------------------------------------------------------
# Email intelligence
# ---------------------------------------------------------------------------
PERSONAL_EMAIL_DOMAINS = {
    "gmail.com", "googlemail.com", "yahoo.com", "yahoo.co.in", "yahoo.co.uk",
    "yahoo.co.kr", "yahoo.com.br", "yahoo.fr", "ymail.com", "rocketmail.com",
    "outlook.com", "outlook.in", "hotmail.com", "hotmail.co.uk", "hotmail.fr",
    "live.com", "live.in", "msn.com", "icloud.com", "me.com", "mac.com",
    "aol.com", "protonmail.com", "proton.me", "pm.me", "zoho.com", "zohomail.in",
    "rediffmail.com", "rediff.com", "mail.com", "gmx.com", "gmx.de", "gmx.net",
    "yandex.com", "yandex.ru", "naver.com", "hanmail.net", "daum.net",
    "nate.com", "qq.com", "163.com", "126.com", "sina.com", "web.de",
    "fastmail.com", "hey.com", "tutanota.com", "mailinator.com",
}

DISPOSABLE_EMAIL_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "10minutemail.com", "tempmail.com",
    "temp-mail.org", "throwaway.email", "yopmail.com", "getnada.com",
    "trashmail.com", "sharklasers.com", "dispostable.com", "maildrop.cc",
}

# Academic TLD suffixes / fragments => strong student / academia signal
ACADEMIC_DOMAIN_PATTERNS = (
    ".edu", ".ac.in", ".ac.uk", ".ac.kr", ".ac.jp", ".edu.in", ".edu.au",
    ".edu.cn", ".ac.za", ".edu.sg", ".edu.my", ".edu.pk", ".edu.bd",
)

EMAIL_REGEX = r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$"

# ---------------------------------------------------------------------------
# Contact classification (rule tiers). Patterns are matched as whole words,
# case-insensitively, against the normalized designation.
# Order inside each tuple matters only for confidence reporting.
# ---------------------------------------------------------------------------
FOUNDER_PATTERNS = (
    "founder", "co founder", "cofounder", "co-founder", "founding partner",
    "founding member", "owner", "proprietor", "entrepreneur", "promoter",
)

C_LEVEL_PATTERNS = (
    "ceo", "cto", "cfo", "coo", "cmo", "cio", "ciso", "cso", "cpo", "cdo",
    "chro", "cro", "cbo", "cco", "chief executive", "chief technology",
    "chief technical", "chief financial", "chief operating", "chief marketing",
    "chief information", "chief security", "chief product", "chief data",
    "chief revenue", "chief people", "chief business", "chief strategy",
    "managing director", "executive director", "president", "chairman",
    "chairperson", "managing partner", "general manager",
)

VP_DIRECTOR_PATTERNS = (
    "vice president", "vp", "svp", "evp", "avp", "director", "head of",
    "department head", "national head", "regional head", "global head",
    "principal", "partner", "associate director", "deputy director",
)

MANAGER_PATTERNS = (
    "manager", "team lead", "team leader", "lead", "supervisor",
    "project lead", "tech lead", "scrum master", "product owner",
)

STUDENT_PATTERNS = (
    "student", "intern", "internship", "trainee", "undergraduate",
    "graduate student", "post graduate", "postgraduate", "phd candidate",
    "phd scholar", "phd student", "doctoral", "research scholar",
    "research fellow", "fellow", "fellowship", "campus ambassador",
    "fresher", "fresh graduate", "recent graduate", "mba candidate",
    "mba student", "btech", "b.tech", "mtech", "m.tech", "bca", "mca",
    "bba", "b.e", "m.e", "pursuing", "aspirant", "learner", "apprentice",
    "scholar", "studying", "final year", "pre final year",
)

# Job-words that confirm a real (non-student) employee when nothing senior
# matches. Anything else falls through to "Unknown".
EMPLOYEE_PATTERNS = (
    "engineer", "developer", "designer", "analyst", "consultant", "architect",
    "executive", "officer", "specialist", "scientist", "administrator",
    "accountant", "auditor", "advisor", "associate", "technician", "writer",
    "marketer", "recruiter", "salesperson", "representative", "coordinator",
    "strategist", "researcher", "professor", "teacher", "lecturer", "doctor",
    "nurse", "lawyer", "advocate", "banker", "trader", "freelancer",
    "programmer", "tester", "devops", "sre", "hr", "operations", "sales",
    "marketing", "finance", "support", "developer relations",
)

# Canonical titles used by the RapidFuzz fallback when no rule fires
# (catches typos like "Maneger", "Founedr", "Studnet").
FUZZY_CANONICAL_TITLES = {
    "founder": "Founder",
    "co-founder": "Founder",
    "owner": "Founder",
    "ceo": "C-Level",
    "chief executive officer": "C-Level",
    "managing director": "C-Level",
    "cto": "C-Level",
    "president": "C-Level",
    "vice president": "VP / Director",
    "director": "VP / Director",
    "head of department": "VP / Director",
    "manager": "Manager",
    "team lead": "Manager",
    "software engineer": "Employee",
    "engineer": "Employee",
    "developer": "Employee",
    "designer": "Employee",
    "analyst": "Employee",
    "consultant": "Employee",
    "student": "Student",
    "intern": "Student",
    "trainee": "Student",
    "research scholar": "Student",
}
FUZZY_MATCH_THRESHOLD = 85  # token_set_ratio score out of 100 (catches 1-typo words)

# Company-name fragments indicating an educational institution.
EDU_COMPANY_PATTERNS = (
    "university", "institute of technology", "institute", "college", "school",
    "academy", "polytechnic", "iit ", "nit ", "iiit", "iim ", "vidyalaya",
    "vishwavidyalaya", "campus", "faculty of",
)

# ---------------------------------------------------------------------------
# Company-name normalization: legal suffixes stripped to build a match key.
# ---------------------------------------------------------------------------
COMPANY_LEGAL_SUFFIXES = (
    "private limited", "pvt ltd", "pvt. ltd.", "pvt. ltd", "pvt.ltd",
    "pvt limited", "p ltd", "limited", "ltd", "llp", "llc", "inc", "inc.",
    "corp", "corp.", "corporation", "co ltd", "co., ltd.", "co.,ltd.",
    "co.,ltd", "co., ltd", "company", "gmbh", "s.a.", "sa", "plc", "pte ltd",
    "pte. ltd.", "technologies", "technology", "tech", "solutions",
    "services", "group",
)

# Designation abbreviation expansion (applied before classification).
TITLE_ABBREVIATIONS = {
    "sr": "senior", "sr.": "senior", "jr": "junior", "jr.": "junior",
    "mgr": "manager", "engg": "engineering", "engr": "engineer",
    "asst": "assistant", "assoc": "associate", "dir": "director",
    "exec": "executive", "mktg": "marketing", "dev": "developer",
    "info": "information", "tech": "technology", "ops": "operations",
}

# ---------------------------------------------------------------------------
# Phone country-code -> country (used when `country` column is empty).
# Covers the codes most common in this dataset; extend as needed.
# ---------------------------------------------------------------------------
PHONE_COUNTRY_CODES = {
    "1": "United States / Canada", "7": "Russia", "20": "Egypt",
    "27": "South Africa", "30": "Greece", "31": "Netherlands", "32": "Belgium",
    "33": "France", "34": "Spain", "36": "Hungary", "39": "Italy",
    "40": "Romania", "41": "Switzerland", "43": "Austria", "44": "United Kingdom",
    "45": "Denmark", "46": "Sweden", "47": "Norway", "48": "Poland",
    "49": "Germany", "52": "Mexico", "55": "Brazil", "60": "Malaysia",
    "61": "Australia", "62": "Indonesia", "63": "Philippines", "65": "Singapore",
    "66": "Thailand", "81": "Japan", "82": "South Korea", "84": "Vietnam",
    "86": "China", "90": "Turkey", "91": "India", "92": "Pakistan",
    "93": "Afghanistan", "94": "Sri Lanka", "95": "Myanmar", "98": "Iran",
    "212": "Morocco", "234": "Nigeria", "254": "Kenya", "263": "Zimbabwe",
    "352": "Luxembourg", "353": "Ireland", "358": "Finland", "372": "Estonia",
    "380": "Ukraine", "420": "Czech Republic", "852": "Hong Kong",
    "880": "Bangladesh", "886": "Taiwan", "960": "Maldives", "961": "Lebanon",
    "962": "Jordan", "965": "Kuwait", "966": "Saudi Arabia",
    "968": "Oman", "971": "United Arab Emirates", "972": "Israel",
    "973": "Bahrain", "974": "Qatar", "975": "Bhutan", "977": "Nepal",
}

# Country-name normalization (common variants -> canonical).
COUNTRY_ALIASES = {
    "india": "India", "in": "India", "bharat": "India",
    "usa": "United States", "us": "United States", "u.s.": "United States",
    "u.s.a.": "United States", "united states of america": "United States",
    "america": "United States", "uk": "United Kingdom", "u.k.": "United Kingdom",
    "great britain": "United Kingdom", "england": "United Kingdom",
    "uae": "United Arab Emirates", "korea": "South Korea",
    "republic of korea": "South Korea", "korea, south": "South Korea",
    "south korea": "South Korea",
}

# ---------------------------------------------------------------------------
# Lead scoring (0-100). Score = BASE + sum(applicable weights), clipped.
# ---------------------------------------------------------------------------
SCORE_BASE = 30
SCORE_WEIGHTS = {
    # positive signals
    "corporate_email": 15,
    "company_present": 10,
    "linkedin_present": 10,
    "title_founder": 20,
    "title_c_level": 18,
    "title_vp_director": 12,
    "title_manager": 6,
    "valid_mobile": 3,
    "country_known": 2,
    # negative signals
    "student": -35,
    "personal_email": -8,
    "invalid_email": -20,
    "missing_company": -15,
    "missing_designation": -10,
    "suspicious": -10,
}
HIGH_VALUE_THRESHOLD = 80
LOW_VALUE_THRESHOLD = 40

# Columns the dashboard treats as the canonical schema after the pipeline.
CANONICAL_COLUMNS = [
    "user_id", "username", "email", "email_domain", "email_type",
    "email_valid", "designation", "designation_norm", "contact_type",
    "student_flag", "confidence_score", "company", "company_norm",
    "is_edu_company", "country", "city", "mobile", "mobile_valid",
    "linkedin", "instagram", "twitter", "has_linkedin", "suspicious_flag",
    "completeness", "lead_score", "source_file",
]
