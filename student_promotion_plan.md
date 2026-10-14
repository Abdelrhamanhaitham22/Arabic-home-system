# Automatic Student Promotion — Phased Implementation Plan

## Agreed rule

- Promote a student when the combined **online written exam (التحريري)**, activity/dictation, and oral score is at least **50%** of the configured combined maximum. Count the online exam score once as the written component; do not add a separate written score on top of it.
- The teacher must submit both activity/dictation and oral scores before promotion is evaluated. A submitted zero is a valid score.
- Promotion moves the student from the level assessed to the next active level in `Level.order`.

## Phase 1 — Record assessment completion

**Status: Complete**

- Added `TeacherAssessment.is_complete` and `completed_at`. Existing records migrate as incomplete.
- The teacher assessment endpoint requires both activity/dictation and oral scores and marks a record complete only after both pass the existing score range validation.
- Exam submission can create or update an assessment's written score without marking the teacher assessment complete.

**Done when:** a genuine submitted zero is distinguishable from a missing teacher score, and existing records cannot promote students unexpectedly.

## Phase 2 — Centralize the promotion decision

**Status: Complete**

- Added `promote_student_from_attempt()` to evaluate a submitted attempt and its completed assessment for the student's current level.
- The service uses the attempt score as التحريري, combines it with activity/dictation and oral scores, and compares the exact decimal percentage with 50%.
- Promotion is ineligible when the attempt maximum differs from the configured written maximum, scores are invalid, or there is no next active level.
- The service locks the student, advances to the next active level by `order`, and records the source attempt/result and score snapshot in `StudentPromotion`.
- A unique source attempt plus a transaction makes repeat calls idempotent and prevents a second promotion from the same attempt.

**Done when:** the service returns a clear promoted/not-eligible reason and repeated calls cannot produce another promotion.

## Phase 3 — Connect the existing score flows

**Status: Complete**

- Exam submission saves the written score and result against the exam's level, then evaluates that attempt for promotion.
- Teacher score submission updates results for the assessment's level, then evaluates the latest submitted attempt for that level.
- Either submission can happen first. The promotion service leaves the student in place until both the online attempt and completed teacher assessment exist.
- Older attempts and assessments continue to use their exam level if `Student.level` has changed.

**Done when:** promotion happens once as soon as both required parts are present, regardless of which is submitted first.

## Phase 4 — Show status and support corrections

**Status: Complete**

- The student results lookup returns and displays the current level.
- The teacher portal shows assessment state: incomplete, awaiting the online exam, below 50%, promoted, at the highest active level, pending promotion, or review required. Teachers can view students they assessed at an assigned level after those students advance; past scores are read-only unless the student's current level is assigned to that teacher.
- Promotion history is available as a read-only Django admin record.
- For a score correction after promotion, authorized staff edit the existing teacher assessment in Django admin; published results for that level are refreshed from the corrected scores. A difference from the promotion snapshot is marked for review. Staff then adjust the student's current level in Student admin if needed. The original promotion record remains as an audit entry, and the system does not reverse promotions automatically.

**Done when:** students and staff can see the outcome and staff can trace the score that caused it.

## Phase 5 — Verify and release

**Status: Verification implemented; release pending**

- Test exactly 50%, below 50%, a submitted zero, missing teacher submission, missing exam attempt, no next active level, repeated requests, and concurrent requests.
- Test both event orders and confirm an earlier level's edited score cannot promote a student again.
- Apply migrations, deploy the backend, and monitor promotion records and errors before relying on the automation.

Verification run on the local SQLite test database: all 22 student tests passed; the concurrent row-lock test was skipped because SQLite does not support `select_for_update`. Django system checks and `makemigrations --check --dry-run` passed. The full backend suite ran 66 tests and exposed five failures in existing exam import, exam form/duplication, and exam response tests; none were in student promotion. Deployment and production monitoring remain pending because this workspace has no configured deployment target.

**Done when:** these cases pass and the promotion history matches the changed student levels.

## Current code involved

- `backend/apps/students/models.py`: current student level.
- `backend/apps/exams/models.py`: ordered, active levels.
- `backend/apps/teachers/models.py` and `backend/apps/teachers/views.py`: teacher scores and submission.
- `backend/apps/attempts/views.py`: exam submission and written score.
- `backend/apps/results/models.py`: stored result and percentage.
