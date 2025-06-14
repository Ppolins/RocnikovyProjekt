SELECT s.name
FROM Students s
JOIN Enrollments e ON s.id = e.student_id
JOIN Courses c ON e.course_id = c.id
WHERE c.id = 1 OR c.parent_id = 1;

/*
toto pre testovanie TLE
WITH RECURSIVE cnt(x) AS (
  SELECT 1
  UNION ALL
  SELECT x+1 FROM cnt
)
SELECT * FROM cnt;*/
