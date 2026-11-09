---
career: "Software Engineer"
type: "interview_questions"
---

**Behavioral:**
- "Tell me about a bug that was especially hard to track down." — a
  strong answer covers: the specific debugging process (reproducing it
  reliably, narrowing down where it occurred, forming and testing
  hypotheses), not just the eventual fix — interviewers care more about
  the method than the specific bug.
- "Describe a disagreement you had with a teammate about a technical
  approach." — a strong answer covers: how the disagreement was resolved
  with evidence or a trial rather than just seniority/opinion, and what
  the actual outcome was.

**Technical:**
- "Explain the difference between a stack and a queue, and give a
  real-world use case for each." — a strong answer covers: a stack is
  last-in-first-out (e.g. undo history, call stacks); a queue is
  first-in-first-out (e.g. a print job queue, a task processing pipeline).
- "How would you design a URL shortener?" (a common system design
  warm-up) — a strong answer covers: generating a short unique key for
  each long URL (hashing or an incrementing counter encoded in base62),
  a database mapping short keys to original URLs, and a redirect
  endpoint that looks up the key and returns an HTTP redirect.
- "What's the difference between SQL and NoSQL databases, and when would
  you choose one over the other?" — a strong answer covers: SQL databases
  enforce a fixed schema and support complex relational queries/joins;
  NoSQL databases trade that structure for flexibility and easier
  horizontal scaling, which fits well when the data is less structured or
  the read/write volume is very high.
