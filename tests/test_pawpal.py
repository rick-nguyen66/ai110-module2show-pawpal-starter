"""Tests for PawPal+ core behavior."""

from datetime import date

from pawpal_system import Pet, Task


def test_mark_complete_changes_task_status():
    """mark_complete() records the date and the task is no longer due that day."""
    task = Task(title="Morning walk", duration_minutes=30)
    today = date(2026, 10, 17)
    assert task.last_completed is None
    assert task.is_due(today)

    task.mark_complete(today)

    assert task.last_completed == today
    assert not task.is_due(today)


def test_add_task_increases_pet_task_count():
    """add_task() grows the pet's task list by one per added task."""
    pet = Pet(name="Mochi", species="dog")
    assert len(pet.get_tasks()) == 0

    pet.add_task(Task(title="Feed breakfast", duration_minutes=10))
    assert len(pet.get_tasks()) == 1

    pet.add_task(Task(title="Evening walk", duration_minutes=20))
    assert len(pet.get_tasks()) == 2
