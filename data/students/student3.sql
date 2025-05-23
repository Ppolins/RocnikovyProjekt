WITH RECURSIVE
  subcourses(id) AS (
    SELECT id FROM Courses WHERE id = 1
    UNION ALL
    SELECT c.id
    FROM Courses c
    JOIN subcourses sc ON c.parent_id = sc.id
  ),
  enrolled_students AS (
    SELECT e.student_id, COUNT(DISTINCT e.course_id) AS enrolled_count
    FROM Enrollments e
    WHERE e.course_id IN (SELECT id FROM subcourses)
    GROUP BY e.student_id
  ),
  total_courses AS (
    SELECT COUNT(*) AS total FROM subcourses
  )
SELECT s.name
FROM Students s
JOIN enrolled_students es ON s.id = es.student_id
JOIN total_courses tc
WHERE es.enrolled_count = tc.total;
