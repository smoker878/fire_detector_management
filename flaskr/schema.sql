-- Initialize the database.
-- Drop any existing data and create empty tables.
DROP TABLE IF EXISTS User;
DROP TABLE IF EXISTS BypassRequistion;
DROP TABLE IF EXISTS Bypass_device;


CREATE TABLE User (
  user_id INTEGER PRIMARY KEY NOT NULL,
  username TEXT  NOT NULL,
  password TEXT NOT NULL,
  department TEXT NOT NULL
);

CREATE TABLE BypassRequistion (
requistion_id INTEGER PRIMARY KEY,
apply_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
apply_department TEXT NOT NULL,
applier_id INTEGER NOT NULL,
applier TEXT NOT NULL,
predict_to_work_date DATE ,
work_id INTEGER  NOT NULL,
work_name TEXT ,
contractor TEXT,
other_message TEXT,
excute_date TIMESTAMP,
excute_department TEXT,
excutor_id INTEGER,
excutor TEXT,
reset_date TIMESTAMP,
reset_department TEXT,
reset_person_id INTEGER,
reset_person TEXT
);

CREATE TABLE Bypass_device (
requistion_id INTEGER,
device TEXT
);

CREATE VIEW CurrentBypass AS
SELECT DISTINCT device FROM Bypass_device
WHERE requistion_id in(
SELECT requistion_id FROM BypassRequistion
WHERE excutor_id is not NULL
AND reset_person_id is NULL);

