"""PawPal+ system classes: Owner, Pet, Task, Scheduler, and plan result types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
from enum import Enum, IntEnum


class Priority(IntEnum):
    """Task priority; higher value is scheduled first."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3


class Frequency(str, Enum):
    """How often a task recurs."""

    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"


@dataclass(eq=False)  # identity equality so remove_task() never removes a look-alike task
class Task:
    """A care task definition (walk, feeding, meds, etc.).

    Completion is tracked as a date rather than a bool so recurring tasks
    become due again on later days.
    """

    title: str
    duration_minutes: int
    priority: Priority = Priority.MEDIUM
    category: str = "general"
    frequency: Frequency = Frequency.DAILY
    preferred_time: time | None = None  # earliest desired start, e.g. time(8, 0)
    last_completed: date | None = None

    def __post_init__(self) -> None:
        """Validate fields: duration must be positive; coerce priority/frequency to enums."""
        pass

    def mark_complete(self, on: date) -> None:
        """Record that this task was completed on the given date."""
        pass

    def is_due(self, on: date) -> bool:
        """Return True if this task needs doing on the given date.

        ONCE: due until completed. DAILY: due unless completed on `on`.
        WEEKLY: due if never completed or last completed 7+ days before `on`.
        """
        pass

    def edit(self, **changes) -> None:
        """Update one or more attributes of this task, re-running validation."""
        pass


@dataclass
class Pet:
    """A pet and the care tasks that belong to it."""

    name: str
    species: str
    age: int = 0
    tasks: list[Task] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate fields: age must be non-negative."""
        pass

    def add_task(self, task: Task) -> None:
        """Add a care task for this pet."""
        pass

    def remove_task(self, task: Task) -> None:
        """Remove this exact task object from this pet."""
        pass

    def get_tasks(self) -> list[Task]:
        """Return all tasks for this pet."""
        pass


@dataclass
class Owner:
    """A pet owner, their daily time budget, and their pets."""

    name: str
    day_start: time = time(8, 0)  # when the owner's free time begins
    available_minutes: int = 0  # length of free time starting at day_start
    preferences: list[str] = field(default_factory=list)  # free-form notes; not yet used by Scheduler
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner."""
        pass

    def get_pets(self) -> list[Pet]:
        """Return all of this owner's pets."""
        pass

    def get_all_tasks(self) -> list[tuple[Pet, Task]]:
        """Return every (pet, task) pair across all of this owner's pets."""
        pass


@dataclass
class PlanEntry:
    """One scheduled task in a generated plan."""

    pet: Pet
    task: Task
    start: datetime
    end: datetime


@dataclass
class SkippedTask:
    """A due task that could not be scheduled, and why."""

    pet: Pet
    task: Task
    reason: str  # e.g. "not enough time remaining"


@dataclass
class Conflict:
    """Two plan entries whose time intervals overlap."""

    first: PlanEntry
    second: PlanEntry
    reason: str


@dataclass
class Plan:
    """The result of one planning run for one date."""

    day: date
    entries: list[PlanEntry] = field(default_factory=list)
    skipped: list[SkippedTask] = field(default_factory=list)


@dataclass
class Scheduler:
    """Builds a daily care plan for one owner.

    Tasks are always read from the owner's pets at call time, so the scheduler
    holds no task state of its own and each generate_plan() call is independent.

    Policy: the owner does one task at a time (no parallel care across pets).
    Due tasks are ordered by priority (high first), then preferred_time
    (earliest first, None last), then shorter duration. Tasks are placed
    back-to-back from day_start, never before their preferred_time; a task
    that would end past the owner's available time is skipped.
    """

    owner: Owner

    def filter_tasks(self, on: date) -> list[tuple[Pet, Task]]:
        """Return (pet, task) pairs that are due on the given date."""
        pass

    def sort_by_priority(self, items: list[tuple[Pet, Task]]) -> list[tuple[Pet, Task]]:
        """Return items ordered by priority, then preferred_time, then duration."""
        pass

    def generate_plan(self, on: date) -> Plan:
        """Build the plan for the given date within the owner's available time."""
        pass

    def detect_conflicts(self, entries: list[PlanEntry]) -> list[Conflict]:
        """Return pairs of entries whose [start, end) intervals overlap."""
        pass

    def explain_plan(self, plan: Plan) -> str:
        """Return a human-readable explanation of the plan and any skipped tasks."""
        pass
