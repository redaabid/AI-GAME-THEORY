# AB2 simulator screening

**Functional smoke check only; do not rank playing strength.**

Budget: 0.02 s/decision. Cap: 12 plies.

| Profile | Reference | W/D/L | Mean/max seconds | Mean depth | Repeated states | Faults |
|---|---|---|---|---:|---:|---:|
| tactical1 | control | 1/2/1 | 0.018 / 0.020 | 5.5 | 0 | 0 |
| width7 | control | 1/2/1 | 0.018 / 0.020 | 7.0 | 0 | 0 |
| guidance | control | 1/2/1 | 0.018 / 0.020 | 6.8 | 0 | 0 |
| travel | control | 1/2/1 | 0.018 / 0.020 | 6.0 | 0 | 0 |

Exploratory small sample; repetitions are full boards with actor.
Reference specifications and exploratory limitations are recorded in protocol.json.
Alerts >1.8 s: 0.
Bootstrap decisions: 0.
