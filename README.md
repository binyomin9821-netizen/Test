# Tenant Application System

The foundation for a real, portfolio-scale version of the tenant
application pilot: real logins with roles, a production-grade database
(PostgreSQL instead of the single-file version), and a data model ready
for the features coming in later phases (paper-application OCR, vacancy
and waitlist logic, inspection scheduling with deadlines, and PM
scoring/photos/voice notes). None of those later features are built yet
-- this stage is purely the new foundation, with the application form and
decision-maker dashboard you already had moved onto it.

**This is still meant to run only on your own computer.** It is not on
the internet and nobody outside your computer can reach it.

## What's in this stage

- **Public application form** (`/apply`) -- unchanged from before: pick a
  property, fill in basic + household info, submit, get a reference
  number.
- **Applicant status check** (`/status`) -- unchanged: look up your
  status and book an inspection time slot with your reference number and
  email.
- **Admin** -- logs in with an email + password (not a shared password
  anymore). Sees every property, every application, and can:
  - Approve/Deny applications.
  - Add properties (`/admin/properties`), each with a manager email and
    phone number, and see outstanding (Pending) applications per
    property.
  - Create Property Manager logins and assign them properties
    (`/admin/property-managers`).
  - Add inspection time slots (`/admin/inspections`).
- **Property Manager** -- logs in with their own email + password, and
  sees **only** the properties assigned to them: those properties'
  scheduled inspections, and can upload inspection photos / mark an
  inspection complete. (There's no separate "inspector" login anymore --
  that role is folded into Property Manager for now, per your call. It's
  easy to split back out later if you want a dedicated inspector role.)

## What's deliberately not built yet

Everything below is scoped for later phases, on purpose -- the data
model is ready for them, but none of the workflow exists yet:

- The real, comprehensive affordable-housing application (SSN,
  household members, income breakdown, etc.) and paper-form OCR.
- Vacancy tracking and waitlist logic (the `Waitlisted` status exists as
  a possible value, but nothing sets it automatically, and units don't
  have an admin screen to mark vacant/occupied yet).
- Per-property dashboards and a property picker for 200+ properties.
- The 5-day inspection SLA, countdown, reminders, and escalation to a
  supervisor.
- The 10-criteria PM scoring form, 10-15 required photos, and voice
  notes.

## A structural choice worth knowing about

The old version used SQLite (one file) and hand-written SQL. This
version uses PostgreSQL and an ORM (SQLAlchemy), which is the standard
way to build something meant to grow -- but it means schema changes
(adding new columns/tables in later phases) need a migration strategy.
For this stage, the app just creates all tables fresh on first startup
(`db.create_all()`), which is simple and reliable. Before Phase 2 adds
new fields (SSN, income, household members, etc.), it's worth adding a
proper migration tool (Flask-Migrate/Alembic) so schema changes can be
applied without wiping data -- flagging that now so it isn't a surprise
later.

---

## Running it for the first time

This version runs in **Docker** instead of installing Python directly.
It's a bit more to install once, but after that, everything -- the
database included -- starts with one command, and you won't hit the
"pip is not recognized" type of issues from before.

### 1. Install Docker Desktop

1. Go to **docker.com/products/docker-desktop** and download it for
   Windows.
2. Run the installer. Accept the defaults.
3. It'll ask you to restart your computer -- do that.
4. After restarting, open the **Docker Desktop** app from your Start
   menu and leave it running in the background (look for the whale icon
   in your system tray, near the clock). Docker Desktop needs to be
   running any time you use the app.

   Note: on some Windows setups, Docker Desktop will prompt you to
   install "WSL2" (Windows Subsystem for Linux) the first time -- just
   follow its prompts and let it install; it's a one-time step.

### 2. Get the project files onto your computer

Same as before: download this project's files as a ZIP from GitHub and
extract them (right-click the ZIP → Extract All). Keep opening folders
until you see `docker-compose.yml`, `run.py`, and a `tenant_app` folder
directly -- that's the one you want to be in.

### 3. Set up your settings file

1. In that folder, find `.env.example`.
2. Make a copy of it in the same folder, and rename the copy to exactly
   `.env` (just `.env`, nothing before the dot).
   - **On Windows**, if you don't see the ".example" part of the
     filename, File Explorer is hiding file extensions. Go to the
     **View** tab in File Explorer and check "File name extensions" to
     turn them on.
3. Open `.env` in Notepad and change at least these two lines to your
   own values:
   ```
   ADMIN_EMAIL=admin@example.com
   ADMIN_BOOTSTRAP_PASSWORD=changeme123
   ```
   This becomes your admin login the first time the app starts. You can
   leave everything else in `.env` as-is for now.

### 4. Open a terminal in that folder

Same trick as before: open the folder in File Explorer, click in the
address bar, type `cmd`, press Enter.

### 5. Start everything with one command

```
docker compose up --build
```

The first time, this downloads and builds everything, which can take a
few minutes -- you'll see a lot of text scroll by, that's normal. When
it settles down and you see log lines mentioning the app running, it's
ready.

Open your browser to:

```
http://127.0.0.1:5000
```

To **stop** it, go back to that terminal window and press `Ctrl+C`.

---

## Running it again later

1. Make sure **Docker Desktop is running** (open it from the Start
   menu if it isn't).
2. Open a terminal in the project folder (step 4 above).
3. Type:
   ```
   docker compose up
   ```
   (no `--build` needed unless you've downloaded a code update).
4. Open `http://127.0.0.1:5000` in your browser.
5. `Ctrl+C` in the terminal when you're done.

Your data persists between runs automatically -- it's stored in a Docker
volume, not inside the containers themselves, so stopping and starting
doesn't lose anything.

### Getting a code update later

Same as before: stop the app, download the new ZIP, extract it, but this
time **copy your existing `.env` file** into the new folder before
starting (so you don't lose your passwords), then run
`docker compose up --build` (the `--build` matters this time, so it
picks up the code changes).

---

## Logging in

- **Admin:** `http://127.0.0.1:5000/login`, using the `ADMIN_EMAIL` /
  `ADMIN_BOOTSTRAP_PASSWORD` you set in `.env`.
- **Property Managers:** same login page. The first time the app starts
  with an empty database, it creates two sample PM logins so you can see
  the role-based access working right away:
  - `pat.rivera@example.com` / `changeme456` (assigned to Maple Court
    Apartments and Riverside Commons)
  - `sam.chen@example.com` / `changeme456` (assigned to Oakwood Terrace
    and Sunset Gardens)

  For real property managers, log in as admin and use the **Property
  Managers** page to create their accounts and assign properties --
  don't reuse the sample logins for real staff.

---

## Setting up tenant emails (optional)

Same feature as before, just configured in `.env` now instead of
`config.py`:

```
EMAIL_ENABLED=true
EMAIL_ADDRESS=your-real-gmail-address@gmail.com
EMAIL_APP_PASSWORD=the16characterapppassword
```

See the earlier instructions for creating a Gmail "App Password" (turn
on 2-Step Verification, then create one at
**myaccount.google.com/apppasswords**). After editing `.env`, stop the
app and run `docker compose up` again for the change to take effect.

---

## A note on the two protected-class questions

Unchanged from before: the form asks for **marital status** and
**number of children**. These are Fair Housing–protected categories, and
the code never uses them in the Approve/Deny decision -- they're shown
to the decision-maker for context only. Worth a compliance check-in
before real applicants use this.

---

## Project files, in plain English

| File / folder | What it does |
|---|---|
| `docker-compose.yml` | Defines the two pieces that run together: the database and the web app. This is what `docker compose up` reads. |
| `Dockerfile` | Instructions for building the web app's container. |
| `.env` (you create this) | Your real passwords and settings. Never uploaded to GitHub. |
| `.env.example` | The template `.env` is copied from. |
| `run.py` | Starts the app -- what the web container actually runs. |
| `tenant_app/__init__.py` | Assembles the app: database, login system, and all the pages. |
| `tenant_app/models.py` | The database structure: Users, Properties, Units, Applications, Inspection Slots/Photos, and who's assigned to what. |
| `tenant_app/auth.py` | Login/logout, and the rules for who can see admin pages vs. property-manager pages. |
| `tenant_app/routes_admin.py` | Admin-only pages. |
| `tenant_app/routes_pm.py` | Property-manager portal pages. |
| `tenant_app/routes_public.py` | The public application form and status page -- no login. |
| `tenant_app/seed.py` | Creates the database tables and sample data the first time the app runs. |
| `tenant_app/mail.py` | Sends the applicant-decision email, if turned on. |
| `tenant_app/config.py` | Reads your `.env` settings -- you shouldn't need to edit this file directly. |
| `tenant_app/templates/` | The actual page layouts (HTML). |
| `tenant_app/static/style.css` | Makes the pages look presentable. |
