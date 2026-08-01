# Tenant Application System

A portfolio-scale system for centralizing affordable-housing applications:
real logins with roles, PostgreSQL, a paper-first application with OCR
intake, vacancy/waitlist tracking, and an inspection workflow with a
5-day SLA, reminders, escalation, PM scoring, photos, and voice notes.

**This is still meant to run only on your own computer.** It is not on
the internet and nobody outside your computer can reach it.

**Read "Known limitations" near the bottom before you rely on this.**
This was built without the ability to actually run the app in the
environment it was built in (details below) -- it needs a real
end-to-end test on your machine before you trust it with real data.

---

## The four roles

1. **Applicant** -- no login. Downloads a printable PDF application,
   fills it out by hand, and turns it in to the property. Can later look
   up their own status and (optionally) self-book an inspection time at
   `/status`.
2. **Admin** (you) -- sees the entire portfolio. Approves/denies
   applications, manages properties and units, creates Property Manager
   logins, manages the waitlist, and reviews completed inspections.
3. **Property Manager** -- logs in with their own email + password, sees
   **only** their assigned properties, and handles inspections: uploads
   photos, scores the 10 criteria, and submits. (There's no separate
   "inspector" role -- that's folded into Property Manager for now, per
   an earlier decision. Easy to split out later if needed.)
4. **(Held back) Inspector as a separate role** -- not built. See above.

---

## The full workflow, start to finish

1. **Apply.** An applicant goes to `/apply`, downloads the PDF, fills it
   out by hand, signs it, and brings/mails it to a property.
2. **Intake.** Admin or a property manager goes to **Upload a paper
   application**, uploads a photo/scan of the completed form. OCR
   (Tesseract) takes a rough first pass at reading it. A human then
   reviews every field side-by-side with the scanned image and corrects
   anything wrong -- **nothing is saved until a person confirms it.**
3. **Auto-tagging.** On save, the application is automatically tagged
   `Active — unit available` if that property currently has a vacant
   unit, or `Waitlisted` if it doesn't. This happens with no manual step.
4. **Waitlist management.** Admin can see each property's waitlist, in
   first-come-first-served order, from that property's dashboard. Moving
   someone off the waitlist (when a unit opens up) or bumping someone
   ahead of the FCFS order always requires typing a reason -- this gets
   logged permanently for compliance. Nothing happens automatically.
5. **Approve for inspection.** Admin reviews an Active or Waitlisted
   application and clicks **Approve for Inspection**. This emails the
   assigned property manager and starts a 5-calendar-day countdown.
6. **PM does the inspection.** The property manager sees the countdown
   on their dashboard (turning red as it nears zero), gets a daily email
   reminder while it's pending, uploads 10-15 photos of the applicant's
   current home, records or uploads a voice note (optional), scores 10
   criteria from 1-10, and submits.
7. **Overdue escalation.** If 5 days pass with no submission, the
   inspection is marked Overdue and both you (admin) and the PM's
   supervisor (if one is on file) get emailed.
8. **Final decision.** Admin reviews the scores, photos, and voice note,
   then clicks Final Approve or Final Deny. The applicant gets emailed
   (if email is turned on) and can also check `/status` any time.

Every notification the system sends (or tries to send) is logged --
type, recipient, timestamp, success/failure -- so "was X actually
notified" is always answerable later.

---

## What's deliberately not built

- **The disability/accommodation question.** Scoped for this phase, held
  back on purpose pending your legal counsel's review of exact wording
  and handling -- there is **no** disability field anywhere in this
  system. Don't add one without checking first; see the comment at the
  top of `tenant_app/models.py`.
- **SMS/text notifications.** Phase 4 asked about Twilio; this pass is
  **email-only**, per your call. See "Adding SMS later" below for what
  that would take.
- **Real-time chat/dispute tools, RealPage integration, scoring-based
  auto-decisions.** Not asked for, not built.

---

## Two structural choices worth knowing about

**No migration tool yet.** This app creates all its tables fresh on
first startup (`db.create_all()`) rather than using Alembic/Flask-Migrate.
That's fine for getting started, but it means if you change the schema
later and already have real data, you'll need to either add a migration
tool at that point or write the `ALTER TABLE` yourself -- `db.create_all()`
only creates tables that don't exist yet, it won't update existing ones.

**No real task scheduler.** The 5-day inspection SLA check
(reminders/escalation) isn't running on a cron job -- it runs
automatically, at most once an hour, whenever the admin or PM dashboard
loads, plus on-demand via "Run SLA Check Now" on the Inspection Slots
page. That's fine for a pilot with people checking in during the day,
but isn't a substitute for a real scheduled job (a cron container, or
Celery beat) if this needs to catch overdue inspections reliably even
when nobody's logged in for a while.

---

## Running it for the first time

### 1. Install Docker Desktop

1. Go to **docker.com/products/docker-desktop** and download it for
   Windows.
2. Run the installer, accept the defaults, restart when it asks.
3. After restarting, open **Docker Desktop** from your Start menu and
   leave it running in the background (look for the whale icon near the
   clock). It needs to be running any time you use this app.
4. If it prompts you to install "WSL2," let it -- one-time step.

### 2. Get the project files

Download this project as a ZIP from GitHub, extract it (right-click →
Extract All), and open folders until you see `docker-compose.yml`,
`run.py`, and a `tenant_app` folder directly.

### 3. Set up your settings file

1. Find `.env.example` in that folder. Copy it and rename the copy to
   exactly `.env`.
   - If you can't see the ".example" part of the filename, turn on
     "File name extensions" in File Explorer's **View** tab.
2. Open `.env` in Notepad and set:
   ```
   ADMIN_EMAIL=admin@example.com
   ADMIN_BOOTSTRAP_PASSWORD=changeme123
   ```
   to your own values -- this becomes your admin login the first time
   the app starts.
3. **Generate a real encryption key** (used to encrypt SSNs at rest) --
   see "Encryption key" below. Don't skip this before storing a real SSN.

### 4. Open a terminal and start it

1. Open the project folder in File Explorer, click the address bar, type
   `cmd`, press Enter.
2. Run:
   ```
   docker compose up --build
   ```
   The first run downloads and builds everything -- can take a few
   minutes, lots of text will scroll by, that's normal.
3. Open your browser to `http://127.0.0.1:5000`.
4. `Ctrl+C` in the terminal to stop it.

## Running it again later

1. Make sure Docker Desktop is running.
2. Open a terminal in the project folder, run `docker compose up` (no
   `--build` needed unless you downloaded a code update).
3. `Ctrl+C` when done.

Your data persists in a Docker volume between runs.

### Getting a code update later

Stop the app, download the new ZIP, extract it, **copy your existing
`.env` file into the new folder** first (so you don't lose your
passwords/keys), then `docker compose up --build`.

---

## Encryption key

SSNs are encrypted before they're stored. Generate a real key before you
store any real one:

1. With Docker Desktop running and the project folder open in a
   terminal, run:
   ```
   docker compose run --rm web python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
2. Copy the output into `.env`:
   ```
   FIELD_ENCRYPTION_KEY=the-key-you-just-generated
   ```
3. **Back this up somewhere safe, separate from your database backups.**
   If this key is ever lost, every encrypted SSN becomes permanently
   unreadable -- there's no way to recover it without the key.
4. Restart the app (`Ctrl+C`, then `docker compose up`).

SSNs are never displayed in full anywhere in the app -- only the last 4
digits, everywhere, always.

---

## Logging in

- **Admin:** `http://127.0.0.1:5000/login`, using your `ADMIN_EMAIL` /
  `ADMIN_BOOTSTRAP_PASSWORD` from `.env`.
- **Property Managers:** same login page. Sample logins are created the
  first time the app starts with an empty database:
  - `pat.rivera@example.com` / `changeme456` (Maple Court Apartments,
    Riverside Commons)
  - `sam.chen@example.com` / `changeme456` (Oakwood Terrace, Sunset
    Gardens)

  For real staff, log in as admin and use **Property Managers** to
  create their accounts -- don't reuse the sample logins.

---

## Testing the paper-application intake

1. Log in as admin (or a PM).
2. Click **Upload a paper application**.
3. For a first try, you don't need a real scanned form -- any photo or
   screenshot works, since Tesseract's guess is only a starting point
   you'll correct anyway. Or print the PDF from `/apply`, fill in a
   couple of fields by hand, and photograph it with your phone.
4. On the review screen, check/correct every field -- especially the
   property (OCR's guess is pre-selected, but verify it), and check the
   "signed and dated" box before saving.
5. Save it, and it'll show up on the dashboard with status `Active — unit
   available` or `Waitlisted` depending on whether that property has a
   vacant unit (see "Testing vacancy/waitlist" below).

**On OCR accuracy:** Tesseract is free and runs locally, but it's built
for printed text, not handwriting -- expect it to get most handwritten
fields wrong or blank. That's why every field is editable and nothing
saves without a human confirming it. If accuracy matters more than cost
for real use, AWS Textract or Google Document AI do meaningfully better
on handwriting (roughly $0.05-$0.065/page at typical volumes) -- swapping
them in would mean replacing the `extract_text()` function in
`tenant_app/ocr.py` with an API call and adding your cloud credentials to
`.env`; the rest of the review/save flow wouldn't need to change.

**On where scanned images are stored:** locally, inside the Docker
volume (`instance/uploads/`), the same as inspection photos. That's
simple and keeps this self-contained, which is right for a pilot. At
real portfolio scale (thousands of scans + inspection photos), a cloud
object store (S3 or similar) would be the better long-term choice --
more reliable, better backups, and it stops a single server's disk from
being the thing that runs out of space. Worth revisiting before this
goes into full production; the code change would be contained to how
photos are saved/served (`routes_intake.py`, `routes_pm.py`,
`uploaded_file` in `tenant_app/__init__.py`), not the database schema.

---

## Testing vacancy/waitlist

1. Log in as admin, go to **Properties**, click a property to open its
   dashboard.
2. Under **Units**, click **Mark Occupied** on the one vacant unit (each
   sample property starts with 1 vacant, 3 occupied).
3. Now every *new* application to that property gets tagged
   `Waitlisted` instead of `Active — unit available` (try uploading
   another paper application to see it).
4. With someone on the waitlist, click **Mark Vacant** on a unit again
   -- the waitlist panel now shows a **Move to Active** button. It
   requires a reason (even for the person already at the top of the
   list) -- that's intentional, so there's always a compliance record
   of who moved someone and why. Nothing happens silently.
5. **Prioritize** lets you bump someone ahead of FCFS order (e.g. for a
   reasonable accommodation) -- also always requires a reason, logged
   the same way.

---

## Testing the inspection SLA (without waiting 5 real days)

1. Log in as admin, open the sample application **Dana Kim** (already
   seeded in `Approved for inspection` status).
2. Go to **Testing Tools** (in the nav bar).
3. Select Dana Kim, set "days old" to `5`, click **Set Clock**.
4. Go to **Inspection Slots** → **Run SLA Check Now**.
5. Refresh Dana Kim's application page -- inspection status should now
   show **Overdue**, and (if email is turned on) both the admin email
   and Pat Rivera's supervisor email (seeded as `supervisor@example.com`)
   will have gotten an escalation notice -- check the flash message and,
   if email is on, your inbox.
6. Try `days old = 2` instead to see the daily-reminder path (PM gets a
   reminder, nothing escalates yet) rather than the overdue path.

---

## Testing a full inspection submission (Phase 5)

1. Log in as `pat.rivera@example.com` / `changeme456`.
2. Open Dana Kim's application from the dashboard.
3. Upload 10 photos (any images work for testing -- the count is what's
   enforced, not content). Watch the counter update.
4. Once 10+ are uploaded, click **Continue to Inspection Scoring**.
5. Try clicking **Allow** on the microphone permission prompt and
   recording a short voice note, or skip it and use the file-upload
   fallback instead -- both are optional.
6. Score all 10 criteria, add a note, submit.
7. Log back in as admin and open Dana Kim's application -- you should
   see all 10 scores as bars, the photo gallery, your notes, and an
   audio player if you attached a voice note. **Final Approve**/**Final
   Deny** buttons are now available.

**Voice note browser support:** works well in current Chrome, Firefox,
and Edge on desktop and Android, and Safari 14.1+ on desktop. Mobile
Safari (iOS) support varies by version and can be flaky with
microphone permissions in some setups -- if recording doesn't work, the
file-upload field next to it is the deliberate fallback (record with any
voice memo app, then upload the file).

---

## Adding SMS later

Not built in this pass (email-only, per your call). When you're ready:
Twilio is the standard choice -- sign up, buy a phone number (~$1/month),
and SMS costs roughly $0.0079/message in the US. You'd add
`TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_FROM_NUMBER` to
`.env`, and add an SMS-sending function alongside the existing ones in
`tenant_app/mail.py` (the notification call sites in `sla.py` and
`routes_admin.py` already have PM/admin objects in scope, so wiring in a
second channel wouldn't need those call sites restructured, just a
phone-number field added to the User model).

---

## Setting up tenant emails (optional)

Off by default. To turn on:

```
EMAIL_ENABLED=true
EMAIL_ADDRESS=your-real-gmail-address@gmail.com
EMAIL_APP_PASSWORD=the16characterapppassword
```

Create the Gmail App Password at **myaccount.google.com/apppasswords**
(requires 2-Step Verification turned on first). Restart the app after
editing `.env`.

---

## A note on protected-class questions

The application form asks for **marital status** and **number of
children/dependents** -- Fair Housing-protected categories. The code
never uses them in any decision -- they're shown for context only.
There's deliberately no disability question at all (see above). Worth a
compliance review before real applicants use this, especially around
the income/employment fields new in this phase and the waitlist
override process -- the override reason is always logged, but the
*content* of an admin's stated reason isn't validated for compliance by
the software; that's a human judgment call each time.

---

## Known limitations (please read before trusting this with real data)

This was built in a sandboxed environment with **no internet access**
and **no working Docker daemon** -- meaning:

- **Nothing here has been run end-to-end.** Every route was written
  carefully and reviewed by hand, and the full database schema (all 13
  tables, every constraint) was validated against a real local
  PostgreSQL instance -- including waitlist ordering, the atomic
  slot-booking/override logic, PM-scoped data isolation, and the SLA
  overdue query -- but the Flask/SQLAlchemy/OCR/PDF code itself has
  never actually been executed. **Please do a full click-through test
  (the sections above) before relying on this.**
- **Docker build is unverified.** The `Dockerfile` and
  `docker-compose.yml` are written to standard, well-established
  patterns, but `docker build` was never run here (no working daemon in
  this environment) -- the first `docker compose up --build` on your
  machine is also the first real build.
- **OCR/PDF libraries are untested.** `pytesseract`, `Pillow`, and
  `reportlab` couldn't be installed in this sandbox either (same
  no-internet issue) -- the PDF layout math was manually checked against
  page dimensions to make sure nothing runs off the page, but the actual
  rendered PDF and OCR output haven't been visually inspected.

None of this means it's likely broken -- the patterns used throughout
are standard and the logic was checked as carefully as possible without
being able to run it -- but "carefully reviewed" isn't the same
assurance as "tested," and this system will hold real Social Security
numbers and income data. Test thoroughly before using it for real
applicants.

---

## Project files, in plain English

| File / folder | What it does |
|---|---|
| `docker-compose.yml` | Defines the two containers (database + web app) that run together. |
| `Dockerfile` | Builds the web app's container, including installing Tesseract. |
| `.env` (you create this) | Your real passwords, keys, and settings. Never uploaded to GitHub. |
| `run.py` | Starts the app -- what the web container runs. |
| `tenant_app/__init__.py` | Assembles the app: database, login system, all pages, protected file-serving. |
| `tenant_app/models.py` | The full database structure -- read the module docstring for the application lifecycle. |
| `tenant_app/crypto.py` | SSN encryption/decryption and masking. |
| `tenant_app/auth.py` | Login/logout and role-based access rules. |
| `tenant_app/routes_admin.py` | Admin pages: dashboard, properties, units, waitlist, PM accounts, inspection slots, SLA tools, decisions. |
| `tenant_app/routes_pm.py` | Property-manager portal: dashboard, photo upload, inspection scoring form. |
| `tenant_app/routes_intake.py` | The paper-application upload/OCR/review/save flow. |
| `tenant_app/routes_public.py` | The public "how to apply" page, PDF download, and status check -- no login. |
| `tenant_app/ocr.py` | Reads text off a scanned form with Tesseract. |
| `tenant_app/pdf_form.py` | Generates the printable paper application. |
| `tenant_app/sla.py` | The 5-day inspection countdown/reminder/escalation logic. |
| `tenant_app/mail.py` | All outbound email, and the notification audit log. |
| `tenant_app/seed.py` | Creates tables and sample data the first time the app runs. |
| `tenant_app/config.py` | Reads your `.env` settings. |
| `tenant_app/templates/` | Page layouts (HTML). |
| `tenant_app/static/style.css` | Styling. |
