---
career: "ML Engineer"
type: "interview_questions"
---

**Behavioral:**
- "Tell me about a time a model performed well in testing but poorly in
  production." — a strong answer covers: how the gap was diagnosed (data
  drift, a training/serving mismatch, a bug in the feature pipeline), and
  what monitoring or process change was put in place to catch it earlier
  next time.
- "Describe a time you had to make a tradeoff between model accuracy and
  system performance (latency/cost)." — a strong answer covers: the
  specific numbers involved (how much accuracy was traded for how much
  speed/cost improvement), and why that tradeoff was the right call for
  the actual use case.

**Technical:**
- "How would you design a system to retrain a model automatically as new
  data arrives?" — a strong answer covers: a scheduled or trigger-based
  retraining pipeline, automated validation against a held-out set before
  deploying the new model, and a rollback plan if the new model performs
  worse.
- "What's the difference between batch inference and real-time inference,
  and when would you use each?" — a strong answer covers: batch inference
  processes many inputs on a schedule (cheaper, higher latency tolerance);
  real-time inference responds to individual requests as they arrive
  (needed when a user is waiting for the result, like a live
  recommendation).
- "How do you monitor a model in production?" — a strong answer covers:
  tracking input data distribution for drift, tracking prediction
  distribution, and tracking actual outcome-based metrics when ground
  truth eventually becomes available, not just assuming the model still
  works because it hasn't crashed.
