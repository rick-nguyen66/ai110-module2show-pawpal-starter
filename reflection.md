# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.
- What classes did you include, and what responsibilities did you assign to each?
Based on the scenario and description in README.md, the core classes include:
Owner: includes name, available_minutes they are free to perform tasks (like feeding their pet or walking), preferences, and a list of their pets
Pet: name, species, age, tasks
Task: title, duration_minutes, priority, category, frequency, is_completed
Scheduler: owned by an owner and has logic like sorting task by priority, filtering, detecting conflicts, and generating a plan

**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.
The biggest change made was specifying the plan detail object. The initial skeleton only had available_minutes for owners (which can be used to identify if a task can be done that day), but no other info on the start/end time for a task. For simplicity, the the owner will have a start time they are free to start, which the planner will layout tasks sequentially, rather than finding chunks of available times during the day, i.e., it is a "duration-only" planner.
---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?
The scheduler looks at five things: the owner's available time window (day_start plus available_minutes), each task's priority, each task's preferred start time, how long each task takes, and whether the task is due today based on how often it repeats. I treated time and priority as the most important, because a busy pet owner can't do more than their free time allows, and essentials like meds and feeding should never get bumped by something optional like grooming. Preferred time and duration only break ties, so high-priority tasks get scheduled first, and any task that doesn't fit gets skipped with a reason instead of overflowing the day.

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?
 The scheduler places tasks greedily in a single pass, highest priority first. It never goes back to fill gaps. For example, if a high-priority task has a late preferred time, the schedule jumps ahead to that time. Any earlier free time is then lost, and a lower-priority task that would have fit there can get skipped. A greedy approach is simple and predictable, with skipped tasks explained with a clear reason and easy to be seen when left out. Also, an owner realistically cares more about high-priority essentials like medicine and feeding, especially if they are limited on time.
---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?
I primarily used AI to expand/flesh out the plan I first outlined in the Mermaid diagram. I also used it to review any possible logical issues in my design but made sure that it was within scope and did not conflict with my known constraints. Another important role AI played was creating the tests, however, it was after I clearly stated what the tests should cover and verifying that it tests for intended behavior.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?
At one point, the AI suggested expanding the owner field to have a list of blocks of time throughout the day. While this could be a good recommendation, this was a bit outside of the scope of the assignment. Often, I have to prevent the AI from straying away from the original intent. In terms of verifying what AI suggests, I always refer its recommendations with the original blueprint, for example, the classes and constraints in the Mermaid diagram.
---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
