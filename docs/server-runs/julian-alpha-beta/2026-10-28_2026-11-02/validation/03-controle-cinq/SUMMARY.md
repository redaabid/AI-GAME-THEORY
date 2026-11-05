# AB2 simulator screening

**Functional smoke check only; do not rank playing strength.**

Budget: 0.02 s/decision. Cap: 12 plies.

| Profile | Reference | W/D/L | Mean/max seconds | Mean depth | Repeated states | Faults |
|---|---|---|---|---:|---:|---:|
| depth24 | control | 1/4/1 | 0.018 / 0.021 | 7.3 | 0 | 0 |
| width8 | depth24 | 1/4/1 | 0.018 / 0.020 | 6.8 | 0 | 0 |
| tactical1 | depth24 | 1/4/1 | 0.018 / 0.020 | 5.6 | 0 | 0 |
| repeat | depth24 | 1/4/1 | 0.018 / 0.020 | 6.8 | 0 | 0 |

Exploratory small sample; repetitions are full boards with actor.
Each added feature faces depth24, while depth24 faces the depth8 control.
Alerts >1.8 s: 0.
Bootstrap decisions: 0.
