"""Demo script: build an owner with pets and tasks, then print today's schedule."""

from datetime import date, time

from pawpal_system import Frequency, Owner, Pet, Priority, Scheduler, Task


def main() -> None:
    owner = Owner(name="Rick", day_start=time(7, 0), available_minutes=240)

    mochi = Pet(name="Mochi", species="dog", age=3)
    luna = Pet(name="Luna", species="cat", age=5)
    pip = Pet(name="Pip", species="rabbit", age=1)
    for pet in (mochi, luna, pip):
        owner.add_pet(pet)

    mochi.add_task(Task("Morning walk", 30, Priority.HIGH, "exercise", preferred_time=time(7, 0)))
    mochi.add_task(Task("Play fetch", 45, Priority.MEDIUM, "exercise", preferred_time=time(10, 0)))
    luna.add_task(Task("Breakfast", 10, Priority.HIGH, "feeding", preferred_time=time(7, 30)))
    luna.add_task(Task("Brush fur", 15, Priority.LOW, "grooming", Frequency.WEEKLY, preferred_time=time(9, 30)))
    pip.add_task(Task("Clean hutch", 20, Priority.MEDIUM, "cleaning", preferred_time=time(8, 30)))
    pip.add_task(Task("Give meds", 5, Priority.HIGH, "medicine", Frequency.WEEKLY))

    scheduler = Scheduler(owner)
    plan = scheduler.generate_plan(date.today())
    print("Today's Schedule")
    print("=" * 40)
    print(scheduler.explain_plan(plan))


if __name__ == "__main__":
    main()
