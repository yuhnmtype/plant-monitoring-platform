# BATADAL verification (M0, 2026-11-06)

Purpose: decide whether BATADAL can be a secondary evaluation set (brief, component 3).
Method: read the official BATADAL data page and the WaterBenchmarkHub page in the browser tools of this session. **No data file was downloaded and no CSV header was inspected.**

## Verified from primary sources

| Item | Finding | Source |
|---|---|---|
| Official data page | https://www.batadal.net/data.html | fetched 2026-11-06 |
| Training dataset 1 | `BATADAL_dataset03.csv`, about one year, simulated, no attacks, released 20 Nov 2016 | official page |
| Training dataset 2 | `BATADAL_dataset04.csv`, about 6 months, several attacks, "some of which are approximately labeled", released 28 Nov 2016 | official page |
| Test dataset | `BATADAL_test_dataset.zip` (contains `BATADAL_test_dataset.csv`), about 3 months, several attacks, no labels, released 20 Feb 2017 | official page |
| Attack lists | published as images: `Attacks_TrainingDataset2.png`, `Attacks_TestDataset.png` | official page |
| Sampling | hourly historical SCADA operations | official page |
| Units | flow in LPS; pressure and water level in metres | official page |
| Network | C-Town, EPANET `.inp` file provided; data are simulated SCADA observations | official page, hub page |
| Format | CSV; column `ATT_FLAG` (1 = attack) plus 43 sensor columns; readings may have been manipulated by the attacker | WaterBenchmarkHub page |
| Citation request | Taormina et al. (2018), Journal of Water Resources Planning and Management 144(8), 04018048, doi 10.1061/(ASCE)WR.1943-5452.0000969 | official page |

## Licence: ambiguous, handle conservatively

The footer of the official data page contains two statements:
- "(c) BATADAL team. All rights reserved"
- "This work is licensed under a Creative Commons Attribution 4.0 International License"

The footer is site-wide. It does not say explicitly that the CSV files carry CC BY 4.0. A Kaggle mirror (third party) labels its copy CC BY 4.0, but that is a secondary claim and is not used as evidence.

Decision for the repo:
1. Do not commit or redistribute any BATADAL file.
2. A download script fetches the files from the official URLs into a git-ignored folder.
3. Cite the paper above in the README and in results tables.
4. Optional: ask the BATADAL team by email whether the data files themselves are CC BY 4.0.

## Not verified (do not claim)

- Exact header of each CSV, and whether a timestamp column exists in all three files.
- Whether the test CSV contains an `ATT_FLAG` column or none.
- A machine-readable source of test labels. The official attack list for the test set is an image. The EPyT-Flow loader appears to return test ground truth, but where that truth comes from was not checked.
- The competition's own scoring formula (time-to-detection and classification score combination). It is in the paper or rules document, not read yet.
- Licence and format of BATADAL 2.0 (process data plus network traces, generated with DHALSIM). Out of scope.
- Figures from secondary summaries (for example a sample count of 12,938 and an 80/20 split from a third-party page). Those describe someone else's experiment and are not used.

## Fit for this project

- Usable: simulated, hourly, CSV, public, chronological files that match a train / validation / test layout.
- Limit 1: only an attack flag exists. There are no physical-fault classes, so BATADAL cannot test fault-versus-attack separation. It tests attack detection only.
- Limit 2: dataset 04 labels are approximate, so threshold selection on it carries label noise.
- Limit 3: hourly sampling and a different network, so results are reported separately from simulator results and never pooled.

Verdict: go, as a secondary evaluation, under the protocol in `docs/evaluation-criteria-v1.md` section 8. If a trustworthy test-label source cannot be established, the test-set part is dropped and that is stated in the README.
