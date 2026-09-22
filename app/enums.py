# Login roles. The interview-panel portal is intentionally removed.
ROLES = ["admin", "buHead", "ta", "benchEngineer", "cto"]

PERMISSIONS = [
    "view", "add", "edit", "deactivate", "assign", "approve", "export",
    "administer", "manageBu", "manageTa", "schedule",
]

MATERIAL_TYPES = ["pdf", "video", "link", "doc", "other"]
BENCH_STATUS = ["newEntry", "assessmentDue", "trainingPlanned", "trainingInProgress",
                "assessment", "deployable", "proposed", "deployed", "released", "transferred"]
PROGRESS_STATUS = ["notStarted", "inProgress", "completed", "overdue"]
PREP_ANSWER_STATUS = ["notStarted", "draft", "submitted", "reviewed"]
MOCK_STATUS = ["scheduled", "completed", "cancelled"]
PIPELINE_STAGE = ["screen", "toSchedule", "scheduled", "feedbackDue",
                  "decision", "selected", "rejected"]
DIFFICULTY = ["easy", "medium", "hard"]
ASSESSMENT_STATUS = ["draft", "published", "archived"]
ATTEMPT_STATUS = ["assigned", "inProgress", "completed", "overdue"]
DEPLOYMENT_KIND = ["propose", "deploy", "transfer", "release"]
