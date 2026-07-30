# Tenant Application System

A three-part system:

1. **Public two-part application form** (`/apply/part1`, `/apply/part2`) — collects
   basic info and household info, saves to the `applications` table.
2. **Inspector Portal** (`/inspector/dashboard`) — mobile-friendly page listing
   pending applications, with a button to upload housing-condition photos to a
   private S3 bucket, linked to the application by `application_id`.
3. **OCR intake script** (`scripts/ocr_fill.py`) — reads a scanned paper
   application (Tesseract or Google Cloud Vision) and fills blank
   Name/Email/Marital Status fields on an existing application row.

A separate **decision-maker view** (`/admin/applications`) shows each
application alongside its inspection photos (via short-lived presigned URLs)
and lets a reviewer set the application's status.

## ⚠️ Fair housing compliance note

This form collects **marital status** and **number of children**, which are
protected classes (marital status / familial status) under the U.S. Fair
Housing Act. As built:

- Both fields are optional and the form states they are used only to confirm
  occupancy requirements, not to evaluate the application.
- Nothing in the approve/deny code path reads `marital_status` or
  `number_of_children` — the decision-maker view shows them for context only.
- **Before deploying this for real applicants**, have your fair housing /
  legal counsel review whether you need to collect these fields at all, how
  they're presented to reviewers, and your staff's decision process. Software
  can keep the fields out of the workflow; it can't stop a person from
  factoring them in.

The OCR script similarly never auto-approves anything — it only stages
Name/Email/Marital Status onto a record and flags it `ocr_needs_review` for a
human to verify, since handwriting OCR has a meaningful error rate.

## Setup

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Local dev uses SQLite by default. For a real SQL database:
export DATABASE_URL="postgresql://user:pass@host:5432/tenant_db"

export SECRET_KEY="change-me"
python run.py
```

Create staff logins:

```bash
python scripts/create_user.py --username inspector1 --password '...' --role inspector
python scripts/create_user.py --username reviewer1  --password '...' --role decision_maker
```

## S3 configuration (Inspector Portal photo uploads)

```bash
export S3_BUCKET_NAME="your-inspection-photos-bucket"
export AWS_REGION="us-east-1"
# Credentials via the standard AWS credential chain (env vars, instance role, etc.)
```

The bucket should **block all public access**; the app generates short-lived
presigned URLs (1 hour) for the decision-maker view instead of public links,
since these are photos of an applicant's home.

## OCR intake

```bash
# Local/offline, printed text works best, handwriting is hit-or-miss:
python scripts/ocr_fill.py --application-id 42 --image scan.jpg --engine tesseract

# Better handwriting accuracy (requires GOOGLE_APPLICATION_CREDENTIALS):
python scripts/ocr_fill.py --application-id 42 --image scan.jpg --engine gcv
```

Requires Tesseract's binary installed separately for the `tesseract` engine
(e.g. `apt install tesseract-ocr`) or a Google Cloud Vision service account
for the `gcv` engine.
