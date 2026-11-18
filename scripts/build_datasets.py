"""Rebuild the four datasets used by notebooks/RandomForest_classifier_regressor.ipynb.

The original training CSV files (forward_AC.csv, forward_CB.csv,
backward_CA.csv, backward_BC.csv) were not preserved. This script rebuilds them
from the Excel files in data/dataset_for_ml/.

Each output file has three columns:
    Time       travel time of the segment, in milliseconds
    Pressure   supply pressure, in bar (3.5, 4, 5 or 6)
    Mechanism  0 = no mechanical fault on the segment, 1 = fault

Run from the repository root:
    python scripts/build_datasets.py

The files are written to notebooks/, next to the training notebook.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "dataset_for_ml"
OUT = ROOT / "notebooks"
COLUMNS = ["Time", "Pressure", "Mechanism"]


def read_columns(file_name, columns):
    """Read three columns (by position) from an Excel file and name them."""
    df = pd.read_excel(DATA / file_name, header=0).iloc[:, columns].copy()
    df.columns = COLUMNS
    return df.dropna(how="all").reset_index(drop=True)


def main():
    datasets = {
        # Forward A -> C: 424 rows, taken as is.
        "forward_AC": read_columns("AC_Downstream_to_Sort.xlsx", [0, 1, 2]),
        # Forward C -> B: the CB columns of the combined forward file (424 rows).
        # The separate CB file has 422 rows; the original training file had 424.
        "forward_CB": read_columns("full_AB_p_m1_m2.xlsx", [3, 4, 5]),
        # Backward C -> A: 421 rows, taken as is.
        "backward_CA": read_columns("CA_Sorting_to_Downstream.xlsx", [0, 1, 2]),
        # Backward B -> C: the file has 422 rows; row 84 (3.5 bar, faulty) is
        # removed so that it lines up pass by pass with backward_CA, which is
        # missing the same pass. This gives the 421 rows of the original training file.
        "backward_BC": read_columns("BC_Upstream_to_Sorting.xlsx", [0, 1, 2]).drop(index=84),
    }

    OUT.mkdir(exist_ok=True)
    for name, df in datasets.items():
        df = df.reset_index(drop=True).astype({"Time": int, "Pressure": float, "Mechanism": int})
        df.to_csv(OUT / f"{name}.csv", index=False)
        counts = df["Mechanism"].value_counts().to_dict()
        print(f"{name}: {len(df)} rows, normal = {counts.get(0, 0)}, faulty = {counts.get(1, 0)}")


if __name__ == "__main__":
    main()
