# Code review: P-E power simulation (coder-critic, round 1, MEDIUM-HIGH), 2026-09-30

**Score: 68/100 (FAIL).**

- **Clean:** no leakage. Design fidelity is mostly faithful (G̃/G indexing, injection from G, ℓ = 0..3 headline).
- **Over-rejection:** this is probably genuine, but partly a design artifact (see below).

## HIGH
| # | Issue | Location | Fix |
|---|---|---|---|
| H1 | The treated share of the pool is about 60% (J_T 40 of 65 E1P common-support clusters), against roughly 20–25% in reality. J_C and the cell-rule drops in Mid/High are artifacts. | 02:36-61, _pf:43-57 | Widen the pool (trim per variable, or on controls only) or cap J_T at a realistic ratio. Report real vs memo J_C. |
| H2 | 200 draws were used, below the protocol's 500–1,000. | — | Re-run with ≥500 draws before any gate. |
| H3 | Size-adjusted critical value is an oracle (q95 of \|z\| over feasible draws), so the MDEs are optimistic. | 03:34-39 | Don't use these MDEs for gates until WCR/RI runs inside the loop. |
| H4 | Analytic SEs are used, not the memo's primary inference (§9.2 step 4). | 02:183-184 | Simulate the actual inference. |

## MED
| Issue | Location | Fix |
|---|---|---|
| Not-yet-treated switchers aren't counted as controls at t < G̃_j. | _pf:98-102 | Count them as eligible controls. |
| Outcome is asinh of raw counts, not the memo's index/rates; "log points" is loose. | 02:97, 01:268 | Document the deviation. |
| CS for E3 is unconditional with no FE/cell structure, and `aggte` group-size weights differ from equal per-ℓ weights. | _pf:150-162 | Align with the E1 specification. |
| Labels are inconsistent (">grid" vs "--"). | 03:153-160 | Use one label. |
| Checkpoint key misses CFG/SC/functions/panel, and seed streams shift if scenarios change. | 02:235 | Key on a hash of those inputs; use per-scenario seed offsets. |

## LOW
- The CI drops NA replicates.
- `on.exit` at top level doesn't run on error.
- `fill=0` silently turns missing cells into zeros.
- `cat` is used instead of `message`.

## Diagnostics before accepting the size result
Run size at δ = 0 under each of these:
- with `bin^fy` removed
- with the cell rule off
- against a TWFE benchmark
- with a cluster-permutation RI

Then compare size by J_C.
