# Online Exam Implementation Plan

## Phase 1: Confirmed Exam Rules

This phase is complete when the rules below are accepted as the contract for the online exam implementation.

### Question source

- Each level owns one active question bank containing 100 questions.
- Questions are categorized as `true_false` or `multiple_choice`.
- Every question has its answer choices and one configured correct answer.
- An exam uses the question bank belonging to its assigned level.
- Questions are not copied into each exam definition.

### Per-student generation

- Each student receives a separate random question set from the level's question bank.
- Each generated set contains exactly 50 questions:
  - 25 true/false questions.
  - 25 multiple-choice questions.
- Question overlap between students is allowed.
- The selected questions are saved to the student's attempt and do not change on refresh.

### Attempts

- A student can have only one attempt for a specific exam.
- The database must enforce uniqueness for the student and exam pair.
- An attempt is either `in_progress` or `submitted`.
- A submitted attempt is permanently locked and cannot be answered or submitted again.
- Existing attempts are resumed rather than generating a new question set.

### Submission and grading

- Correct answers are never sent to the frontend before submission.
- Answers are graded on the server using the answer key saved with the attempt.
- Submission calculates the score and percentage immediately.
- Unanswered questions receive zero points and are treated as wrong.
- The submission response includes the complete review:
  - Total score and percentage.
  - Every question in the student's generated set.
  - The student's answer.
  - Whether the answer was correct or wrong.
  - The correct answer for wrong or unanswered questions.

### Exam eligibility

- An exam cannot be opened unless its level has the required question bank.
- The active bank must contain 100 questions, including at least 25 true/false and 25 multiple-choice questions.
- Objective questions must have valid answer choices and exactly one correct answer.

### Scope boundary

Phase 1 defines rules only. Database models, migrations, APIs, frontend screens, and tests are implemented in later phases.

## Goal

Replace the legacy PDF workflow with browser-based online exams. Teachers create exams and questions, students answer using their student code, objective questions are graded automatically, written answers are graded by teachers, and only approved results are published.

## Phase 1: Remove Legacy PDF Workflow

- Back up the production database and media before deletion.
- Delete existing PDF exam records, results, and answer-sheet records through migrations.
- Delete stored exam PDFs and student answer files.
- Remove PDF download and answer-upload endpoints.
- Remove old PDF frontend screens and teacher file-grading UI.
- Keep only the level, exam scheduling, section, result, and teacher foundations needed by the online system.

## Phase 2: Homepage Videos

- Add two video records managed through Django Admin.
- Support upload, replacement, activation, and hiding.
- Store Arabic and Russian titles and descriptions.
- Validate supported video type and maximum size.
- Display active videos on the homepage.
- Use persistent object storage in production.

## Phase 3: Online Exam Structure

- Add online exam models and question models.
- Support multiple choice, true/false, short answer, and written answer questions.
- Store question point values and answer choices.
- Configure correct answers for objective questions.
- Assign exams to student levels.
- Add opening date, closing date, and time limit.
- Support draft, open, closed, and published statuses.

## Phase 4: Level-Based Exam Structure

- Keep exam configuration limited to level, schedule, time limit, status, and score settings.
- Use the assigned level's active question bank as the only source of exam questions.
- Keep one `Questions` section as the exam's admin container for all question-bank questions.
- Divide questions inside that section by question type: True/False and Multiple Choice.
- Keep sections out of the student exam API; students receive the generated question set later.
- Keep legacy section-score records compatible until attempt-based grading replaces them.
- Set the standard generated exam maximum to 50 points, one point per selected question.
- Prevent an exam from opening unless its level question bank passes validation.

## Phase 4: Teacher Exam Management

- Allow authorized teachers to create and edit assigned-level exams.
- Add and edit questions and answer choices.
- Configure correct answers and points.
- Preview exams before publishing.
- Prevent publishing incomplete or invalid exam definitions.

## Phase 5: Student Exam Experience

- Student enters their permanent student code.
- Student sees exams available for their assigned level.
- Student starts one attempt per exam.
- Show a server-validated countdown timer.
- Save answers during the attempt.
- Allow one final submission only.
- Prevent access after the closing time or time limit.

## Phase 6: Anti-Cheating Controls

- Enforce one attempt per student and exam at the database level.
- Randomize question and answer-choice order per attempt.
- Validate deadlines and time limits on the server.
- Record start and final submission times.
- Record browser and IP metadata with appropriate privacy controls.
- Record tab switching, copy/paste, fullscreen exit, and inactivity events.
- Show suspicious-activity warnings to authorized teachers.

## Phase 7: Automatic and Manual Grading

- Automatically grade multiple choice and true/false answers.
- Apply configured grading rules for short answers where appropriate.
- Send written answers to the assigned teacher.
- Allow question-level comments and overall feedback.
- Save incomplete grading as a draft.
- Prevent publishing incomplete results.

## Phase 8: Published Results

- Students check results using their student code.
- Show score, percentage, question or section scores, and published feedback.
- Publish results only after teacher approval.
- Never expose correct answers, private teacher notes, or anti-cheating records publicly.

## Phase 9: Testing and Deployment

- Test legacy deletion and backup procedures.
- Test video management and persistent storage.
- Test exam creation, validation, preview, and publishing.
- Test one-attempt enforcement, answer saving, timer, and deadline rules.
- Test automatic and manual grading.
- Test Arabic and Russian mobile layouts.
- Configure production backups, object storage, upload limits, and monitoring.

## Confirmed Student Flow

1. Teacher creates an online exam with questions and answers.
2. Student enters their student code.
3. Student opens the exam and answers directly in the browser.
4. Student submits the exam once.
5. Teacher opens the submitted answers.
6. Objective questions are graded automatically.
7. Written answers are graded manually.
8. Teacher publishes the result.
9. Student checks the published result using their student code.
