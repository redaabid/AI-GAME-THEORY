# AB2 simulator screening

**Simulator results only; real Windows server verification still required.**

Budget: 1.5 s/decision. Cap: 200 plies.

| Profile | Reference | W/D/L | Mean/max seconds | Mean depth | Repeated states | Faults |
|---|---|---|---|---:|---:|---:|
| tactical1 | control | 2/0/2 | 1.429 / 1.519 | 15.3 | 553 | 0 |
| width7 | control | 2/0/2 | 1.421 / 1.536 | 15.2 | 571 | 0 |
| guidance | control | 2/0/2 | 1.477 / 1.531 | 13.7 | 425 | 0 |
| travel | control | 2/0/2 | 1.452 / 1.500 | 11.5 | 565 | 0 |

Exploratory small sample; repetitions are full boards with actor.
Reference specifications and exploratory limitations are recorded in protocol.json.
Alerts >1.8 s: 0.
Bootstrap decisions: 0.
