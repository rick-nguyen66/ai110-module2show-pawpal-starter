import streamlit as st
from pawpal_system import Frequency, Owner, Pet, Priority, Scheduler, Task
from datetime import date, time

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

st.subheader("Quick Demo Inputs (UI only)")
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


st.markdown("### Tasks")
st.caption("Add a few tasks. In your final version, these should feed into your scheduler.")

if "tasks" not in st.session_state:
    st.session_state.tasks = []

col1, col2, col3 = st.columns(3)
with col1:
    task_title = st.text_input("Task title", value="Morning walk")
with col2:
    duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
with col3:
    priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)

if st.button("Add task"):
    try:
        pet.add_task(Task(task_title, int(duration), Priority[priority.upper()]))
    except ValueError as e:
        st.error(str(e))

if pet.tasks:
    st.table([
        {"title": t.title, "duration_minutes": t.duration_minutes, "priority": t.priority.name.lower()}
        for t in pet.tasks
    ])
else:
    st.info("No tasks yet. Add one above.")

st.divider()

st.subheader("Build Schedule")
st.caption("This button should call your scheduling logic once you implement it.")

if st.button("Generate schedule"):
    scheduler = Scheduler(owner)
    plan = scheduler.generate_plan(date.today())
    if plan.entries:
        st.table([
            {"time": f"{e.start:%H:%M}-{e.end:%H:%M}", "pet": e.pet.name,
             "task": e.task.title, "priority": e.task.priority.name.lower()}
            for e in plan.entries
        ])
    for s in plan.skipped:
        st.warning(f"Skipped {s.task.title}: {s.reason}")
    st.text(scheduler.explain_plan(plan))
