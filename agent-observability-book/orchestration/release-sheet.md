# Release sheet (Chapter 19)

Fill this in before the canary starts. Update the day rows at
each review. A date is a time to look at the evidence, never a
reason to expand on its own, and neither is a test that found
no difference.

| | Agent and version |
| --- | --- |
| **Change** | What changed: prompt, pack, model, tools, policy |
| **Assignment** | Share of traffic, how it's assigned, which tenants |
| **Exposure cap** | The most traffic and the highest-risk actions allowed |
| **Decision measure** | One customer outcome, measured the same way for both versions, and its window |
| **Monitors** | Rates compared on receipts, with their alert threshold and minimum sample |
| **Tolerance** | The largest drop in the decision measure you accept, and who agreed it |
| **Serious-harm stop** | The event that rolls back at once, at any sample |
| **Roll back if** | A monitor alerts, or the outcome's whole interval is below the tolerance |
| **Extend if** | Too little evidence, outcomes still maturing, or the interval too wide. Next review date |
| **Expand if** | The interval's low end clears the tolerance and no stop fired; next exposure step |
| **After expanding** | Late measures (such as 30-day reversals) that can still roll back |
| **Owners** | Release, rollback, eval follow-up |
| **Day 1** | |
| **Day 2** | |
| **Day 3** | |
