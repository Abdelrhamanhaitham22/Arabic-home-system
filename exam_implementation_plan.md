# Exam and Teacher Grading Implementation Plan

## Goal

Add level-based exams to بيت العربية. The first available exam will be the Level 6 final exam from the supplied six-page PDF. Students will submit their answers, teachers will mark them, and students will see published results using their existing student code.

## Current Baseline

- Students register through the public frontend and receive a permanent code such as `ST202600001`.
- Exams are stored in `backend/apps/exams/models.py` with a name, maximum score, and date.
- Final results are stored in `backend/apps/results/models.py` with a student, exam, and score.
- Students look up results through `GET /api/results/{student_code}/`.
- Administrators currently create exams and enter final scores through Django Admin at `/admin/`.
- The production database is PostgreSQL on Railway. Local development can use SQLite.

## Product Decision for Version 1

Use PDF-based submissions first. Students answer the supplied exam on paper, scan or photograph their answer sheet, and upload it. Teachers correct the uploaded answer sheet and enter section scores in the admin area.

This is faster and safer than converting the complete Arabic exam into an online form. Writing, listening, dictation, and open-answer questions also require teacher review.

## Exam Definition

The supplied exam should be created as:

- Level: Level 6
- Name: Level 6 Final Exam
- Maximum score: 80
- Sections:
  - Reading: 15
  - Vocabulary: 15
  - Grammar: 15
  - Writing: 15
  - Listening: 10
  - Dictation: 10
- Exam PDF: uploaded and attached to the exam record

## Phase 1: Data Model and Admin Foundation

### Objectives

Introduce levels, exam files, section scoring, publishing, and answer submissions without breaking the existing public result lookup.

### Backend changes

1. Add a `Level` model:
   - `name`
   - `order`
   - `is_active`

2. Extend `Student`:
   - Add an optional `level` foreign key.
   - Keep existing students valid during migration.

3. Extend `Exam`:
   - Add `level` foreign key.
   - Add optional uploaded PDF field.
   - Add publication/status fields.

4. Add an `ExamSection` model:
   - `exam`
   - `name`
   - `max_score`
   - `order`

5. Add an `ExamSubmission` model:
   - `student`
   - `exam`
   - uploaded answer file
   - submission status
   - submitted and reviewed timestamps

6. Extend or replace `Result` with section scores:
   - `submission`
   - `student`
   - `exam`
   - total score
   - published flag
   - teacher notes

7. Add a section score model:
   - `result`
   - `exam_section`
   - score
   - teacher comment

8. Add database constraints:
   - A section score cannot exceed its section maximum.
   - A student cannot have two submissions for the same exam unless explicitly allowed later.
   - A result cannot be published before required scores are present.

### Admin changes

- Register levels in Django Admin.
- Add level and PDF fields to exams.
- Add inline exam sections.
- Add submission list and filters by level, exam, and status.
- Add result and section-score editing.
- Add a clear publish action.

### Verification

- Run migrations locally.
- Run existing backend tests.
- Create Level 6 and the six exam sections in local admin.
- Confirm current result lookup still works for existing results.

## Phase 2: Seed the Level 6 Exam

### Objectives

Make the supplied exam available in the real database.

### Work

1. Add the PDF through Django Admin or a controlled data migration/management command.
2. Create Level 6.
3. Create the Level 6 final exam with maximum score 80.
4. Create the six scoring sections and their maximum scores.
5. Confirm the PDF can be downloaded by authorized staff.
6. Do not expose the answer sheet or teacher material publicly unless explicitly requested.

### Verification

- Confirm the file is stored using configured media storage.
- Confirm the exam is visible only to authenticated staff in admin.
- Confirm the section totals equal 80.

## Phase 3: Student Submission Workflow

### Objectives

Allow a registered student to submit a Level 6 answer sheet.

### Backend changes

- Add an authenticated-by-student-code submission endpoint.
- Validate that the student exists.
- Validate that the exam is open for submissions.
- Validate file type and file size.
- Store the uploaded file outside the database using Django media storage.
- Prevent duplicate submissions unless a teacher reopens the submission.
- Return a submission confirmation without exposing private staff data.

### Frontend changes

- Add an exam page showing available exams grouped by level.
- Add Level 6 exam details and PDF download.
- Add student-code verification before submission.
- Add answer-file upload with clear Arabic and Russian messages.
- Add submission status: submitted, under review, returned, or published.

### Verification

- Test valid PDF/image upload.
- Test unsupported file type.
- Test oversized file.
- Test unknown student code.
- Test duplicate submission.
- Test mobile upload behavior.

## Phase 4: Teacher Correction Workflow

### Objectives

Allow teachers to review answer sheets and enter marks safely.

### Authentication and permissions

- Use Django authentication.
- Add a teacher/staff role using groups and permissions.
- Separate teacher permissions from full superuser permissions.
- Require authentication for submissions, files, marking, and publishing.

### Admin workflow

1. Teacher filters submissions by Level 6 and exam.
2. Teacher opens the uploaded answer sheet.
3. Teacher enters marks for each section.
4. The system validates every section maximum.
5. The system calculates the total automatically.
6. Teacher adds optional feedback.
7. Teacher saves as `under review` or publishes the result.
8. Publishing makes the result visible to the student lookup page.

### Verification

- Teachers cannot enter a score above a section maximum.
- Teachers cannot publish incomplete marking.
- Non-staff users cannot access files or marking pages.
- Total score always equals the sum of section scores.
- A published result is visible through the student code lookup.

## Phase 5: Student Result Display

### Objectives

Show students useful results without revealing private information.

### API response

Return:

- Exam name
- Level
- Exam date
- Total score
- Maximum score
- Percentage
- Section scores
- Teacher feedback, if published

Only published results should be returned publicly.

### Frontend changes

- Group results by exam and level.
- Show section-by-section marks.
- Keep the existing student-code lookup compatible.
- Show a clear message when marking is not yet published.

## Phase 6: Production Deployment and Operations

### Work

- Configure Railway PostgreSQL migrations.
- Configure persistent media storage. Railway service disk should not be assumed permanent for important uploads.
- Prefer an object-storage provider for exam PDFs and answer sheets before production use.
- Set upload size limits at Nginx and Django levels.
- Back up the database.
- Restrict media URLs and staff-only files.
- Add audit fields for who reviewed and published each result.
- Add monitoring for failed uploads and grading errors.

## Recommended Order of Work

1. Phase 1: models, migrations, admin, and tests.
2. Phase 2: create and verify the Level 6 exam.
3. Phase 4: teacher grading through Django Admin.
4. Phase 5: display section scores to students.
5. Phase 3: student upload workflow.
6. Phase 6: production storage and hardening.

The teacher workflow can be built before student uploads by creating submissions manually in admin. This lets the scoring and publication rules be tested with the Level 6 exam before exposing uploads to students.

## Open Decisions Before Implementation

1. Should students upload one combined answer-sheet file, or one file per page?
2. Should students be allowed to retake or replace a submission?
3. Should teachers see student names, student codes, or both while correcting?
4. Should the Level 6 exam be visible to all registered students or only students assigned to Level 6?
5. Which persistent file-storage provider should Railway use for PDFs and answer sheets?
