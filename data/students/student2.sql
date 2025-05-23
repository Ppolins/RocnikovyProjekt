WITH RECURSIVE subcourses(id) AS (
    SELECT id FROM Courses WHERE id = 1
    UNION ALL
    SELECT c.id FROM Courses c
    JOIN subcourses sc ON c.parent_id = sc.id
)
SELECT s.name
FROM Students s
JOIN Enrollments e ON s.id = e.student_id
WHERE e.course_id IN (SELECT id FROM subcourses);
