from faker import Faker
from datetime import date, timedelta
import random
import psycopg2
from psycopg2.extras import RealDictCursor
import time

fake = Faker("vi_VN")

# Add a slight delay to ensure DB is fully ready if run right after docker-compose up
print("Waiting for database connection...")
time.sleep(2)

conn = psycopg2.connect(
    dbname="ai_pm_copilot",
    user="postgres",
    password="postgres",
    host="localhost",
    port="5432"
)

cur = conn.cursor(cursor_factory=RealDictCursor)

roles = ["ADMIN", "DIRECTOR", "PM", "TEAM_LEAD", "DEVELOPER", "QA"]

users = []

print("Seeding users...")
for role in roles:
    count = {
        "ADMIN": 1,
        "DIRECTOR": 1,
        "PM": 3,
        "TEAM_LEAD": 2,
        "DEVELOPER": 5,
        "QA": 3
    }[role]

    for _ in range(count):
        cur.execute("""
            INSERT INTO users (full_name, email, global_role)
            VALUES (%s, %s, %s)
            RETURNING id, full_name, email, global_role
        """, (
            fake.name(),
            fake.unique.email(),
            role
        ))
        users.append(cur.fetchone())

projects = [
    ("CRM Internal System", "Hệ thống CRM nội bộ cho đội sales và chăm sóc khách hàng."),
    ("E-commerce Platform", "Nền tảng thương mại điện tử với giỏ hàng, thanh toán và quản lý đơn hàng."),
    ("AI Project Management Copilot", "Hệ thống quản lý dự án tích hợp AI Agent, RAG, báo cáo và cảnh báo rủi ro.")
]

project_rows = []

pm_users = [u for u in users if u["global_role"] == "PM"]
dev_users = [u for u in users if u["global_role"] == "DEVELOPER"]
qa_users = [u for u in users if u["global_role"] == "QA"]
lead_users = [u for u in users if u["global_role"] == "TEAM_LEAD"]

print("Seeding projects and members...")
for index, (name, description) in enumerate(projects):
    pm = pm_users[index % len(pm_users)]

    cur.execute("""
        INSERT INTO projects (name, description, status, start_date, end_date, created_by)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id, name
    """, (
        name,
        description,
        "active",
        date.today() - timedelta(days=30),
        date.today() + timedelta(days=60),
        pm["id"]
    ))

    project = cur.fetchone()
    project_rows.append(project)

    members = [
        (pm, "PM"),
        (lead_users[index % len(lead_users)], "TEAM_LEAD"),
        (dev_users[index % len(dev_users)], "DEVELOPER"),
        (dev_users[(index + 1) % len(dev_users)], "DEVELOPER"),
        (qa_users[index % len(qa_users)], "QA")
    ]

    for user, role in members:
        cur.execute("""
            INSERT INTO project_members (project_id, user_id, role)
            VALUES (%s, %s, %s)
            ON CONFLICT (project_id, user_id) DO NOTHING
        """, (
            project["id"],
            user["id"],
            role
        ))

task_titles = [
    "Thiết kế database schema",
    "Tạo API tạo project",
    "Tạo API tạo task",
    "Xây dựng màn hình kanban board",
    "Tạo API upload document",
    "Chunk tài liệu cho RAG",
    "Tạo embedding cho document chunks",
    "Xây dựng Project QA Agent",
    "Lưu chat history",
    "Tạo daily report bằng AI",
    "Phát hiện task quá deadline",
    "Review RBAC cho project members"
]

statuses = ["todo", "in_progress", "review", "done", "blocked"]
priorities = ["low", "medium", "high", "urgent"]

print("Seeding sprints, tasks and comments...")
for project in project_rows:
    for sprint_no in range(1, 3):
        cur.execute("""
            INSERT INTO sprints (project_id, name, goal, start_date, end_date, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            project["id"],
            f"Sprint {sprint_no}",
            f"Hoàn thành các chức năng chính của sprint {sprint_no}",
            date.today() - timedelta(days=14 * (2 - sprint_no)),
            date.today() + timedelta(days=14 * sprint_no),
            "active" if sprint_no == 2 else "completed"
        ))

        sprint = cur.fetchone()

        cur.execute("""
            SELECT u.id
            FROM users u
            JOIN project_members pm ON pm.user_id = u.id
            WHERE pm.project_id = %s
              AND pm.role IN ('DEVELOPER', 'QA', 'TEAM_LEAD')
        """, (project["id"],))

        assignees = cur.fetchall()

        for i in range(10):
            status = random.choice(statuses)
            priority = random.choice(priorities)

            due_date = date.today() + timedelta(days=random.randint(-7, 21))

            cur.execute("""
                INSERT INTO tasks (
                    project_id, sprint_id, title, description,
                    status, priority, task_type,
                    assignee_id, due_date, estimate_hours, actual_hours
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                project["id"],
                sprint["id"],
                random.choice(task_titles),
                fake.paragraph(nb_sentences=3),
                status,
                priority,
                "feature",
                random.choice(assignees)["id"],
                due_date,
                random.choice([4, 8, 12, 16, 24]),
                random.choice([0, 2, 4, 6, 8, 12])
            ))

            task = cur.fetchone()

            for _ in range(random.randint(0, 3)):
                commenter = random.choice(assignees)
                cur.execute("""
                    INSERT INTO comments (task_id, user_id, content)
                    VALUES (%s, %s, %s)
                """, (
                    task["id"],
                    commenter["id"],
                    fake.sentence()
                ))

print("Seeding documents...")
cur.execute("""
    INSERT INTO documents (project_id, filename, file_type, extracted_text)
    VALUES (
        %s,
        'requirement-ai-pm-copilot.md',
        'markdown',
        'Hệ thống cho phép PM tạo task bằng ngôn ngữ tự nhiên, hỏi đáp tài liệu dự án, tạo daily report và cảnh báo rủi ro.'
    )
""", (project_rows[2]["id"],)) # AI Project Management Copilot

print("Seeding risk events...")
cur.execute("""
    INSERT INTO risk_events (
        project_id,
        risk_type,
        severity,
        title,
        description,
        suggestion,
        status
    )
    VALUES
    (
        %s,
        'sprint_delay',
        'high',
        'Sprint có nguy cơ trễ tiến độ',
        'Sprint còn ít ngày nhưng nhiều task đang ở trạng thái todo hoặc blocked.',
        'PM nên ưu tiên xử lý các task blocked và giảm scope nếu cần.',
        'open'
    ),
    (
        %s,
        'overdue_task',
        'medium',
        'Một số task đã quá deadline',
        'Có task quá hạn nhưng chưa hoàn thành.',
        'Team Lead cần kiểm tra lại assignee và cập nhật tiến độ.',
        'open'
    )
""", (project_rows[2]["id"], project_rows[2]["id"]))

conn.commit()
cur.close()
conn.close()

print("Seed data created successfully.")
