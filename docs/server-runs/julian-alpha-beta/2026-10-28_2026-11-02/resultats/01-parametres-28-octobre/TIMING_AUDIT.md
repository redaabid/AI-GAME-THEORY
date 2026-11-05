# Timing audit after the completed run

Windows System / Kernel-Power events confirm Modern Standby during the test:
- 18:30:01 UTC: standby (idle), activity resumes around 18:59:56 UTC.
- 19:00:27 UTC: standby, exit at 19:39:55 UTC, followed by hibernation/resume events.

These intervals strongly support suspension of the PC as the explanation for the roughly 29-minute and 39-minute elapsed measurements in game 005, width8 vs depth24, thetrap, candidate vampires. Individual turn UTC timestamps were not recorded, so exact attribution of all three outliers is not established. Preserve all raw timings; do not interpret them as normal uninterrupted search duration or silently remove them.

The search checks its deadline cooperatively. The simulator records overruns but does not enforce the real server's timeout/turn-loss behavior, so game 005 is unsuitable for certifying timing or server-compliant playing strength. Replay that condition with the PC awake before judging width8. Official per-decision limit: 2 seconds, local search budget: 1.5 seconds. No replay launched by this audit.
