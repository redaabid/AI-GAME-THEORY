# AB2 paired simulator tournament

**Exploratory simulator evidence; real-server confirmation remains required.**

Budget: 1.5 s/decision; cap: 200 plies; all species and first-player roles.
Primary criterion: win=1, draw=0.5. Secondary screening tie-break: fewer repeated states.
Equal scores remain inconclusive; a tie-break is not a statistical result.

## Screening

| Agent | Games | W/D/L | Score | Mean/max s | Faults |
|---|---:|---|---:|---|---:|
| travel | 32 | 1/31/0 | 0.516 | 0.017 / 0.021 | 0 |
| guidance | 32 | 0/32/0 | 0.500 | 0.017 / 0.020 | 0 |
| tactical1 | 32 | 0/32/0 | 0.500 | 0.017 / 0.020 | 0 |
| width7 | 32 | 0/32/0 | 0.500 | 0.017 / 0.020 | 0 |
| control | 32 | 0/31/1 | 0.484 | 0.017 / 0.021 | 0 |

## Fresh-map confirmation

| Agent | Games | W/D/L | Score | Mean/max s | Faults |
|---|---:|---|---:|---|---:|
| travel | 16 | 4/12/0 | 0.625 | 0.018 / 0.020 | 0 |
| guidance | 16 | 0/12/4 | 0.375 | 0.018 / 0.021 | 0 |

Provisional finalists: travel, guidance.
Selected after screening only; no weights are adjusted on confirmation maps.

