SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM subs;
SELECT COUNT(*) FROM users_subs;

SELECT * FROM users WHERE user_id = -1;
DELETE FROM users WHERE user_id = -1;

SELECT pg_size_pretty(pg_total_relation_size('users'));
SELECT pg_size_pretty(pg_total_relation_size('subs'));
SELECT pg_size_pretty(pg_total_relation_size('users_subs'));
