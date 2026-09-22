from typing import List, Optional
from pydantic import BaseModel


class LoginIn(BaseModel):
    email: str
    password: str


class ChangePasswordIn(BaseModel):
    currentPassword: str
    newPassword: str


class ProfileIn(BaseModel):
    # Employee-maintained master profile (single source of truth).
    name: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    profilePhoto: Optional[str] = None
    dateOfJoining: Optional[str] = None
    designation: Optional[str] = None
    # professional
    totalExperience: Optional[str] = None
    relevantExperience: Optional[str] = None
    previousExperience: Optional[str] = None
    primaryDomain: Optional[str] = None
    secondaryDomain: Optional[str] = None
    # preferences
    preferredRole: Optional[str] = None
    preferredTechnology: Optional[str] = None
    preferredDomain: Optional[str] = None
    preferredLocation: Optional[str] = None
    secondaryLocation: Optional[str] = None
    willingToRelocate: Optional[bool] = None
    workMode: Optional[str] = None
    # availability
    availabilityType: Optional[str] = None
    availableFrom: Optional[str] = None
    noticePeriod: Optional[str] = None
    # links / docs
    github: Optional[str] = None
    linkedin: Optional[str] = None
    resumeUrl: Optional[str] = None
    # collections
    skills: Optional[List[dict]] = None
    certifications: Optional[List[dict]] = None


class BuIn(BaseModel):
    name: str
    code: str
    practices: List[str] = []
    headName: str
    headEmail: Optional[str] = None
    password: Optional[str] = None


class TaIn(BaseModel):
    name: str
    email: Optional[str] = None
    password: Optional[str] = None
    bu: Optional[str] = None


class EmployeeIn(BaseModel):
    name: str
    employeeId: Optional[str] = None   # fixed id entered by BU (e.g. LS1703)
    email: Optional[str] = None  # login email entered by BU (not auto-generated)
    phone: Optional[str] = None  # mobile number
    password: Optional[str] = None     # optional; defaults to firstname@123
    bu: Optional[str] = None
    practice: str = ""
    targetRole: str = ""
    benchReason: str = ""
    manager: str = ""
    skills: List[dict] = []


class ProgressLogIn(BaseModel):
    materialId: Optional[str] = None
    planId: Optional[str] = None
    note: str = ""
    pct: int = 0
    date: Optional[str] = None


class PrepMaterialIn(BaseModel):
    title: str
    client: str = "General"
    type: str = "link"          # pdf/video/link/doc/other
    url: str = ""
    description: str = ""
    bu: Optional[str] = None


class MaterialIn(BaseModel):
    title: str
    type: str = "link"
    url: str = ""
    downloadUrl: str = ""
    fileName: str = ""
    fileType: str = ""
    skill: str = ""
    bu: Optional[str] = None
    description: str = ""


# class PlanItemIn(BaseModel):
#     materialId: str
#     title: str = ""
#     mandatory: bool = True
#     order: int = 0
#
#
# class PlanIn(BaseModel):
#     name: str
#     bu: Optional[str] = None
#     targetRole: str = ""
#     description: str = ""
#     durationHours: int = 0
#     skills: List[str] = []
#     items: List[PlanItemIn] = []


class PlanItemIn(BaseModel):
    materialId: str = ""          # optional — a module can exist without a material
    title: str = ""               # module name
    mandatory: bool = True
    order: int = 0
    week: int = 0
    duration: str = ""
    assessmentType: str = "None"


class SkillCoveredIn(BaseModel):
    skill: str = ""
    level: str = ""


class PlanIn(BaseModel):
    name: str
    bu: Optional[str] = None
    targetRole: str = ""
    primarySkill: str = ""
    category: str = ""
    difficulty: str = ""
    durationValue: int = 0
    durationUnit: str = "days"
    durationHours: int = 0
    skills: List[str] = []
    skillsCovered: List[SkillCoveredIn] = []
    items: List[PlanItemIn] = []
    description: str = ""
    expectedOutcome: str = ""
    trainer: str = ""
    status: str = "active"        # 'draft' or 'active'
    assessmentIds: List[str] = []

class NoteIn(BaseModel):
    title: str = ""
    body: str = ""

class ProgressIn(BaseModel):
    employeeId: str
    planId: Optional[str] = None
    materialId: Optional[str] = None
    status: str = "inProgress"
    pct: int = 0


class QuestionIn(BaseModel):
    id: Optional[str] = None
    text: str
    options: List[str] = []
    correctIndex: int = 0
    marks: int = 1
    explanation: str = ""
    answerText: str = ""


class AssessmentIn(BaseModel):
    name: str
    bu: Optional[str] = None
    practice: str = ""
    skill: str = ""
    topic: str = ""
    difficulty: str = "medium"
    durationMinutes: int = 20
    passingScorePct: int = 60
    maxAttempts: int = 2
    status: str = "draft"
    questions: List[QuestionIn] = []


class AssignIn(BaseModel):
    employeeIds: List[str]
    dueDate: Optional[str] = None


class SubmitIn(BaseModel):
    scoreMarks: int
    totalMarks: int
    correct: int
    incorrect: int
    timeTakenSeconds: int = 0
    answers: List[dict] = []

class ModuleDoneIn(BaseModel):
    planId: str
    key: str
    title: str = ""
    completed: bool = True

class BankIn(BaseModel):
    name: str
    client: str = ""
    role: str = ""
    technology: str = ""
    category: str = ""
    bu: Optional[str] = None
    confidentiality: str = "Internal"
    version: str = "v1"
    docUrl: str = ""          # uploaded question-bank document
    fileName: str = ""
    fileType: str = ""
    questions: List[QuestionIn] = []


class PrepAssignIn(BaseModel):
    employeeId: str
    bankId: str


class PrepAnswerIn(BaseModel):
    questionId: str
    answerText: str
    status: str = "submitted"


class PrepReviewIn(BaseModel):
    questionId: str
    reviewerComment: str = ""
    score: int = 0
    status: str = "reviewed"


class TrainerIn(BaseModel):
    name: str
    email: str = ""
    internal: bool = True
    expertise: List[str] = []
    capacityHoursPerWeek: int = 0
    rating: float = 0


class PanelIn(BaseModel):
    name: str
    bu: Optional[str] = None
    members: List[dict] = []
    rounds: List[str] = []


class AssignResourceIn(BaseModel):
    employeeId: str


class SkillIn(BaseModel):
    name: str
    category: str = ""
    levels: List[str] = ["Beginner", "Intermediate", "Advanced", "Expert"]


class MockIn(BaseModel):
    employeeId: str
    panelId: Optional[str] = None
    role: str = ""
    scheduledAt: str
    durationMinutes: int = 45
    meetLink: Optional[str] = None


class ScorecardIn(BaseModel):
    rounds: List[dict] = []
    overall: int = 0
    recommendation: str = ""


class InterviewIn(BaseModel):
    candidateId: Optional[str] = None
    employeeId: Optional[str] = None
    panelId: Optional[str] = None
    role: str = ""
    scheduledAt: str
    durationMinutes: int = 45
    meetLink: Optional[str] = None


class AvailabilityIn(BaseModel):
    slots: List[dict] = []


class StatusIn(BaseModel):
    status: str


class StageIn(BaseModel):
    stage: str


class LibraryDocIn(BaseModel):
    domain: str
    title: str
    type: str = "link"          # pdf/doc/ppt/link
    url: str = ""               # link, or set by upload
    description: str = ""

class LibraryQuizIn(BaseModel):
    domain: str
    questions: List[QuestionIn] = []

class LibraryQuizSubmitIn(BaseModel):
    domain: str
    scoreMarks: int
    totalMarks: int

class CtoIn(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    employeeId: Optional[str] = None
    bu: Optional[str] = None
    password: Optional[str] = None

class ResetPasswordIn(BaseModel):
    password: Optional[str] = None