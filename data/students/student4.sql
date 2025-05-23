WITH RECURSIVE subcourses(id) AS (
    SELECT id FROM Courses WHERE id = 1
    UNION
    SELECT c.id
    FROM Courses c
    JOIN subcourses sc ON c.parent_id = sc.id
),
filtered_enrollments AS (
    SELECT DISTINCT e.student_id
    FROM Enrollments e
    WHERE e.course_id IN (SELECT id FROM subcourses)
)
SELECT s.name
FROM Students s
JOIN filtered_enrollments fe ON s.id = fe.student_id
ORDER BY s.name;
