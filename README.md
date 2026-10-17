# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Paste a sample of your app's CLI or Streamlit output here so a reader can see what a generated plan looks like:

Plan for Rick on 2026-10-17:
  07:00-07:30  Mochi: Morning walk (30 min; high priority, preferred after 07:00)
  07:30-07:40  Luna: Breakfast (10 min; high priority, preferred after 07:30)
  07:40-07:45  Pip: Give meds (5 min; high priority)
  08:30-08:50  Pip: Clean hutch (20 min; medium priority, preferred after 08:30)
  10:00-10:45  Mochi: Play fetch (45 min; medium priority, preferred after 10:00)
  10:45-11:00  Luna: Brush fur (15 min; low priority, preferred after 09:30)
Total scheduled: 125 of 240 available minutes.

## 🧪 Testing PawPal+

```bash
# Run the full test suite:
pytest

# Run with coverage:
pytest --cov
```

Automated test suite covers edge cases, sorting correctness, conflict handling, recurrence logic, and core logic.
Confidence level: 4/5


Sample test output:

collected 29 items                                                                                                     

tests/test_pawpal.py .............................                                                               [100%]

================================================== 29 passed in 0.08s ==================================================

## 📐 Smarter Scheduling

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | `Scheduler.sort_by_priority()`, `Scheduler.sort_by_time()` | Planning order is priority (high first), then preferred time (earliest first, none last), then shorter duration. `sort_by_time()` orders by preferred time only, for display. Both are stable, so ties keep insertion order. |
| Filtering | `Scheduler.filter_tasks(on, pet_name, status)` | Filter by pet name and by status: `"due"` (incomplete and due or overdue on `on`), `"done"` (completed), or `None` (all). Tasks that fit in no free gap are skipped with a reason (`plan.skipped`). |
| Time placement | `Scheduler.generate_plan()` | Tracks free gaps in the owner's window and places each task in the earliest gap that starts at or after its preferred time and is long enough, so a late high-priority task doesn't waste the morning. |
| Conflict handling | `Scheduler.find_requested_conflicts()`, `Scheduler.detect_conflicts()` | Tasks whose requested times overlap (same pet or different pets) are reported as warnings in `plan.conflicts` instead of raising errors. The higher-priority task keeps its slot and the other moves to the next free gap, so the final plan never overlaps. |
| Recurring tasks | `Pet.complete_task()`, `Task.mark_complete()`, `Task.is_due()`, `Task.next_due_date()` | Each task is one occurrence with a `due_date`. Completing a DAILY or WEEKLY task adds a new occurrence due 1 or 7 days after the completion date. ONCE tasks don't recur. Completed tasks stay as history. |


## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. Run `streamlit run app.py`, then enter the owner's name, pet's name and species, what time the day starts (e.g. 08:00), and how many minutes are available (e.g. 120).
2. Add tasks with a title, duration, priority, optional preferred time, and repeat setting, e.g. "Morning walk" (30 min, high, 08:00, daily) and "Breakfast" (10 min, medium, 08:15, daily).
3. Review the task table, filtering it to *Due today*, *Completed*, or *All* and sorting it by *Priority* or *Preferred time*.
4. Watch for yellow warnings when two tasks' preferred times overlap, like the walk and breakfast above, which tell you the scheduler will shift one of them.
5. Click **Generate schedule** to see a summary banner, metrics for tasks scheduled, minutes used, and tasks skipped, and a time-ordered plan table.
6. The scheduler places tasks by priority, then preferred time, then shortest duration, putting each one in the earliest free slot at or after its preferred time, so the walk runs 08:00–08:30 and breakfast moves to 08:30–08:40.
7. Tasks that fit nowhere, such as a 200-minute grooming session in a 120-minute day, appear as skipped warnings with the reason displayed.
8. Expand **Why this plan?** for a plain-text explanation of each scheduled task, the total time used, and any skipped tasks or conflicts.
9. Use **Mark complete** on a due task to record it; daily and weekly tasks automatically get a next occurrence due tomorrow or in a week.



**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
