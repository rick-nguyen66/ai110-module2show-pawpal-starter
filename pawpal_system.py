"""PawPal+ system classes: Owner, Pet, Task, and Scheduler."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Task:
    """A single pet care activity (walk, feeding, meds, etc.)."""

    title: str
    duration_minutes: int
    priority: str = "medium"  # "low" | "medium" | "high"
    category: str = "general"
    frequency: str = "daily"  # e.g. "daily", "weekly", "once"
    preferred_time: str = ""  # e.g. "08:00" or "morning"
    completed: bool = False

    def mark_complete(self) -> None:
        """Mark this task as completed."""
        pass

    def is_due_today(self) -> bool:
        """Return True if this task should be scheduled today."""
        pass

    def edit(self, **changes) -> None:
        """Update one or more attributes of this task."""
        pass


@dataclass
class Pet:
    """A pet and the care tasks associated with it."""

    name: str
    species: str
    age: int = 0
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a care task for this pet."""
        pass

    def remove_task(self, task: Task) -> None:
        """Remove a care task from this pet."""
        pass

    def get_tasks(self) -> list[Task]:
        """Return all tasks for this pet."""
        pass


@dataclass
class Owner:
    """A pet owner, their constraints, and their pets."""

    name: str
    available_minutes: int = 0
    preferences: list[str] = field(default_factory=list)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner."""
        pass

    def get_pets(self) -> list[Pet]:
        """Return all of this owner's pets."""
        pass

    def get_all_tasks(self) -> list[Task]:
        """Return every task across all of this owner's pets."""
        pass


@dataclass
class Scheduler:
    """Builds a daily care plan for an owner's pets."""

    owner: Owner
    tasks: list[Task] = field(default_factory=list)
    skipped_tasks: list[Task] = field(default_factory=list)

    def sort_by_priority(self) -> list[Task]:
        """Return tasks ordered from highest to lowest priority."""
        pass

    def filter_tasks(self) -> list[Task]:
        """Return only tasks that are due today and not yet completed."""
        pass

    def detect_conflicts(self) -> list[tuple]:
        """Return pairs of tasks whose scheduled times overlap."""
        pass

    def generate_plan(self) -> list[tuple]:
        """Build the daily plan as (start_time, task) pairs within available time."""
        pass

    def explain_plan(self) -> str:
        """Return a human-readable explanation of the generated plan."""
        pass
