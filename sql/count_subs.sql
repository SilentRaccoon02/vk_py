SELECT subs.sub_name,
       subs.sub_id,
       subs.category,
       count_n.n
FROM (SELECT users_subs.sub_id,
             COUNT(users_subs.sub_id) AS n
      FROM users_subs
      GROUP BY users_subs.sub_id) AS count_n
         JOIN subs ON subs.sub_id = count_n.sub_id
ORDER BY count_n.n DESC
LIMIT 200;
