# Data-Driven Predictive Maintenance for Industry 4.0

Data, code and Node-RED flow of a data-driven predictive maintenance study on a **Festo MPS 500 Handling station** (Nazarbayev University, Astana, Kazakhstan).

The project detects **mechanical faults** and **abnormal air pressure** on the station's pneumatic gripper. It does this only from how long the gripper takes to travel between position sensors. Sensor data is collected over an IIoT pipeline (PLC → Node-RED → cloud storage), machine-learning models are trained on it, and the results are shown on a web and mobile dashboard.

## Contents

- [How the experiment works](#how-the-experiment-works)
- [Folder structure](#folder-structure)
- [Data](#data)
- [Notebooks](#notebooks)
- [Node-RED flow](#node-red-flow)
- [Revision analysis](#revision-analysis)
- [How to run](#how-to-run)
- [Known gaps and issues](#known-gaps-and-issues)
- [Authors](#authors)

## How the experiment works

The gripper moves along a pneumatic linear drive and passes three proximity sensors:

| Point | Sensor | PLC input | Name in data |
|---|---|---|---|
| A (start) | Downstream station | I0.2 (`x1B2`) | Downstream / "Down str." |
| C (middle) | Sorting position | I0.3 (`x1B3`) | Sorting / "Sort" |
| B (end) | Upstream station | I0.1 (`x1B1`) | Upstream / "Up str." |

- **Forward pass (A → B):** two travel times are measured, A→C and C→B.
- **Backward pass (B → A):** two travel times are measured, B→C and C→A.

All times are in milliseconds. Node-RED reads the sensors from the Siemens PLC, computes the times and stores them in Google Sheets. The sheets were later downloaded as the Excel files in `data/`.

Two kinds of fault were created on purpose:

- **Pressure:** the supply pressure was set by hand on the valve to **3.5, 4, 5 (normal) or 6 bar**. There is no pressure sensor; the operator noted the value.
- **Mechanical fault ("mechanical obstacle"):** switched on or off separately for each part of the path.
  - `mech_1` = fault between A and C.
  - `mech_2` = fault between C and B.
  - 0 means normal, 1 means faulty.

Pressure and labels were written down while the data was being recorded.

## Folder structure

```
data/
  dataset_for_ml/                 Excel files used to build the ML datasets
  dataset_handling_processing/    Early Excel exports from Node-RED
notebooks/
  RandomForest_classifier_regressor.ipynb   Random Forest fault classifier and pressure regressor
  GradientBoostingRegressor_CV.ipynb        Gradient Boosting pressure regressor
  forward_AC.csv, forward_CB.csv,           The four training datasets
  backward_CA.csv, backward_BC.csv          (see "Training datasets")
  early_experiments/                        Earlier attempts made while developing the method
node-red/
  FINAL.json                      Node-RED flow: data collection + dashboard
revision/                         Revision analysis: grouped validation (see "Revision analysis")
requirements.txt
```

## Data

### File naming

Recording files are named `<direction>_<pressure>_<mech_1>_<mech_2>.xlsx`.

For example, `A_B_3.5_N_Y.xlsx` means:

- forward direction (A → B);
- 3.5 bar;
- no fault between A and C;
- a fault between C and B.

`B_A_...` files are backward passes. `Y` means yes (faulty) and `N` means no (normal).

### `data/dataset_for_ml/`

| File | Content | Rows |
|---|---|---|
| `A_B_*.xlsx`, `B_A_*.xlsx` (32 files) | Raw recordings, one file per condition: 2 directions × 4 pressures × 4 fault combinations | varies |
| `AC_Downstream_to_Sort.xlsx` | Forward A→C: time, pressure, `mech_1` | 424 |
| `CB_Sort_to_Upstream.xlsx` | Forward C→B: time, pressure, `mech_2` | 422 |
| `CA_Sorting_to_Downstream.xlsx` | Backward C→A: time, pressure, `mech_1` | 421 |
| `BC_Upstream_to_Sorting.xlsx` | Backward B→C: time, pressure, `mech_2` | 422 |
| `full_AB_p_m1_m2.xlsx` | Forward A→C and C→B side by side | 424 |
| `full_BA_p_m1_m2.xlsx` | Backward C→A and B→C side by side | 422 |

### Training datasets

The training notebook reads four CSV files, stored in `notebooks/`: `forward_AC.csv`, `forward_CB.csv`, `backward_CA.csv` and `backward_BC.csv`. Each has the columns `Pressure` (bar), `Time` (ms) and `Mechanism` (0 = normal, 1 = fault).

These are the files the reported results were produced with: running the training notebook on them reproduces every result saved in it.

How they relate to the Excel files in `data/dataset_for_ml/`:

| Dataset | Corresponding Excel file | Samples |
|---|---|---|
| forward_AC | `AC_Downstream_to_Sort.xlsx` (identical) | 424 |
| forward_CB | `CB_Sort_to_Upstream.xlsx` plus two repeated rows (see known issues) | 424 |
| backward_CA | `CA_Sorting_to_Downstream.xlsx` (identical) | 421 |
| backward_BC | `BC_Upstream_to_Sorting.xlsx` without its row 84, a pass that is also missing from backward_CA | 421 |

Test set sizes (Normal / Faulty) after the 85 / 15 split:

| Dataset | Samples | Test set |
|---|---|---|
| forward_AC | 424 | 38 / 26 |
| forward_CB | 424 | 32 / 32 |
| backward_CA | 421 | 35 / 29 |
| backward_BC | 421 | 34 / 30 |

### Sample distribution

Each cell is Normal / Faulty, counted from the four training datasets.

| Dataset | 3.5 bar | 4 bar | 5 bar | 6 bar | All |
|---|---|---|---|---|---|
| forward_AC | 40 / 44 | 30 / 40 | 129 / 31 | 57 / 53 | 256 / 168 |
| forward_CB | 40 / 44 | 27 / 43 | 132 / 28 | 60 / 50 | 259 / 165 |
| backward_CA | 40 / 44 | 30 / 40 | 129 / 30 | 55 / 53 | 254 / 167 |
| backward_BC | 40 / 44 | 27 / 43 | 134 / 25 | 60 / 48 | 261 / 160 |

### `data/dataset_handling_processing/`

Earlier exports from Node-RED for some of the conditions, kept for reference.

## Notebooks

### `notebooks/RandomForest_classifier_regressor.ipynb`

Trains and evaluates the Random Forest models for each of the four datasets.

- **Classifier (finds faults):** Random Forest, with time and pressure as inputs and the fault label (`Mechanism`) as output.
- **Regressor (predicts pressure):** Random Forest, with time and the fault label as inputs and pressure as output.
- **Shared steps:**
  - 85 / 15 train/test split with `random_state=42`;
  - scaling with `StandardScaler`;
  - settings chosen by `GridSearchCV` with 5-fold cross-validation.
- **Outputs:** confusion matrices and feature-importance charts. Trained models are saved to `classifier/` and `regressor/`.
- **Last cell:** an example of loading a saved classifier and using it on new data.

### `notebooks/GradientBoostingRegressor_CV.ipynb`

A Gradient Boosting regressor for pressure, using fixed settings (100 trees, learning rate 0.1, depth 3) with 5-fold cross-validation.

### `notebooks/early_experiments/`

Earlier attempts made while developing the method. They are kept for transparency and are **not** the source of the reported results.

| Notebook | What it tries |
|---|---|
| `2nd_Class_Reg_model.ipynb`, `3rd_attempt_Classific_Regression.ipynb` | Random Forest with travel time as the only input |
| `4th_withAggregator.ipynb` | Sliding-window features, plus code that sends predictions to Node-RED over MQTT |
| `Without_scaler.ipynb` | The windowed version without scaling |
| `1_direct_prediction.ipynb`, `zip_file.ipynb` | Decision Tree and XGBoost, testing on whole recording files |
| `Split_dataset.ipynb` | Decision Tree on the combined `full_AB` + `full_BA` data |
| `Bode plot_1.ipynb` | Plots of travel time for different pressures and faults (not a frequency-domain Bode plot) |

These notebooks load data from absolute Windows paths on the author's laptop. Change the paths before running them.

## Node-RED flow

`node-red/FINAL.json` contains two parts.

**1. Data collection.** It does four things:

- reads the three gripper sensors from the PLC (`s7 in` nodes, PLC at 10.1.1.8);
- times each segment in the functions `Carrier2TestingStation` (forward) and `TestingStation2Carrier` (backward);
- formats the values with the "Data converter" functions;
- appends them to Google Sheets.

**2. Dashboard.** A web dashboard and a mobile dashboard (via Remote-RED) show pressure, the fault status of each segment and the travel times.

### Palettes to install

Install these from Node-RED: menu → Manage palette → Install.

| Palette | Nodes |
|---|---|
| `node-red-contrib-s7` | `s7 in`, `s7 endpoint` |
| `node-red-contrib-google-sheets` | `GSheet`, `gauth` |
| `node-red-dashboard` | `ui_chart`, `ui_gauge`, `ui_text`, `ui_button`, `ui_numeric`, `ui_template` |
| `node-red-contrib-remote` | `remote-access`, `remote-config` |

`node-red-dashboard` is deprecated but still works, and this flow needs it. The newer `@flowfuse/node-red-dashboard` uses different node types and will not open these nodes.

The flow imports without the following, but these nodes will show errors until they are set up:

- access to the PLC network;
- a Google service-account key;
- your own Remote-RED instance (its connection code was removed from this copy);
- the dashboard images `/images/phase1_static.jpg` to `phase4_static.jpg`.

## Revision analysis

The folder [`revision/`](revision/) contains an additional analysis made for the manuscript revision. It uses only the real collected data.

**Why it was done.** The original notebook tests the models on a random 15% of the rows. Rows from the same recording run end up in both training and testing, and rows from one run are very similar to each other, which can make accuracy look better than it really is. The revision analysis always tests on **whole recording runs that were not used for training**.

**What it does.**

- Finds the recording run of every row by matching the four training files to the raw recordings in `data/dataset_for_ml/` (16 runs per segment).
- Runs grouped, repeated, nested cross-validation (3 outer folds × 3 repeats; recording run as the group).
- Compares Random Forest and Gradient Boosting with simple baselines and other common models.
- Checks which inputs matter (Time / Pressure / both), how well pressure can be estimated from Time alone, and random-row vs grouped testing.

**Main result.** Fault detection stays at about 86–91% accuracy on forward_AC, backward_CA and backward_BC when tested on new recording runs. For forward_CB it drops from about 89% (random rows) to about 62%, because its normal travel times change between recording runs.

**Data note.** The revision analysis uses 422 rows for forward_CB: the two repeated rows listed under [Data issues](#data-issues) were left out, because they do not occur in the raw recordings. The other three files are used unchanged.

Full method, results and output files: [`revision/README.md`](revision/README.md).

## How to run

1. Install Python 3 and the packages:
   ```
   pip install -r requirements.txt
   ```
2. Create two empty folders in `notebooks/`: `classifier/` and `regressor/`. The notebook saves models into them.
3. Open `notebooks/RandomForest_classifier_regressor.ipynb` in Jupyter and run all cells. It reads the four CSV files from the same folder.

## Known gaps and issues

### Missing files

- **The Gradient Boosting classifier code is not included.**
- **The Gradient Boosting regressor notebook uses fixed settings.** The run with grid search (best learning rate 0.05) is not included, so this notebook's results differ from the grid-searched Gradient Boosting results.

### Data issues

- **The backward datasets have 421 samples; the forward ones have 424.**
- **`forward_CB.csv` contains two rows that appear to be accidental repeats.** Lines 371–372 of the file (6 bar, faulty, 2277 ms and 2279 ms) repeat lines 368–369. They are 2 of 424 samples. The original results were produced with them included; the [revision analysis](#revision-analysis) leaves them out.

### Code issues

- **The Random Forest regressor saves the wrong files.** It saves a classifier and the wrong scaler into `regressor/` instead of the regressor and its own scaler. The printed results are correct.
- **The sliding-window notebooks overstate accuracy.** Neighbouring windows share 9 of their 10 rows and end up in both the training and the test set, so their 96–98% accuracies are too optimistic.

### Dashboard

- **The dashboard shows simulated values, not model output.** It displays fixed or random numbers.
- **The MQTT topics do not match.** The flow listens on the topic `predictive/maintenance`, but the notebook code sends to `mps512/feedback0202`.

## Authors

- **Alisher Yelseitov:** experiments, data collection, models.
- **Zhalgas Bolatbayev:** Node-RED support, data checking and documentation.
- **Tohid Alizadeh:** supervision.

Nazarbayev University, Astana, Kazakhstan.

No licence has been chosen yet. Please contact the authors before reusing the data or code.
