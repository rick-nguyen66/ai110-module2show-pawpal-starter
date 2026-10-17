import streamlit as st
from pawpal_system import Frequency, Owner, Pet, Priority, Scheduler, Task
from datetime import date, time

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferred times.
"""
)

PRIORITY_BADGE = {Priority.HIGH: "🔴 high", Priority.MEDIUM: "🟡 medium", Priority.LOW: "🟢 low"}


def fmt_time(t: time | None) -> str:
    """Format an optional time as HH:MM, or a dash when unset."""
    return t.strftime("%H:%M") if t is not None else "—"


def task_rows(items) -> list[dict]:
    """Turn (pet, task) pairs into table rows."""
    return [
        {
            "Pet": pet.name,
            "Task": task.title,
            "Priority": PRIORITY_BADGE[task.priority],
            "Duration (min)": task.duration_minutes,
            "Preferred time": fmt_time(task.preferred_time),
            "Repeats": task.frequency.value,
            "Due": task.due_date.isoformat() if task.due_date else "today",
            "Status": f"✅ done {task.last_completed.isoformat()}" if task.is_complete else "⏳ pending",
        }
        for pet, task in items
    ]


st.divider()

st.subheader("Owner & Pet")
owner_name = st.text_input("Owner name", value="Jordan")
pet_name = st.text_input("Pet name", value="Mochi")
species = st.selectbox("Species", ["dog", "cat", "other"])

day_start = st.time_input("Day starts at", value=time(8, 0))
available = st.number_input("Available minutes", min_value=0, max_value=1440, value=120)

# essentially a dictionary holding states
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name=owner_name)
    st.session_state.owner.add_pet(Pet(name=pet_name, species=species))

owner: Owner = st.session_state.owner
pet: Pet = owner.pets[0]
owner.name, owner.day_start, owner.available_minutes = owner_name, day_start, int(available)
pet.name, pet.species = pet_name, species
scheduler = Scheduler(owner)
today = date.today()


st.markdown("### Tasks")

col1, col2, col3 = st.columns(3)
with col1:
    task_title = st.text_input("Task title", value="Morning walk")
with col2:
    duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
with col3:
    priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)

col4, col5 = st.columns(2)
with col4:
    preferred = st.time_input("Preferred time (optional)", value=None)
with col5:
    frequency = st.selectbox("Repeats", [f.value for f in Frequency], index=1)

if st.button("Add task"):
    try:
        pet.add_task(Task(task_title, int(duration), Priority[priority.upper()],
                          frequency=Frequency(frequency), preferred_time=preferred))
        st.success(f"Added '{task_title}' for {pet.name}.")
    except ValueError as e:
        st.error(str(e))

if pet.tasks:
    fcol, scol = st.columns(2)
    with fcol:
        status_label = st.radio("Show", ["Due today", "Completed", "All"], horizontal=True)
    with scol:
        sort_label = st.radio("Sort by", ["Priority", "Preferred time"], horizontal=True)

    status = {"Due today": "due", "Completed": "done", "All": None}[status_label]
    items = scheduler.filter_tasks(today, status=status)
    items = scheduler.sort_by_priority(items) if sort_label == "Priority" else scheduler.sort_by_time(items)

    if items:
        st.table(task_rows(items))
    else:
        st.info(f"No tasks match '{status_label}'.")

    due = scheduler.filter_tasks(today)
    conflicts = scheduler.find_requested_conflicts(due, today)
    for conflict in conflicts:
        st.warning(f"⚠️ Preferred times overlap: {conflict.reason}. "
                   "The scheduler will shift one of them to a later free slot.")

    if due:
        with st.form("complete_task"):
            choice = st.selectbox(
                "Mark a task complete",
                range(len(due)),
                format_func=lambda i: f"{due[i][0].name}: {due[i][1].title}",
            )
            if st.form_submit_button("Mark complete"):
                done_pet, done_task = due[choice]
                next_task = done_pet.complete_task(done_task, today)
                if next_task is not None:
                    st.session_state.flash = (f"Completed '{done_task.title}'. "
                                              f"Next occurrence due {next_task.due_date.isoformat()}.")
                else:
                    st.session_state.flash = f"Completed '{done_task.title}'."
                st.rerun()

    if "flash" in st.session_state:
        st.success(st.session_state.pop("flash"))
else:
    st.info("No tasks yet. Add one above.")

st.divider()

st.subheader("Build Schedule")
st.caption("Tasks are placed by priority, then preferred time, then shortest duration.")

if st.button("Generate schedule"):
    plan = scheduler.generate_plan(today)
    total = sum(e.task.duration_minutes for e in plan.entries)

    if plan.entries:
        st.success(f"Scheduled {len(plan.entries)} task(s) for {owner.name} on {plan.day:%A, %b %d}.")
        m1, m2, m3 = st.columns(3)
        m1.metric("Scheduled", len(plan.entries))
        m2.metric("Minutes used", f"{total} / {owner.available_minutes}")
        m3.metric("Skipped", len(plan.skipped))

        st.table([
            {
                "Time": f"{e.start:%H:%M}–{e.end:%H:%M}",
                "Pet": e.pet.name,
                "Task": e.task.title,
                "Priority": PRIORITY_BADGE[e.task.priority],
                "Duration (min)": e.task.duration_minutes,
                "Preferred time": fmt_time(e.task.preferred_time),
            }
            for e in plan.entries
        ])
    else:
        st.info("No tasks could be scheduled for today.")

    for conflict in plan.conflicts:
        st.warning(f"⚠️ Conflict resolved: {conflict.reason}. The lower-priority (or later-sorted) task was shifted.")
    for s in plan.skipped:
        st.warning(f"⏭️ Skipped **{s.task.title}** ({s.pet.name}): {s.reason}")

    with st.expander("Why this plan?"):
        st.text(scheduler.explain_plan(plan))
