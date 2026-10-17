"""PawPal+ system classes: Owner, Pet, Task, Scheduler, and plan result types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
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
        if not self.title or not self.title.strip():
            raise ValueError("Task title must not be empty")
        if self.duration_minutes <= 0:
            raise ValueError("Task duration_minutes must be positive")
        if isinstance(self.priority, str):
            self.priority = Priority[self.priority.upper()]
        else:
            self.priority = Priority(self.priority)
        self.frequency = Frequency(self.frequency.lower() if isinstance(self.frequency, str) else self.frequency)

    def mark_complete(self, on: date) -> None:
        """Record that this task was completed on the given date."""
        self.last_completed = on

    def is_due(self, on: date) -> bool:
        """Return True if this task needs doing on the given date.

        ONCE: due until completed. DAILY: due unless completed on `on`.
        WEEKLY: due if never completed or last completed 7+ days before `on`.
        """
        if self.last_completed is None:
            return True
        if self.frequency is Frequency.ONCE:
            return False
        if self.frequency is Frequency.DAILY:
            return self.last_completed < on
        return (on - self.last_completed).days >= 7

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
        except (ValueError, KeyError):
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
        return [(pet, task) for pet, task in self.owner.get_all_tasks() if task.is_due(on)]

    def sort_by_priority(self, items: list[tuple[Pet, Task]]) -> list[tuple[Pet, Task]]:
        """Return items ordered by priority, then preferred_time, then duration."""

        def key(item: tuple[Pet, Task]) -> tuple:
            task = item[1]
            no_time = task.preferred_time is None
            return (-task.priority, no_time, task.preferred_time or time.min, task.duration_minutes)

        return sorted(items, key=key)  # stable, so ties keep pet/task insertion order

    def generate_plan(self, on: date) -> Plan:
        """Build the plan for the given date within the owner's available time."""
        plan = Plan(day=on)
        day_start = datetime.combine(on, self.owner.day_start)
        day_end = day_start + timedelta(minutes=self.owner.available_minutes)
        cursor = day_start

        for pet, task in self.sort_by_priority(self.filter_tasks(on)):
            start = cursor
            if task.preferred_time is not None:
                start = max(start, datetime.combine(on, task.preferred_time))
            end = start + timedelta(minutes=task.duration_minutes)
            if end > day_end:
                if start >= day_end:
                    reason = "preferred time is after the owner's available time"
                else:
                    reason = "not enough time remaining"
                plan.skipped.append(SkippedTask(pet, task, reason))
                continue
            plan.entries.append(PlanEntry(pet, task, start, end))
            cursor = end

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

        conflicts = self.detect_conflicts(plan.entries)
        if conflicts:
            lines.append("Conflicts:")
            for conflict in conflicts:
                lines.append(f"  {conflict.reason}")
        return "\n".join(lines)
