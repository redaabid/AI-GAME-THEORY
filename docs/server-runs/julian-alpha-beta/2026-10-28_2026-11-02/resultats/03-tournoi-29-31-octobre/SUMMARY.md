# AB2 paired simulator tournament

**Exploratory simulator evidence; real-server confirmation remains required.**

Budget: 1.5 s/decision; cap: 200 plies; all species and first-player roles.
Primary criterion: win=1, draw=0.5. Secondary screening tie-break: fewer repeated states.
Equal scores remain inconclusive; a tie-break is not a statistical result.

## Screening

| Agent | Games | W/D/L | Score | Mean/max s | Faults |
|---|---:|---|---:|---|---:|
| width7 | 32 | 8/16/8 | 0.500 | 1.422 / 1.569 | 0 |
| guidance | 32 | 8/16/8 | 0.500 | 1.435 / 1.565 | 0 |
| control | 32 | 8/16/8 | 0.500 | 1.405 / 1.577 | 0 |
| tactical1 | 32 | 8/16/8 | 0.500 | 1.424 / 1.560 | 0 |
| travel | 32 | 8/16/8 | 0.500 | 1.424 / 1.567 | 0 |

## Fresh-map confirmation

| Agent | Games | W/D/L | Score | Mean/max s | Faults |
|---|---:|---|---:|---|---:|
| width7 | 16 | 6/8/2 | 0.625 | 1.444 / 1.566 | 0 |
| guidance | 16 | 2/8/6 | 0.375 | 1.451 / 1.573 | 0 |

Provisional finalists: width7, guidance.
Selected after screening only; no weights are adjusted on confirmation maps.

