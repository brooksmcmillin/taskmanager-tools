"""
Daily Planner PDF Generator
Creates a daily planner PDF with schedule, tasks, and notes sections
"""

import os
from datetime import datetime

from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from taskmanager_sdk import create_authenticated_client
from taskmanager_sdk.exceptions import AuthenticationError

# Load Environment Variables
load_dotenv()

# Create Taskmanager Client
try:
    client = create_authenticated_client(
        os.environ["TASKMANAGER_CLIENT_ID"],
        os.environ["TASKMANAGER_CLIENT_SECRET"],
        base_url=os.environ["TASKMANAGER_URL"],
    )
    print("Authenticated successfully!")
except AuthenticationError as e:
    print(f"Authentication failed: {e}")


def create_daily_planner(filename="daily_planner.pdf"):
    """Create a daily planner PDF with schedule, tasks, and notes sections"""

    # Create canvas with letter size
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter

    # Define margins
    margin = 0.5 * inch
    usable_width = width - (2 * margin)
    usable_height = height - (2 * margin)

    # Define layout proportions
    schedule_width = usable_width * 0.45  # Left side for schedule
    tasks_width = usable_width * 0.55  # Right side for tasks

    # Heights for different sections
    top_section_height = usable_height * 0.60  # Schedule and tasks
    notes_height = usable_height * 0.40  # Notes section at bottom

    # Starting positions
    left_x = margin
    right_x = margin + schedule_width + 0.1 * inch  # Small gap between columns
    top_y = height - margin

    # Title
    c.setFont("Helvetica-Bold", 16)
    title_y = top_y - 0.3 * inch
    date_str = datetime.now().strftime("%A, %B %d, %Y")
    c.drawString(left_x, title_y, date_str)

    # Starting Y position for content
    content_start_y = title_y - 0.5 * inch

    # ============ DAILY SCHEDULE (LEFT SIDE) ============
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left_x, content_start_y, "Daily Schedule")

    # Draw schedule lines (8 AM to 9 PM)
    c.setFont("Helvetica", 10)
    schedule_y = content_start_y - 0.3 * inch
    hours = [
        "8 AM",
        "9 AM",
        "10 AM",
        "11 AM",
        "12 PM",
        "1 PM",
        "2 PM",
        "3 PM",
        "4 PM",
        "5 PM",
        "6 PM",
        "7 PM",
        "8 PM",
        "9 PM",
    ]

    line_spacing = (top_section_height - 1 * inch) / len(hours)

    for i, hour in enumerate(hours):
        y_pos = schedule_y - (i * line_spacing)

        # Draw hour label
        c.drawString(left_x, y_pos, hour)

        # Draw line for writing
        line_x_start = left_x + 0.5 * inch
        line_x_end = left_x + schedule_width - 0.2 * inch
        c.setLineWidth(0.5)
        c.line(line_x_start, y_pos - 2, line_x_end, y_pos - 2)

    # ============ TASKS SECTIONS (RIGHT SIDE) ============

    # Until I update the API to accept filtering by due date, just get the first five tasks
    tasks = client.get_todos().data[0:5]

    # Personal Tasks
    c.setFont("Helvetica-Bold", 12)
    c.drawString(right_x, content_start_y, "Personal Tasks")

    # Draw lines for personal tasks
    c.setFont("Helvetica", 10)
    personal_y_start = content_start_y - 0.3 * inch
    personal_lines = 7
    line_height = 0.25 * inch

    c.setFont("Helvetica", 10)
    for i in range(personal_lines):
        y_pos = personal_y_start - (i * line_height)
        c.setLineWidth(0.5)
        # Checkbox
        c.rect(right_x, y_pos, 12, 12)
        # Line for task
        c.line(right_x + 20, y_pos - 2, right_x + tasks_width - 0.3 * inch, y_pos - 2)
    
        if len(tasks) > i:
            c.drawString(right_x + 20, y_pos, tasks[i]["title"])

    # Work Tasks
    work_tasks_y = personal_y_start - (personal_lines * line_height) - 0.5 * inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(right_x, work_tasks_y, "Work Tasks")

    # Draw lines for work tasks
    work_y_start = work_tasks_y - 0.3 * inch
    work_lines = 7

    for i in range(work_lines):
        y_pos = work_y_start - (i * line_height)
        c.setLineWidth(0.5)
        # Checkbox
        c.rect(right_x, y_pos, 12, 12)
        # Line for task
        c.line(right_x + 20, y_pos - 2, right_x + tasks_width - 0.3 * inch, y_pos - 2)

    # ============ NOTES SECTION (BOTTOM) ============
    notes_y = margin + notes_height

    # Draw separator line
    c.setLineWidth(1)
    c.line(left_x, notes_y, width - margin, notes_y)

    # Notes title
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left_x, notes_y - 0.25 * inch, "Notes")

    # Save the PDF
    c.save()
    print(f"PDF created successfully: {filename}")


if __name__ == "__main__":
    create_daily_planner()
    print("Daily planner PDF has been generated!")
