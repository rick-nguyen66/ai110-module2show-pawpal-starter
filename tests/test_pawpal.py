"""Tests for PawPal+ core behavior."""

from datetime import date, datetime, time, timedelta

import pytest

from pawpal_system import Frequency, Owner, Pet, Priority, Scheduler, Task

TODAY = date(2026, 10, 17)


def make_scheduler(*pets: Pet, day_start: time = time(8, 0), available_minutes: int = 240) -> Scheduler:
    """Build a Scheduler for an owner with the given pets and time window."""
    owner = Owner(name="Rick", day_start=day_start, available_minutes=available_minutes)
    for pet in pets:
        owner.add_pet(pet)
    return Scheduler(owner)


def at(hour: int, minute: int = 0) -> datetime:
    """Return a datetime on TODAY at the given time."""
    return datetime.combine(TODAY, time(hour, minute))


# --- Basics -----------------------------------------------------------------


def test_mark_complete_changes_task_status():
    """mark_complete() records the date and the task is no longer due that day."""
    task = Task(title="Morning walk", duration_minutes=30)
    assert task.last_completed is None
    assert task.is_due(TODAY)

    task.mark_complete(TODAY)

    assert task.last_completed == TODAY
    assert not task.is_due(TODAY)


def test_add_task_increases_pet_task_count():
    """add_task() grows the pet's task list by one per added task."""
    pet = Pet(name="Mochi", species="dog")
    assert len(pet.get_tasks()) == 0

    pet.add_task(Task(title="Feed breakfast", duration_minutes=10))
    assert len(pet.get_tasks()) == 1

    pet.add_task(Task(title="Evening walk", duration_minutes=20))
    assert len(pet.get_tasks()) == 2


# --- Sorting correctness ----------------------------------------------------


def test_sort_by_time_returns_chronological_order_with_untimed_last():
    """sort_by_time() orders by preferred_time, earliest first, untimed tasks last."""
    pet = Pet(name="Mochi", species="dog")
    evening = Task("Evening walk", 20, preferred_time=time(18, 0))
    untimed = Task("Brush", 10)
    morning = Task("Breakfast", 10, preferred_time=time(7, 30))
    noon = Task("Lunch", 10, preferred_time=time(12, 0))
    items = [(pet, t) for t in (evening, untimed, morning, noon)]

    ordered = [task for _, task in make_scheduler(pet).sort_by_time(items)]

    assert ordered == [morning, noon, evening, untimed]


def test_plan_entries_are_in_chronological_order():
    """generate_plan() returns entries sorted by start time, not by priority."""
    pet = Pet(name="Mochi", species="dog")
    pet.add_task(Task("Meds", 10, priority=Priority.HIGH, preferred_time=time(11, 0)))
    pet.add_task(Task("Play", 30, priority=Priority.LOW))
    pet.add_task(Task("Walk", 30, priority=Priority.MEDIUM, preferred_time=time(9, 0)))

    plan = make_scheduler(pet).generate_plan(TODAY)

    starts = [entry.start for entry in plan.entries]
    assert starts == sorted(starts)
    assert [e.task.title for e in plan.entries] == ["Play", "Walk", "Meds"]
    for earlier, later in zip(plan.entries, plan.entries[1:]):
        assert earlier.end <= later.start  # no overlaps in the final plan


def test_sort_by_priority_puts_priority_before_time():
    """A late high-priority task sorts ahead of an early low-priority task."""
    pet = Pet(name="Mochi", species="dog")
    early_low = Task("Early low", 10, priority=Priority.LOW, preferred_time=time(8, 0))
    late_high = Task("Late high", 10, priority=Priority.HIGH, preferred_time=time(18, 0))

    ordered = make_scheduler(pet).sort_by_priority([(pet, early_low), (pet, late_high)])

    assert [task for _, task in ordered] == [late_high, early_low]


def test_sort_by_priority_tie_breakers():
    """Equal priority: earlier time, then untimed last, then shorter, then insertion order."""
    pet = Pet(name="Mochi", species="dog")
    timed = Task("Timed", 30, preferred_time=time(9, 0))
    long_untimed = Task("Long", 30)
    short_untimed = Task("Short", 5)
    short_untimed_twin = Task("Short twin", 5)
    items = [(pet, t) for t in (long_untimed, short_untimed, short_untimed_twin, timed)]

    ordered = [task for _, task in make_scheduler(pet).sort_by_priority(items)]

    assert ordered == [timed, short_untimed, short_untimed_twin, long_untimed]


def test_priority_string_is_coerced_and_invalid_rejected():
    """Priority accepts names like 'high' and rejects unknown names."""
    assert Task("Meds", 5, priority="high").priority is Priority.HIGH
    with pytest.raises(KeyError):
        Task("Meds", 5, priority="urgent")


# --- Recurrence logic -------------------------------------------------------


def test_completing_daily_task_creates_task_for_following_day():
    """Completing a daily task adds a fresh occurrence due the next day."""
    pet = Pet(name="Mochi", species="dog")
    walk = Task("Walk", 30, priority=Priority.HIGH, frequency=Frequency.DAILY, preferred_time=time(8, 0))
    pet.add_task(walk)

    next_walk = pet.complete_task(walk, TODAY)

    assert next_walk is not None and next_walk is not walk
    assert next_walk.due_date == TODAY + timedelta(days=1)
    assert next_walk.last_completed is None
    assert walk.is_complete  # original stays as history
    assert pet.get_tasks() == [walk, next_walk]
    # Settings carry over to the next occurrence.
    assert (next_walk.title, next_walk.duration_minutes, next_walk.priority, next_walk.preferred_time) == (
        "Walk", 30, Priority.HIGH, time(8, 0)
    )


def test_next_daily_occurrence_is_not_scheduled_today_but_is_tomorrow():
    """The new occurrence shows up in tomorrow's plan, not today's."""
    pet = Pet(name="Mochi", species="dog")
    walk = Task("Walk", 30)
    pet.add_task(walk)
    scheduler = make_scheduler(pet)

    next_walk = pet.complete_task(walk, TODAY)

    assert scheduler.generate_plan(TODAY).entries == []
    assert [e.task for e in scheduler.generate_plan(TODAY + timedelta(days=1)).entries] == [next_walk]


def test_completing_weekly_task_creates_task_seven_days_later():
    """Weekly tasks recur one week after completion."""
    pet = Pet(name="Mochi", species="dog")
    bath = Task("Bath", 45, frequency=Frequency.WEEKLY)
    pet.add_task(bath)

    next_bath = pet.complete_task(bath, TODAY)

    assert next_bath.due_date == TODAY + timedelta(days=7)


def test_completing_once_task_does_not_recur():
    """One-time tasks return None and add nothing to the pet."""
    pet = Pet(name="Mochi", species="dog")
    vet = Task("Vet visit", 60, frequency=Frequency.ONCE)
    pet.add_task(vet)

    assert pet.complete_task(vet, TODAY) is None
    assert pet.get_tasks() == [vet]


def test_late_completion_counts_from_completion_date():
    """An overdue daily task completed late recurs from the completion date."""
    overdue = Task("Walk", 30, due_date=TODAY - timedelta(days=7))
    assert overdue.is_due(TODAY)

    next_walk = overdue.mark_complete(TODAY)

    assert next_walk.due_date == TODAY + timedelta(days=1)


@pytest.mark.parametrize(
    ("completed_on", "expected"),
    [
        (date(2026, 12, 31), date(2027, 1, 1)),
        (date(2028, 2, 28), date(2028, 2, 29)),  # leap year
    ],
)
def test_daily_recurrence_crosses_calendar_boundaries(completed_on, expected):
    """Daily recurrence rolls over year ends and leap days."""
    assert Task("Walk", 30).mark_complete(completed_on).due_date == expected


def test_completing_task_twice_raises_and_adds_no_duplicate():
    """Completing an already-completed occurrence is rejected."""
    pet = Pet(name="Mochi", species="dog")
    walk = Task("Walk", 30)
    pet.add_task(walk)
    pet.complete_task(walk, TODAY)

    with pytest.raises(ValueError):
        pet.complete_task(walk, TODAY)
    assert len(pet.get_tasks()) == 2


def test_complete_task_rejects_task_from_another_pet():
    """complete_task() only accepts this pet's own tasks."""
    pet = Pet(name="Mochi", species="dog")
    with pytest.raises(ValueError):
        pet.complete_task(Task("Walk", 30), TODAY)


# --- Conflict detection -----------------------------------------------------


def test_duplicate_preferred_times_are_flagged():
    """Two tasks requesting the exact same time are reported as a conflict."""
    dog = Pet(name="Mochi", species="dog")
    cat = Pet(name="Tofu", species="cat")
    dog.add_task(Task("Walk", 30, preferred_time=time(9, 0)))
    cat.add_task(Task("Feed", 10, preferred_time=time(9, 0)))

    plan = make_scheduler(dog, cat).generate_plan(TODAY)

    assert len(plan.conflicts) == 1
    conflict = plan.conflicts[0]
    assert {conflict.first.task.title, conflict.second.task.title} == {"Walk", "Feed"}
    assert "Walk" in conflict.reason and "Feed" in conflict.reason
    # The owner still does one thing at a time: both are scheduled without overlap.
    first, second = plan.entries
    assert first.end <= second.start


def test_back_to_back_times_are_not_a_conflict():
    """Intervals are half-open, so one task ending as another starts is fine."""
    pet = Pet(name="Mochi", species="dog")
    items = [
        (pet, Task("Walk", 30, preferred_time=time(8, 0))),
        (pet, Task("Feed", 30, preferred_time=time(8, 30))),
    ]

    assert make_scheduler(pet).find_requested_conflicts(items, TODAY) == []


def test_nested_and_triple_overlaps_are_all_flagged():
    """Every overlapping pair is reported, including a task nested inside another."""
    pet = Pet(name="Mochi", species="dog")
    items = [
        (pet, Task("Long walk", 60, preferred_time=time(8, 0))),
        (pet, Task("Meds", 5, preferred_time=time(8, 15))),
        (pet, Task("Feed", 10, preferred_time=time(8, 15))),
    ]

    conflicts = make_scheduler(pet).find_requested_conflicts(items, TODAY)

    pairs = {frozenset((c.first.task.title, c.second.task.title)) for c in conflicts}
    assert pairs == {
        frozenset(("Long walk", "Meds")),
        frozenset(("Long walk", "Feed")),
        frozenset(("Meds", "Feed")),
    }


def test_untimed_and_completed_tasks_are_not_flagged():
    """Only due tasks with a preferred_time can conflict."""
    pet = Pet(name="Mochi", species="dog")
    done = Task("Walk", 30, preferred_time=time(9, 0))
    pet.add_task(done)
    pet.add_task(Task("Feed", 10, preferred_time=time(9, 0), frequency=Frequency.ONCE))
    pet.add_task(Task("Brush", 10))
    pet.complete_task(done, TODAY)

    assert make_scheduler(pet).generate_plan(TODAY).conflicts == []


# --- Slot fitting -----------------------------------------------------------


def test_lower_priority_task_fills_gap_before_high_priority_task():
    """A high-priority task placed mid-window leaves an earlier gap for others."""
    pet = Pet(name="Mochi", species="dog")
    pet.add_task(Task("Meds", 30, priority=Priority.HIGH, preferred_time=time(10, 0)))
    pet.add_task(Task("Play", 60, priority=Priority.LOW))

    plan = make_scheduler(pet).generate_plan(TODAY)

    assert [(e.task.title, e.start) for e in plan.entries] == [("Play", at(8)), ("Meds", at(10))]
    assert plan.skipped == []


def test_task_that_exactly_fills_window_is_scheduled():
    """A task ending exactly at the end of the window fits."""
    pet = Pet(name="Mochi", species="dog")
    pet.add_task(Task("Long hike", 240))

    plan = make_scheduler(pet, available_minutes=240).generate_plan(TODAY)

    assert plan.entries[0].end == at(12)
    assert plan.skipped == []


def test_task_longer_than_window_is_skipped():
    """A task that cannot fit anywhere is skipped with a clear reason."""
    pet = Pet(name="Mochi", species="dog")
    pet.add_task(Task("Long hike", 241))

    plan = make_scheduler(pet, available_minutes=240).generate_plan(TODAY)

    assert plan.entries == []
    assert plan.skipped[0].reason == "not enough free time remaining"


def test_preferred_time_before_window_starts_at_day_start():
    """A preferred time before day_start is clamped to day_start."""
    pet = Pet(name="Mochi", species="dog")
    pet.add_task(Task("Breakfast", 10, preferred_time=time(6, 0)))

    plan = make_scheduler(pet).generate_plan(TODAY)

    assert plan.entries[0].start == at(8)


def test_preferred_time_after_window_is_skipped():
    """A preferred time after the window ends is skipped with that reason."""
    pet = Pet(name="Mochi", species="dog")
    pet.add_task(Task("Evening walk", 20, preferred_time=time(18, 0)))

    plan = make_scheduler(pet).generate_plan(TODAY)

    assert plan.skipped[0].reason == "preferred time is after the owner's available time"


def test_no_available_time_skips_with_accurate_reason():
    """With a zero-minute window, tasks are skipped because there is no time at all."""
    pet = Pet(name="Mochi", species="dog")
    pet.add_task(Task("Feed", 10))

    plan = make_scheduler(pet, available_minutes=0).generate_plan(TODAY)

    assert plan.entries == []
    assert plan.skipped[0].reason == "owner has no available time"


# --- Filtering and editing --------------------------------------------------


def test_filter_tasks_by_pet_and_status():
    """filter_tasks() narrows by pet name and due/done/all status."""
    dog = Pet(name="Mochi", species="dog")
    cat = Pet(name="Tofu", species="cat")
    walk = Task("Walk", 30, frequency=Frequency.ONCE)
    feed = Task("Feed", 10)
    dog.add_task(walk)
    cat.add_task(feed)
    dog.complete_task(walk, TODAY)
    scheduler = make_scheduler(dog, cat)

    assert scheduler.filter_tasks(TODAY) == [(cat, feed)]
    assert scheduler.filter_tasks(TODAY, status="done") == [(dog, walk)]
    assert scheduler.filter_tasks(TODAY, pet_name="Mochi", status=None) == [(dog, walk)]


def test_edit_rolls_back_on_invalid_value():
    """A failed edit leaves the task unchanged."""
    task = Task("Walk", 30)
    with pytest.raises(ValueError):
        task.edit(title="Run", duration_minutes=0)
    assert (task.title, task.duration_minutes) == ("Walk", 30)


def test_remove_task_removes_exact_object_not_look_alike():
    """remove_task() uses identity, so an identical-looking task stays."""
    pet = Pet(name="Mochi", species="dog")
    first, twin = Task("Walk", 30), Task("Walk", 30)
    pet.add_task(first)
    pet.add_task(twin)

    pet.remove_task(twin)

    assert pet.get_tasks() == [first]
    assert pet.get_tasks()[0] is first
