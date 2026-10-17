"""PawPal+ system classes: Owner, Pet, Task, Scheduler, and plan result types."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime, time, timedelta
from enum import Enum, IntEnum
from typing import Literal


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
    """One occurrence of a care task (walk, feeding, meds, etc.).

    Each Task is a single occurrence with its own due_date. Completing a DAILY
    or WEEKLY task returns a fresh Task for the next occurrence; the completed
    one stays on the pet as history.
    """

    title: str
    duration_minutes: int
    priority: Priority = Priority.MEDIUM
    category: str = "general"
    frequency: Frequency = Frequency.DAILY
    preferred_time: time | None = None  # earliest desired start, e.g. time(8, 0)
    due_date: date | None = None  # None = due from today onward
    last_completed: date | None = None  # set when this occurrence is completed

    def __post_init__(self) -> None:
        """Validate fields: duration must be positive; coerce priority/frequency to enums."""
        if not self.title or not self.title.strip():
            raise ValueError("Task title must not be empty")
        if self.duration_minutes <= 0:
            raise ValueError("Task duration_minutes must be positive")
        if isinstance(self.priority, str):
            self.priority = Priority[self.priority.upper()]
        else:
            self.priority = Priority(self.priority)
        self.frequency = Frequency(self.frequency.lower() if isinstance(self.frequency, str) else self.frequency)

    def mark_complete(self, on: date) -> Task | None:
        """Mark this occurrence completed on the given date.

        Returns the next occurrence for DAILY (due on + 1 day) and WEEKLY
        (due on + 7 days) tasks, or None for ONCE tasks. The next date is
        counted from the completion date so late completions don't pile up.
        Raises ValueError if this occurrence is already complete.
        """
        if self.is_complete:
            raise ValueError(f"'{self.title}' was already completed on {self.last_completed.isoformat()}")
        self.last_completed = on
        if self.frequency is Frequency.DAILY:
            return replace(self, due_date=on + timedelta(days=1), last_completed=None)
        if self.frequency is Frequency.WEEKLY:
            return replace(self, due_date=on + timedelta(days=7), last_completed=None)
        return None

    @property
    def is_complete(self) -> bool:
        """True once this occurrence has been completed."""
        return self.last_completed is not None

    def is_due(self, on: date) -> bool:
        """Return True if this occurrence is incomplete and due (or overdue) on the given date."""
        if self.is_complete:
            return False
        return self.due_date is None or self.due_date <= on

    def next_due_date(self, on: date) -> date | None:
        """Return the first date on or after `on` when this occurrence is due (None if completed)."""
        if self.is_complete:
            return None
        if self.due_date is None:
            return on
        return max(on, self.due_date)

    def edit(self, **changes) -> None:
        """Update one or more attributes of this task, re-running validation."""
        unknown = set(changes) - set(self.__dataclass_fields__)
        if unknown:
            raise AttributeError(f"Unknown Task field(s): {', '.join(sorted(unknown))}")
        previous = {name: getattr(self, name) for name in changes}
        for name, value in changes.items():
            setattr(self, name, value)
        try:
            self.__post_init__()
        except (ValueError, KeyError, TypeError):
            for name, value in previous.items():
                setattr(self, name, value)
            raise


@dataclass
class Pet:
    """A pet and the care tasks that belong to it."""

    name: str
    species: str
    age: int = 0
    tasks: list[Task] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate fields: age must be non-negative."""
        if self.age < 0:
            raise ValueError("Pet age must be non-negative")

    def add_task(self, task: Task) -> None:
        """Add a care task for this pet."""
        self.tasks.append(task)

    def remove_task(self, task: Task) -> None:
        """Remove this exact task object from this pet."""
        self.tasks.remove(task)

    def get_tasks(self) -> list[Task]:
        """Return all tasks for this pet."""
        return list(self.tasks)

    def complete_task(self, task: Task, on: date) -> Task | None:
        """Mark one of this pet's tasks complete and add its next occurrence, if any."""
        if not any(t is task for t in self.tasks):
            raise ValueError(f"'{task.title}' is not one of {self.name}'s tasks")
        next_task = task.mark_complete(on)
        if next_task is not None:
            self.add_task(next_task)
        return next_task


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
        self.pets.append(pet)

    def get_pets(self) -> list[Pet]:
        """Return all of this owner's pets."""
        return list(self.pets)

    def get_all_tasks(self) -> list[tuple[Pet, Task]]:
        """Return every (pet, task) pair across all of this owner's pets."""
        return [(pet, task) for pet in self.pets for task in pet.tasks]


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
    conflicts: list[Conflict] = field(default_factory=list)  # overlapping *requested* times


@dataclass
class Scheduler:
    """Builds a daily care plan for one owner.

    Tasks are always read from the owner's pets at call time, so the scheduler
    holds no task state of its own and each generate_plan() call is independent.

    Policy: the owner does one task at a time (no parallel care across pets).
    Due tasks are ordered by priority (high first), then preferred_time
    (earliest first, None last), then shorter duration. Each task goes into the
    earliest free gap in the owner's window that starts no earlier than its
    preferred_time and is long enough; tasks that fit nowhere are skipped.
    """

    owner: Owner

    def filter_tasks(
        self,
        on: date,
        pet_name: str | None = None,
        status: Literal["due", "done"] | None = "due",
    ) -> list[tuple[Pet, Task]]:
        """Return (pet, task) pairs matching the given pet and status on a date.

        status="due" keeps incomplete tasks due (or overdue) on `on`, "done"
        keeps completed tasks, and None keeps every task.
        """
        items = self.owner.get_all_tasks()
        if pet_name is not None:
            items = [(pet, task) for pet, task in items if pet.name == pet_name]
        if status == "due":
            items = [(pet, task) for pet, task in items if task.is_due(on)]
        elif status == "done":
            items = [(pet, task) for pet, task in items if task.is_complete]
        return items

    def sort_by_priority(self, items: list[tuple[Pet, Task]]) -> list[tuple[Pet, Task]]:
        """Return items ordered by priority, then preferred_time, then duration."""

        def key(item: tuple[Pet, Task]) -> tuple:
            task = item[1]
            no_time = task.preferred_time is None
            return (-task.priority, no_time, task.preferred_time or time.min, task.duration_minutes)

        return sorted(items, key=key)  # stable, so ties keep pet/task insertion order

    def sort_by_time(self, items: list[tuple[Pet, Task]]) -> list[tuple[Pet, Task]]:
        """Return items ordered by preferred_time (earliest first, None last)."""
        return sorted(items, key=lambda item: (item[1].preferred_time is None, item[1].preferred_time or time.min))

    def find_requested_conflicts(self, items: list[tuple[Pet, Task]], on: date) -> list[Conflict]:
        """Return pairs of tasks whose preferred_time slots overlap on the given date."""
        requested = []
        for pet, task in items:
            if task.preferred_time is None:
                continue
            start = datetime.combine(on, task.preferred_time)
            requested.append(PlanEntry(pet, task, start, start + timedelta(minutes=task.duration_minutes)))
        return self.detect_conflicts(requested)

    def generate_plan(self, on: date) -> Plan:
        """Build the plan for the given date within the owner's available time."""
        plan = Plan(day=on)
        day_start = datetime.combine(on, self.owner.day_start)
        day_end = day_start + timedelta(minutes=self.owner.available_minutes)
        free: list[tuple[datetime, datetime]] = [(day_start, day_end)] if day_end > day_start else []

        due = self.filter_tasks(on)
        plan.conflicts = self.find_requested_conflicts(due, on)

        for pet, task in self.sort_by_priority(due):
            earliest = day_start
            if task.preferred_time is not None:
                earliest = max(earliest, datetime.combine(on, task.preferred_time))
            duration = timedelta(minutes=task.duration_minutes)

            for i, (gap_start, gap_end) in enumerate(free):
                start = max(gap_start, earliest)
                end = start + duration
                if end <= gap_end:
                    pieces = [(gap_start, start), (end, gap_end)]
                    free[i:i + 1] = [(s, e) for s, e in pieces if e > s]
                    plan.entries.append(PlanEntry(pet, task, start, end))
                    break
            else:
                if day_end <= day_start:
                    reason = "owner has no available time"
                elif earliest >= day_end:
                    reason = "preferred time is after the owner's available time"
                else:
                    reason = "not enough free time remaining"
                plan.skipped.append(SkippedTask(pet, task, reason))

        plan.entries.sort(key=lambda e: e.start)
        return plan

    def detect_conflicts(self, entries: list[PlanEntry]) -> list[Conflict]:
        """Return pairs of entries whose [start, end) intervals overlap."""
        conflicts: list[Conflict] = []
        ordered = sorted(entries, key=lambda e: e.start)
        for i, first in enumerate(ordered):
            for second in ordered[i + 1:]:
                if second.start >= first.end:
                    break  # sorted by start, so no later entry can overlap `first`
                conflicts.append(
                    Conflict(
                        first,
                        second,
                        f"'{first.task.title}' ({first.pet.name}) overlaps "
                        f"'{second.task.title}' ({second.pet.name})",
                    )
                )
        return conflicts

    def explain_plan(self, plan: Plan) -> str:
        """Return a human-readable explanation of the plan and any skipped tasks."""
        lines = [f"Plan for {self.owner.name} on {plan.day.isoformat()}:"]
        if not plan.entries:
            lines.append("  No tasks scheduled.")
        for entry in plan.entries:
            task = entry.task
            why = f"{task.priority.name.lower()} priority"
            if task.preferred_time is not None:
                why += f", preferred after {task.preferred_time.strftime('%H:%M')}"
            lines.append(
                f"  {entry.start.strftime('%H:%M')}-{entry.end.strftime('%H:%M')}  "
                f"{entry.pet.name}: {task.title} ({task.duration_minutes} min; {why})"
            )

        total = sum(e.task.duration_minutes for e in plan.entries)
        lines.append(f"Total scheduled: {total} of {self.owner.available_minutes} available minutes.")

        if plan.skipped:
            lines.append("Skipped:")
            for skipped in plan.skipped:
                lines.append(f"  {skipped.pet.name}: {skipped.task.title} - {skipped.reason}")

        if plan.conflicts:
            lines.append("Requested-time conflicts (lower-priority task was moved):")
            for conflict in plan.conflicts:
                lines.append(f"  {conflict.reason}")
        return "\n".join(lines)
