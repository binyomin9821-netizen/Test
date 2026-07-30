-- Reference schema (Postgres/MySQL-flavored). SQLAlchemy creates this
-- automatically via db.create_all() when the app starts, using the
-- DATABASE_URL you configure; this file is for reference / manual setup
-- against a production SQL database.

CREATE TABLE IF NOT EXISTS applications (
    id                  SERIAL PRIMARY KEY,
    full_name           VARCHAR(200) NOT NULL,
    phone               VARCHAR(50)  NOT NULL,
    email               VARCHAR(200) NOT NULL,
    current_address     VARCHAR(400) NOT NULL,
    marital_status      VARCHAR(50),
    number_of_children  INTEGER,
    status              VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ocr_raw_text        TEXT,
    ocr_needs_review    BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    username        VARCHAR(120) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    role            VARCHAR(20) NOT NULL DEFAULT 'inspector'
);

CREATE TABLE IF NOT EXISTS inspection_photos (
    id              SERIAL PRIMARY KEY,
    application_id  INTEGER NOT NULL REFERENCES applications(id),
    s3_bucket       VARCHAR(200) NOT NULL,
    s3_key          VARCHAR(500) NOT NULL,
    uploaded_by_id  INTEGER REFERENCES users(id),
    uploaded_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
