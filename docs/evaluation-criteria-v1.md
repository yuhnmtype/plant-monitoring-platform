# Evaluation criteria v1

Status: **FROZEN** by the git tag `eval-criteria-v1`. This file is never edited after the tag (section 11).
Date drafted: 2026-11-06. All data in this project is simulated. Nothing here claims real industrial experience.

## 0. Parameters confirmed by Huy for the freeze

These values were proposals until the freeze and are fixed by the tag.

| ID | Parameter | Value | Why |
|---|---|---|---|
| P1 | Simulated length and chronological split | 18 months of data: train 12 months, 7-day gap, validation 3 months, 7-day gap, test 3 months | Train covers one full annual cycle if annual seasonality is simulated; measured with the run start 2025-01-01 and 7-day gaps: train 365 days, validation 90 days, test 91 days |
| P2 | Minimum incidents per class in validation and test; maximum share of anomalous time per split | 5 per class; 10% | 7 classes x 5 = 35 incidents per split; the share cap keeps the data from being mostly anomalous |
| P3 | False-alarm budget B for threshold selection | 1 false alarm per day | One alarm a day is a plausible operator limit; it is a proposal, not a measured fact |
| P4 | Secondary metric D1: fault-versus-attack labelling accuracy among detected incidents | Included | Without it the README cannot claim the system tells faults from attacks |
| P5 | Seeds | Primary 42; robustness repeats 43, 44, 45, 46 | Fixed here so nobody picks seeds after seeing results |

Sampling interval is fixed in the M1 spec. For scale only: at 15-minute sampling, the measured run from 2025-01-01 stores 52,416 samples per sensor (546 days x 96: train 35,040, validation 8,640, test 8,736). The two 7-day gaps cover 1,344 sample times (14 days x 96) that are not stored.

P2-P5 and the optional regime/context channel decision were first confirmed by Huy on 2026-11-06. P1 was changed on 2026-11-08 (two 7-day gaps between the splits). Huy confirmed P1-P5 as written above before the freeze; the freeze date is the date of the git tag `eval-criteria-v1`.

## 1. Data and splits (simulator)

1. One simulated run per profile and seed, split by time as in P1. No shuffling anywhere. Gaps between splits hold no data (section 2).
2. Before any detector runs, the simulator config fixes the incident schedule per split: class, start, end. It must satisfy P2. The simulator validates this automatically and fails otherwise. Arithmetic check of P2 with the proposed values and the measured split lengths: 10% is 216 hours of the 90-day validation split and about 218 hours of the 91-day test split, so 35 incidents must average at most about 6 hours each.
3. Profile 1 has 7 incident classes (from the brief): sensor drift, stuck sensor, weak pump, valve fault (physical faults); manipulated readings, manipulated commands, replayed data (attacks).
4. If P2 turns out to be infeasible at M1, the fix (a longer run or fewer classes) is made and recorded before the tag is created, not after.
5. The schedule keeps at least 24 hours between incidents (min_gap_hours in the profile), so that one alarm, which merges alerts at most G = 3 intervals apart, cannot span two incidents, and at least 48 hours between any incident and a split boundary. The simulator validates both. The training split holds no incidents. A larger boundary margin may be chosen before any detector runs and is then recorded in the deviations log; it must not exceed the gap (section 2).
6. The injection parameters of every incident class (magnitude, shape, affected sensor or relation) are fixed in the M3 spec and committed before any detector runs on validation or test data. They are not changed after a result has been seen; a change is a labelled deviation and the earlier results stay.

## 2. Leakage guards

- Between consecutive splits a gap is removed that is at least as long as the longest feature look-back window. Features for a timestamp are computed from data of its own split only; a window never reaches into another split. The longest feature look-back must not exceed the incident-free margin of section 1, item 5 (48 hours unless raised before any detector runs), so that no incident falls in a window that is only partly filled, and the margin must not exceed the gap. The profile sets the gap (split_gap_days, 7 for profile 1); it acts as an embargo between splits.
- No incident may cross a split boundary.
- Detectors never read the incident-label table. Labels are read only by the evaluation code.
- Normalisation constants, baseline parameters and model weights are estimated on the training split only.

## 3. Systems under evaluation

Names and families are fixed now; exact hyperparameter spaces are written in the M3 and M4 specs before they are run on validation.

- **R0, naive reference:** a fixed alert rule from the profile's nominal normal ranges (value outside range, or outside range for the current regime if the profile defines regimes).
- **B1, statistical baseline:** a per-sensor rolling statistic with a control-chart style limit (the exact form is fixed in the M3 spec).
- **L1, one ML method:** chosen at the start of M4 and recorded in an ADR before it touches validation data.
- On simulator data L1 is trained on the training split only, without labels (unsupervised or semi-supervised), because the training split holds no incidents and detectors never read the label table.

A learned method must beat R0 and B1 under section 7 before the README may call it an improvement.

## 4. Threshold selection and test discipline

1. Thresholds and hyperparameters are chosen on validation only.
2. Rule: choose the threshold with the highest validation incident recall subject to validation false alarms per day <= B. Ties go to the larger threshold. If no threshold meets B, take the one with the lowest false alarms per day and flag it in the results.
3. Every configuration evaluated on validation is logged in a committed file, so the amount of tuning is visible.
4. After thresholds are frozen, the test split is evaluated once per frozen configuration. A rerun is allowed only for a documented bug; the buggy and the corrected result are both kept and labelled.

## 5. Event definitions

- A detector outputs a score per timestamp; the threshold turns it into per-timestamp alerts.
- A detector may leave its score undefined until its look-back window is full. Such timestamps raise no alert and still count in the split duration.
- Consecutive alert timestamps separated by at most G = 3 sampling intervals merge into one **alarm** with a start and an end.
- An **incident** has start s, end e and a class, taken from the label table.
- An alarm **matches** an incident if their time intervals overlap.
- An incident is **detected** if at least one alarm matches it. Several alarms on one incident count as one detection; extra alarms inside an incident are not false alarms.
- **Detection delay** = max(0, alarm start minus s), using the first matching alarm. It is defined only for detected incidents.
- A **false alarm** is an alarm that matches no incident.
- **False alarms per day** = false alarms divided by the duration of the whole split in days (incident time included in the denominator).

## 6. Metrics

- **Primary:** incident recall at the frozen operating point (detected incidents / all incidents), overall and per class, always with counts.
- **Secondary:** median and 90th-percentile delay over detected incidents plus the number undetected; false alarms per day on test; event precision (matched alarms / all alarms); point-level precision, recall and F1 per timestamp.
- **Sensitivity to the budget:** recall also at false-alarm budgets of 0.25, 0.5 and 2 per day besides B. Thresholds are chosen on validation by the rule of section 4, each budget is a frozen configuration evaluated once on test, on the primary seed only. These results are descriptive and are never used for the word "beats".
- **D1 (if P4 is accepted):** among detected incidents, the share where the diagnosed type (fault or attack) equals the true type. It is reported with its 95% interval (section 7), the confusion matrix, and the accuracy of a baseline that always names the type that is more frequent among the detected incidents. The README may claim fault-versus-attack separation only if the lower end of the D1 interval is above that baseline accuracy. If no diagnosing component exists by the end of M4, D1 is reported as "not evaluated" and the README must not claim fault-versus-attack separation.

## 7. Uncertainty and the word "beats"

- 95% confidence intervals come from bootstrap resampling of incidents (at least 1,000 resamples, fixed seed).
- Detector X **beats** detector Y only if X's primary recall is higher, the 95% interval of the paired difference excludes zero, and X's test false alarms per day do not exceed the larger of Y's test false alarms per day and the budget B (P3).
- A recall gain with test false alarms above that limit is reported as a trade-off. No evidence of a difference is reported as exactly that.
- The decision uses the primary seed. The four repeat seeds (fresh simulated datasets, thresholds recalibrated on each validation split) are reported as mean and standard deviation for robustness and never change the verdict.

## 8. Public benchmark protocol (BATADAL)

Facts and open points are in `docs/benchmarks/batadal-check.md`.

1. Files come from the official URLs by script and are never committed.
2. Fit or baseline estimation: `BATADAL_dataset03.csv` (normal operation only).
3. Thresholds and hyperparameters: `BATADAL_dataset04.csv`, using its published attack list. Labels there are approximate, and this is stated in the results.
4. If a method is supervised, dataset 04 is split chronologically, the earlier part for training and the later part for thresholds. The split point is recorded before any result is seen. Features use data of one file only and, after such a split, of one part only; a score stays undefined until its window is full (section 5).
5. Test: the BATADAL test file, labelled from the official test attack list. The transcription is done once, checked a second time, and committed in its own commit before the first BATADAL test evaluation. If a trustworthy label source cannot be established, the test part is dropped and the README says so.
6. Same event definitions as section 5, at hourly resolution, same budget B.
7. BATADAL has an attack flag only, so D1 does not apply. Results are reported separately and never pooled with simulator results.
8. The competition's official score may be reported only if its formula is taken from the paper or rules document; otherwise it is omitted.

## 9. Generality criterion (profile 2)

- Success: adding profile 2 changes zero lines under the core paths.
- Core paths: `src/plantmon/` and `db/`. Profile paths: `profiles/`. Check: `git diff profile1-done profile2-done -- src/plantmon db` must be empty. `profile1-done` is tagged after the schema, index and data-quality work of M2 and before any profile 2 file is added, so that the diff contains only what profile 2 needed.
- If not empty, every change is listed with its reason in a generality report and the criterion is reported as not met.
- Running detection evaluation on profile 2 is optional; if done, it uses these criteria and is reported separately.

## 10. Reporting

- The README results section shows every system including R0, with confidence intervals, whatever the outcome.
- Negative results get the same prominence as positive ones.
- Any deviation from this file goes into a deviations log with date and reason.

## 11. Freeze and change policy

- The tag `eval-criteria-v1` is created only after Huy confirms P1-P5, and before any detector runs on validation or test data.
- After the tag this file is never edited, not even for typos. Corrections go to an errata file; changed criteria become a new file labelled v2 and v1 results stay.
- Commits and tags follow the usual rule: nothing is committed until Huy sends "xong".

## 12. Known weaknesses of this protocol

- On simulated data the author defines both the anomalies and the detectors, so the simulator results cannot show real-world performance.
- One simulator and simple noise models; the gap to real plants is not measured.
- Cross-sensor relations in the simulator are linear and set by the author; real plants have nonlinear, noisier relations.
- The simulated training split contains no incidents, by design; real training data would rarely be this clean.
- Because the training split holds no incidents, the ML method cannot learn from the simulator what faults or attacks look like; any diagnosis (D1) comes from rules or is reported as not evaluated.
- BATADAL is also simulated, has attack labels only, and its validation labels are approximate.
- Event definitions with merging and overlap matching favour long incidents; point-level metrics are reported alongside for that reason.
- With 35 incidents per split, confidence intervals will be wide. That is reported, not hidden.
- Feature look-back windows are capped at the 48-hour margin, so methods that need longer history (for example weekly patterns) are not evaluated.
