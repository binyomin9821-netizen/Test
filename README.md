# Tenant Application Pilot

A small private tool for the affordable-housing team. It has two parts:

1. **A public application form** — an applicant picks a property, then
   fills in their basic info (name, phone, email, current address) and
   household info (marital status, number of children), and submits.
2. **A password-protected decision-maker page** — one shared password
   gets you into a dashboard listing every application from every
   property, newest first, with its status (Pending / Approved / Denied).
   Clicking an application shows full details with Approve/Deny buttons.

Everything is stored in one file, `instance/app.db`. There is no separate
database program to install.

**This is meant to run only on your own computer.** It is not on the
internet and nobody outside your computer can reach it. That's
intentional — do not deploy this to a public web host as-is.

---

## Running it for the first time

You'll do this once to get set up. It looks like a lot of steps, but each
one is small.

### 1. Install Python

Python is the programming language this tool is written in.

- Go to **python.org/downloads** and download the installer for your
  operating system (Windows or Mac).
- Run the installer.
  - **On Windows:** on the first screen, check the box that says
    **"Add python.exe to PATH"** before clicking Install. This step is
    easy to miss and important.
  - **On Mac:** just click through the installer normally.

### 2. Get the project files onto your computer

Download this project's files as a folder on your computer (for example,
by downloading the ZIP from GitHub and unzipping it to somewhere easy to
find, like your Desktop, in a folder named `tenant-app`).

### 3. Open a terminal in that folder

The terminal is a window where you type commands instead of clicking.

- **On Windows:** open the `tenant-app` folder in File Explorer, click in
  the address bar at the top, type `cmd`, and press Enter. A black window
  opens, already pointed at the right folder.
- **On Mac:** open the `tenant-app` folder in Finder, then go to
  **Finder > Services > New Terminal at Folder** (or open the Terminal
  app and type `cd ` followed by dragging the folder into the window,
  then press Enter).

### 4. Install the one thing this project needs (Flask)

In that terminal window, type this and press Enter:

```
pip install -r requirements.txt
```

(On some Macs you may need to type `pip3` instead of `pip`.)

You'll see some text scroll by — that's normal. When it stops and gives
you a new line to type on, it's done.

### 5. Start the app

Still in that same terminal window, type:

```
python run.py
```

(Again, on some Macs use `python3` instead of `python`.)

Your web browser should open automatically to the application form. If
it doesn't, open your browser yourself and go to:

```
http://127.0.0.1:5000/apply
```

The first time you run this, it also automatically creates the database
and fills it with 5 sample properties and 3 sample applications, so you
immediately have something to look at.

To **stop** the app, click back into the terminal window and press
`Ctrl+C`.

---

## Running it again later

Every time after the first, it's just steps 3 and 5 above:

1. Open a terminal in the `tenant-app` folder (see step 3 above).
2. Type `python run.py` and press Enter.
3. Your browser opens to the form automatically.
4. When you're done, press `Ctrl+C` in the terminal to stop it.

Your data (all submitted applications) is saved in `instance/app.db` and
will still be there next time you start it up.

---

## Using it

- **Applicants:** go to `http://127.0.0.1:5000/apply`, or just the main
  page — it goes there automatically.
- **Decision-maker:** go to `http://127.0.0.1:5000/admin/login`. The
  starting password is:

  ```
  changeme123
  ```

  **Change this before giving this to anyone else.** Open the file
  `config.py` in a plain text editor (Notepad on Windows, TextEdit on
  Mac — set TextEdit to plain text mode), find the line that says:

  ```
  ADMIN_PASSWORD = "changeme123"
  ```

  and replace `changeme123` with your own password, then save the file.
  You'll need to stop and restart the app (`Ctrl+C`, then `python
  run.py` again) for the change to take effect.

---

## What's already built vs. what's next

**Built now:**
- Property selection + two-part application form, saved to the database.
- Confirmation message on submit.
- Password-protected dashboard of all applications, newest first, with
  status.
- Application detail view with Approve / Deny buttons.

**Deliberately not built yet** (the database is already set up to hold
these, so adding them later won't require restructuring anything):
- A photo upload of a handwritten paper application, and text pulled
  from that photo.
- Inspection photos of the applicant's current home, and an inspection
  status.
- Automated emails to property managers (each property already has a
  `property_manager_email` field ready for this — it's just unused for
  now, since property managers don't log into this tool at all).

---

## A note on the two protected-class questions

The form asks for **marital status** and **number of children**. Under
the Fair Housing Act, these are protected categories, and the pilot's
code never uses them to make or influence an approve/deny decision — the
Approve/Deny buttons don't look at those fields at all. They're shown to
the decision-maker for context only. Before using this with real
applicants, it's worth confirming with whoever handles fair-housing
compliance at your company that collecting these fields, and how they're
presented, fits your policy.

---

## Project files, in plain English

| File | What it does |
|---|---|
| `app.py` | The web app itself — all the pages and what happens when you submit the form or click Approve/Deny. |
| `run.py` | The file you actually run. Sets up the database if needed and opens your browser. |
| `seed.py` | Creates the database and fills it with sample properties/applications the first time. |
| `schema.sql` | Describes the structure of the database (what information gets stored). |
| `config.py` | The one file you might edit — the admin password. |
| `templates/` | The actual page layouts (HTML). |
| `static/style.css` | Makes the pages look presentable. |
| `instance/app.db` | The database file itself — created automatically, holds all your real data. Not included in this download; it's created the first time you run the app. |
