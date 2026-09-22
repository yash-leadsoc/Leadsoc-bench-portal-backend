"""Collection names + authenticated-principal wrapper (docs are plain dicts)."""
USERS = "users"
BUS = "business_units"
EMPLOYEES = "employees"
MATERIALS = "materials"
PLANS = "training_plans"
PROGRESS = "training_progress"
ASSESSMENTS = "assessments"
ASSIGNMENTS = "assignments"
RESULTS = "results"
QUESTION_BANKS = "question_banks"
PREP = "prep_assignments"
MOCKS = "mock_interviews"
TRAINERS = "trainers"
PANELS = "panels"
SKILLS = "skill_nodes"
REQUIREMENTS = "requirements"
CANDIDATES = "candidates"
INTERVIEWS = "interview_events"
DEPLOYMENTS = "deployments"
PRACTICES = "practices"
SLA = "sla_rules"
TEMPLATES = "notif_templates"
INTEGRATIONS = "integrations"
NOTIFICATIONS = "notifications"
AUDIT = "audit_logs"
READINESS_CFG = "readiness_config"
PROGRESS_LOGS = "progress_logs"
PREP_MATERIALS = "prep_materials"

LIBRARY = "library_docs"
LIBRARY_QUIZ = "library_quiz"
LIBRARY_PROGRESS = "library_progress"
NOTES = "training_notes"


class User:
    def __init__(self, doc: dict):
        self.id = doc["_id"]
        self.name = doc.get("name", "")
        self.email = doc.get("email", "")
        self.role = doc.get("role")
        self.bu = doc.get("bu")
        self.employee_id = doc.get("employeeId")
        self.cross_bu = doc.get("crossBu", False)
        self.must_change_password = doc.get("mustChangePassword", False)
        self.password_hash = doc.get("passwordHash", "")

    def as_dict(self):
        return {"id": self.id, "name": self.name, "email": self.email,
                "role": self.role, "bu": self.bu, "employeeId": self.employee_id,
                "crossBu": self.cross_bu,
                "mustChangePassword": self.must_change_password}
