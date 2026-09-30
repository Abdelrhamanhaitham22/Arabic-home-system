# Online Exam Implementation Plan

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
