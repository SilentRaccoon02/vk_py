SELECT cats.category,
       COUNT(DISTINCT user_id) AS total
FROM (SELECT users.user_id,
             subs.category
      FROM users
               JOIN users_subs ON users.user_id = users_subs.user_id
               JOIN subs ON subs.sub_id = users_subs.sub_id
      WHERE subs.category IS NOT NULL) AS cats
GROUP BY cats.category
ORDER BY total DESC;
