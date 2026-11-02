# AB2 simulator screening

**Simulator results only; real Windows server verification still required.**

Budget: 1.5 s/decision. Cap: 200 plies.

| Profile | Reference | W/D/L | Mean/max seconds | Mean depth | Repeated states | Faults |
|---|---|---|---|---:|---:|---:|
| depth24 | control | 2/2/0 | 1.440 / 1.514 | 14.0 | 478 | 0 |
| width8 | depth24 | 0/2/2 | 11.764 / 2363.948 | 10.7 | 391 | 0 |
| tactical1 | depth24 | 1/2/1 | 1.422 / 1.534 | 12.6 | 498 | 0 |
| repeat | depth24 | 0/2/2 | 1.451 / 1.528 | 12.7 | 440 | 0 |

Exploratory small sample; repetitions are full boards with actor.
Each added feature faces depth24, while depth24 faces the depth8 control.
Alerts >1.8 s: 3.
Bootstrap decisions: 0.
