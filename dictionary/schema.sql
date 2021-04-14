-- Initialize the database.
-- Drop any existing data and create empty tables.

DROP TABLE IF EXISTS word;
DROP TABLE IF EXISTS phrase;
DROP TABLE IF EXISTS rel;
DROP TABLE IF EXISTS user;

CREATE TABLE user (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL
);

CREATE TABLE word (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL,
  user_id INTEGER NOT NULL,
  FOREIGN KEY (user_id) REFERENCES user (id),
  unique (name)
);

CREATE TABLE phrase (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL,
  user_id INTEGER NOT NULL,
  FOREIGN KEY (user_id) REFERENCES user (id),
  unique (name)
);

CREATE TABLE rel (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  mainWordId INTEGER NOT NULL,
  phraseWordId INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  FOREIGN KEY (user_id) REFERENCES user (id),
  FOREIGN KEY (mainWordId) REFERENCES word (id),
  FOREIGN KEY (phraseWordId) REFERENCES word (id),
  unique (mainWordId, phraseWordId)
);

CREATE TABLE phrel (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  phraseId INTEGER NOT NULL,
  wordId INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  FOREIGN KEY (user_id) REFERENCES user (id),
  FOREIGN KEY (phraseId) REFERENCES phrase (id),
  FOREIGN KEY (wordId) REFERENCES word (id),
  unique (phraseId, wordId)
);