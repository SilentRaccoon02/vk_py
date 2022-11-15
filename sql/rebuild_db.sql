DROP TABLE IF EXISTS
    users,
    subs,
    users_subs
    CASCADE;


CREATE TABLE IF NOT EXISTS users
(
    id         serial PRIMARY KEY,
    status     integer     NOT NULL DEFAULT 0,
    user_id    integer     NOT NULL UNIQUE,
    first_name varchar(64) NOT NULL,
    last_name  varchar(64) NOT NULL
);


CREATE TABLE IF NOT EXISTS subs
(
    id       serial PRIMARY KEY,
    sub_id   integer      NOT NULL UNIQUE,
    sub_name varchar(128) NOT NULL,
    category varchar(64)
);


CREATE TABLE IF NOT EXISTS users_subs
(
    id      serial PRIMARY KEY,
    user_id integer NOT NULL REFERENCES users (user_id) ON DELETE RESTRICT,
    sub_id  integer NOT NULL REFERENCES subs (sub_id) ON DELETE RESTRICT,
    UNIQUE (user_id, sub_id)
);
