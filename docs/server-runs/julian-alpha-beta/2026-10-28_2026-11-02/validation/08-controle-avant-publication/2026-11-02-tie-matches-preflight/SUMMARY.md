# AB2 simulator screening

**Functional smoke check only; do not rank playing strength.**

Budget: 0.02 s/decision. Cap: 12 plies.

| Profile | Reference | W/D/L | Mean/max seconds | Mean depth | Repeated states | Faults |
|---|---|---|---|---:|---:|---:|
| tie_vs_reference | control | 3/4/1 | 0.019 / 0.020 | 5.2 | 0 | 0 |
| tie_vs_width7 | width7 | 2/4/2 | 0.019 / 0.020 | 4.8 | 0 | 0 |

Exploratory small sample; repetitions are full boards with actor.
Reference specifications and exploratory limitations are recorded in protocol.json.
Alerts >1.8 s: 0.
Bootstrap decisions: 0.
