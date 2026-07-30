-- Database structure for the tenant application pilot.
-- This file is read once by seed.py to create the database file.

-- One row per property/building in the portfolio.
CREATE TABLE IF NOT EXISTS properties (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    name                    TEXT NOT NULL,
    address                 TEXT NOT NULL,
    property_manager_email  TEXT
    -- property_manager_email isn't used yet. Later, this is the address
    -- automated emails to that building's manager will be sent to.
);

-- One row per tenant application.
CREATE TABLE IF NOT EXISTS applications (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id             INTEGER NOT NULL REFERENCES properties(id),

    -- Part 1: basic info
    full_name               TEXT NOT NULL,
    phone                   TEXT NOT NULL,
    email                   TEXT NOT NULL,
    current_address         TEXT NOT NULL,

    -- Part 2: household info
    marital_status           TEXT,
    number_of_children       INTEGER,

    -- Decision-maker workflow
    status                  TEXT NOT NULL DEFAULT 'Pending',   -- Pending / Approved / Denied
    created_at              TEXT NOT NULL DEFAULT (datetime('now')),
    decision_date           TEXT,

    -- Reserved for future stages (unused for now, columns exist so nothing
    -- needs to change later): a photo of the handwritten paper form, the
    -- text pulled out of that photo, and the current status of the
    -- in-person home inspection.
    paper_form_photo_path    TEXT,
    ocr_extracted_text       TEXT,
    inspection_status        TEXT
);

-- Reserved for a future stage: inspection photos of the tenant's current
-- home. Not used yet, but the table exists so it can be filled in later
-- without changing anything already built.
CREATE TABLE IF NOT EXISTS inspection_photos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id  INTEGER NOT NULL REFERENCES applications(id),
    photo_path      TEXT NOT NULL,
    uploaded_at     TEXT NOT NULL DEFAULT (datetime('now'))
);
