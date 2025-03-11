import pandas as pd
import re
import os
import glob
import concurrent.futures

def parse_hours(val):
    """
    Convert a cell value into hours (float).
      - Blank or 'x' => 0.0
      - Numeric string => float(val)
      - Negative values => clamp to 0.0
    """
    if pd.isnull(val):
        return 0.0
    s = str(val).strip().lower()
    if s in ["", "x"]:
        return 0.0
    try:
        f = float(s)
        return f if f >= 0 else 0.0
    except ValueError:
        return 0.0

def drop_if_both_empty(df_in: pd.DataFrame) -> pd.DataFrame:
    """
    Drop rows if BOTH 'PROJECT NO' and 'PROJECT NAME' are empty.
    Empty means: NaN, blank string, or "0"/"0.0".
    """
    if df_in.empty:
        return df_in
    needed_cols = ["PROJECT NO", "PROJECT NAME"]
    for col in needed_cols:
        if col not in df_in.columns:
            return df_in

    def is_invalid(val):
        if pd.isnull(val):
            return True
        s = str(val).strip()
        return s in ["", "0", "0.0"]

    mask = ~((df_in["PROJECT NO"].apply(is_invalid)) &
             (df_in["PROJECT NAME"].apply(is_invalid)))
    return df_in[mask].copy()

def process_file(file_path, input_base, output_base):
    metrics = {
        "file": file_path,
        "missing_name": 0,
        "missing_date": 0,
        "project_rows": 0,
        "summary_rows": 0,
        "has_summary": 0
    }
    try:
        # Open Excel file (works for both .xls and .xlsx)
        with pd.ExcelFile(file_path) as xls:
            # 1) Extract employee name from Q3 (or R3 if Q3 is empty) and month/year from AJ3.
            df_raw = pd.read_excel(xls, sheet_name="Sheet1", header=None, dtype=str)
        # Q3: row 3 (index 2), col Q (17th col in 1-based => index 16)
        employee_name_raw = df_raw.iloc[2, 16] if (df_raw.shape[0] > 2 and df_raw.shape[1] > 16) else None
        # If Q3 is empty or NaN, try R3 (index 17)
        if pd.isnull(employee_name_raw) or str(employee_name_raw).strip() == "":
            if df_raw.shape[1] > 17:
                employee_name_raw = df_raw.iloc[2, 17]
        # AJ3: row 3 (index 2), col AJ (36th col in 1-based => index 35)
        month_year_raw = df_raw.iloc[2, 35] if (df_raw.shape[1] > 35) else None

        employee_name = (str(employee_name_raw).strip() 
                         if pd.notnull(employee_name_raw) and str(employee_name_raw).strip() != "" 
                         else "Unknown")
        month_year = (str(month_year_raw).strip() 
                      if pd.notnull(month_year_raw) and str(month_year_raw).strip() != "" 
                      else "Unknown")
        if employee_name == "Unknown":
            metrics["missing_name"] = 1
        if month_year == "Unknown":
            metrics["missing_date"] = 1
        print(f"Detected Name = {employee_name}, Month/Year = {month_year}")

        # 2) Read timecard table using row 5 (Excel row 5, index 4) as header.
        with pd.ExcelFile(file_path) as xls:
            df = pd.read_excel(xls, sheet_name="Sheet1", header=4, dtype=str)

        # 3) Limit to the first 36 columns (3 metadata + 31 days + TOTAL + DESCRIPTION/COMMENTS).
        NUM_COLS_TO_KEEP = 36
        df = df.iloc[:, :NUM_COLS_TO_KEEP]

        # 4) Assign expected column names.
        expected_cols = (
            ["PROJECT NO", "PROJECT NAME", "WORK CODE"] +
            [str(i) for i in range(1, 32)] +
            ["TOTAL", "DESCRIPTION / COMMENTS"]
        )
        df.columns = expected_cols[: df.shape[1]]

        # 5) Convert day columns (and TOTAL if present) to numeric hours.
        day_cols = [c for c in df.columns if c.isdigit()]  # "1".."31"
        for c in day_cols:
            df[c] = df[c].apply(parse_hours)
        if "TOTAL" in df.columns:
            df["TOTAL"] = df["TOTAL"].apply(parse_hours)

        # 6) Split data at the row where "PROJECT NAME" contains "subtotal".
        if "PROJECT NAME" not in df.columns:
            raise ValueError("PROJECT NAME column is missing; layout might differ.")
        subtotal_idx = df[df["PROJECT NAME"].str.contains("subtotal", case=False, na=False)].index
        if len(subtotal_idx) > 0:
            subrow = subtotal_idx[0]
            project_data = df.iloc[:subrow].copy()       # project work rows
            summary_data = df.iloc[subrow + 1 :].copy()     # summary rows
        else:
            project_data = df.copy()
            summary_data = pd.DataFrame()

        # 7) Drop rows if BOTH 'PROJECT NO' and 'PROJECT NAME' are empty.
        project_data = drop_if_both_empty(project_data)
        summary_data = drop_if_both_empty(summary_data)

        # 8) EXTRA HANDLING FOR SUMMARY DATA:
        if not summary_data.empty:
            summary_data.reset_index(drop=True, inplace=True)
            # (A) Remove rows starting at the first row where column A (PROJECT NO) contains "total".
            col0 = summary_data.columns[0]
            total_idx = summary_data[ summary_data[col0].fillna("")
                                       .str.lower().str.strip().str.contains("total", na=False)
                                     ].index
            if not total_idx.empty:
                cutoff = total_idx[0]
                summary_data = summary_data.iloc[:cutoff].copy()
            # (B) Collapse the first three columns into one column titled "non-billable".
            if len(summary_data.columns) >= 3:
                c0, c1, c2 = summary_data.columns[0], summary_data.columns[1], summary_data.columns[2]
                summary_data["non-billable"] = (
                    summary_data[c0].fillna("") + " " +
                    summary_data[c1].fillna("") + " " +
                    summary_data[c2].fillna("")
                ).str.strip()
                summary_data.drop(columns=[c0, c1, c2], inplace=True)
                new_cols = ["non-billable"] + [col for col in summary_data.columns if col != "non-billable"]
                summary_data = summary_data[new_cols]

        # 9) EXTRA HANDLING FOR PROJECT DATA:
        # Drop the second row (index 1) from project_data because it is an extra title row.
        if not project_data.empty and len(project_data) > 1:
            project_data = project_data.drop(project_data.index[1]).copy()

        metrics["project_rows"] = len(project_data)
        metrics["summary_rows"] = len(summary_data)
        if not summary_data.empty:
            metrics["has_summary"] = 1

        # 10) Construct output paths preserving the input folder structure.
        rel_path = os.path.relpath(file_path, input_base)
        subdir = os.path.dirname(rel_path)
        proj_out_folder = os.path.join(output_base, subdir, "Projects")
        sum_out_folder = os.path.join(output_base, subdir, "Summaries")
        os.makedirs(proj_out_folder, exist_ok=True)
        os.makedirs(sum_out_folder, exist_ok=True)

        file_safe_name = re.sub(r"\W+", "_", employee_name)
        file_safe_month = re.sub(r"\W+", "_", month_year)
        base_name = f"{file_safe_name}_{file_safe_month}"
        projects_csv = os.path.join(proj_out_folder, f"{base_name}_projects.csv")
        summary_csv = os.path.join(sum_out_folder, f"{base_name}_summary.csv")

        project_data.to_csv(projects_csv, index=False)
        if not summary_data.empty:
            summary_data.to_csv(summary_csv, index=False)
            print(f"[SAVED] {projects_csv} and {summary_csv}")
        else:
            print(f"[SAVED] {projects_csv} (no summary rows)")

        return metrics
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        raise

# ---------------------------------------------------------------------
# MAIN LOOP: Process every employee file from 2003 to 2024.
input_directory = "Timekeeping"
output_base = "Cleaned_Timekeeping"

# Initialize counters and lists.
total_files = 0
successful_files = 0
error_files = 0
errored_files = []
missing_name_count = 0
missing_date_count = 0
total_project_rows = 0
total_summary_rows = 0
files_with_summary = 0

# Gather files from year folders 2003-2024 (both .xls and .xlsx).
all_files = []
for year_folder in os.listdir(input_directory):
    if not year_folder.isdigit():
        continue
    year = int(year_folder)
    if year < 2020 or year > 2024:
        continue
    year_path = os.path.join(input_directory, year_folder)
    if not os.path.isdir(year_path):
        continue
    for month_folder in os.listdir(year_path):
        month_path = os.path.join(year_path, month_folder)
        if not os.path.isdir(month_path):
            continue
        # Use pattern to capture both .xls and .xlsx files.
        for file in glob.glob(os.path.join(month_path, "*.xls*")):
            all_files.append(file)  # file is already a full path

print(f"Total files found: {len(all_files)}")

# Process files in parallel using ThreadPoolExecutor.
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
    future_to_file = {executor.submit(process_file, file, input_directory, output_base): file for file in all_files}
    for future in concurrent.futures.as_completed(future_to_file):
        file = future_to_file[future]
        total_files += 1
        try:
            metrics = future.result()
            successful_files += 1
            if metrics["missing_name"]:
                missing_name_count += 1
            if metrics["missing_date"]:
                missing_date_count += 1
            total_project_rows += metrics["project_rows"]
            total_summary_rows += metrics["summary_rows"]
            files_with_summary += metrics["has_summary"]
        except Exception as exc:
            error_files += 1
            errored_files.append(file)
            print(f"Error processing {file}: {exc}")

# Print summary.
print("\n----- Processing Summary -----")
print(f"Total files processed: {total_files}")
print(f"Successfully processed: {successful_files}")
print(f"Files with errors: {error_files}")
if errored_files:
    print("Errored files:")
    for f in errored_files:
        print("  ", f)
print(f"Files with missing name: {missing_name_count}")
print(f"Files with missing month/year: {missing_date_count}")
print(f"Total project rows processed: {total_project_rows}")
print(f"Total summary rows processed: {total_summary_rows}")
print(f"Files with summary rows: {files_with_summary}")
