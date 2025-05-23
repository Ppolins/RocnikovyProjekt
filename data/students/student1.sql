SELECT s.name
FROM Students s
JOIN Enrollments e ON s.id = e.student_id
JOIN Courses c ON e.course_id = c.id
WHERE c.id = 1 OR c.parent_id = 1;
