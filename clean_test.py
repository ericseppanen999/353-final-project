import pandas as pd
import re
import os
import glob
import logging
from datetime import datetime

# https://realpython.com/python-logging/

# log config for catching errors and missing names
# log file will be created in the same directory as the script
error_logger=logging.getLogger("error_logger")
error_logger.setLevel(logging.ERROR)
error_handler=logging.FileHandler("error_log.txt", mode='w')
error_formatter=logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
error_handler.setFormatter(error_formatter)
error_logger.addHandler(error_handler)
missing_logger = logging.getLogger("missing_logger")
missing_logger.setLevel(logging.WARNING)
missing_handler = logging.FileHandler("missing_names_log.txt", mode='w')
missing_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
missing_handler.setFormatter(missing_formatter)
missing_logger.addHandler(missing_handler)


def parse_hours(val):
    # convert cell hours to float
    if pd.isnull(val):
        return 0.0
    s=str(val).strip().lower()
    if s in ["","x"]: # blank or "x" means 0 hours
        return 0.0
    try:
        f=float(s)
        return f if f>=0 else 0.0
    except ValueError:
        return 0.0 # whatever

def drop_if_both_empty(df_in):

    if df_in.empty:
        return df_in
    needed_cols=["PROJECT NO","PROJECT NAME"]

    # check if needed columns are present
    # if not, return the original dataframe
    for col in needed_cols:
        if col not in df_in.columns:
            return df_in
    
    # check invalid values in PROJECT NO and PROJECT NAME columns
    def is_invalid(val):
        if pd.isnull(val):
            return True
        s=str(val).strip()
        return s in ["","0","0.0"]

    # create a mask to filter out rows where both PROJECT NO and PROJECT NAME are invalid
    mask=~((df_in["PROJECT NO"].apply(is_invalid)) & (df_in["PROJECT NAME"].apply(is_invalid)))
    return df_in[mask].copy()

def process_file(file_path,input_base,output_base):
    metrics={"file":file_path,
            "missing_name":0,
            "missing_date":0,
            "project_rows":0,
            "summary_rows":0,
            "has_summary":0
            } # for logging purposes
    try:
        with pd.ExcelFile(file_path) as xls:
            df_raw=pd.read_excel(xls,sheet_name="Sheet1",header=None,dtype=str)
        # manually determine employee name and month/year from the first few rows of the file.
        # if time, try to find a better solution
        # candidate locations for employee name (row, col):
        # priority order: Q3 (2,16), Q2 (1,16), R3 (2,17), O3 (2,14), Q1 (1,16), R1 (1,17), O1 (1,14)
        
        candidates=[(2,16),(1,16),(2,17),(2,14),(1,16),(1,17),(1,14)]
        # find employee name in the candidates
        employee_name_raw=None
        candidate_row=None
        for row_idx,col_idx in candidates:
            if df_raw.shape[0]>row_idx and df_raw.shape[1]>col_idx:
                #cjecl
                candidate=df_raw.iloc[row_idx,col_idx]
                if pd.notnull(candidate) and str(candidate).strip()!="":
                    employee_name_raw=candidate
                    candidate_row=row_idx
                    # found
                    #print(employee_name,candidate_row,candidate)
                    break
        #manually determine month/year from the first few rows of the file
        # for month/year, first try AJ3 (r:3, i:2, c:35),
        # then AJ2 (r:2, i:1, c:35),
        # then AK3 (r:3, i:2, c:36),
        # then AK2 (r:2, i:1, c:36),
        # then AI2 (r:2, i:1, c:34),
        # then AI3 (r:3, i:2, c:34)
        # same as above, but with different column numbers
        month_year_raw=None
        month_year_candidates=[(2,35),(1,35),(2,36),(1,36),(1,34),(2,34)]
        for row_idx,col_idx in month_year_candidates:
            if df_raw.shape[0]>row_idx and df_raw.shape[1]>col_idx:
                candidate=df_raw.iloc[row_idx,col_idx]
                if pd.notnull(candidate) and str(candidate).strip()!="":
                    # print(candidate)
                    month_year_raw=candidate
                    break
        
        # convert employee name and month/year to strings, and strip whitespace
        # if either is missing, log it and set to "Unknown"
        employee_name=str(employee_name_raw).strip() if employee_name_raw is not None else "Unknown"
        month_year = str(month_year_raw).strip() if pd.notnull(month_year_raw) and str(month_year_raw).strip() != "" else "Unknown"
        if employee_name=="Unknown":
            metrics["missing_name"]=1
            missing_logger.warning(f"Missing name in file:{file_path}")
        if month_year=="Unknown":
            metrics["missing_date"]=1
            missing_logger.warning(f"Missing month/year in file:{file_path}")

        print(f"Detected Name = {employee_name}, Month/Year ={month_year}")

        # determine header row for timecard table.
        # we try row 4 (i 3): if that row has at least 5 cells that are purely numeric, we assume it's the header; else use row 5 (i 4).
        header_row_candidate=3
        with pd.ExcelFile(file_path) as xls:
            temp_df=pd.read_excel(xls,sheet_name="Sheet1",header=None,dtype=str)
        if temp_df.shape[0]>header_row_candidate:
            row_contents=temp_df.iloc[header_row_candidate]
            #cells that only contain numeric
            numeric_count = sum(
                1 for cell in row_contents
                if re.match(r'^\d+$', str(cell).strip()))
            header_row=header_row_candidate if numeric_count>=5 else 4
        else:
            header_row=4

        #print(f"Header row = {header_row}")
        #to account for adjusting header rows
        # manual time sheets 
        with pd.ExcelFile(file_path) as xls:
            df=pd.read_excel(xls,sheet_name="Sheet1",header=header_row,dtype=str)

        #limit to first 36 cols since nonsense beyond those sometimes
        #print(df.shape)
        df=df.iloc[:,:36]
        expected_cols=(
            ["PROJECT NO", "PROJECT NAME", "WORK CODE"] +
            [str(i) for i in range(1,32)] +
            ["TOTAL","DESCRIPTION / COMMENTS"])
        df.columns=expected_cols[:df.shape[1]]
        #print(df.columns)
        #print(df.shape[1])
        
        
        day_cols=[c for c in df.columns if c.isdigit()]
        for c in day_cols:
            df[c]=df[c].apply(parse_hours)
        if "TOTAL" in df.columns:
            df["TOTAL"]=df["TOTAL"].apply(parse_hours)

        if "PROJECT NAME" not in df.columns:
            raise ValueError("PROJECT NAME is missing; strange layout")
        subtotal_idx=df[df["PROJECT NAME"].str.contains("subtotal",case=False,na=False)].index
        if len(subtotal_idx)>0:
            subrow=subtotal_idx[0]
            project_data=df.iloc[:subrow].copy()
            summary_data=df.iloc[subrow+1 :].copy()
        else:
            project_data=df.copy()
            summary_data=pd.DataFrame()

        # drop rows if both empty
        project_data=drop_if_both_empty(project_data)
        summary_data=drop_if_both_empty(summary_data)

        # hnalde summary data
        if not summary_data.empty:
            summary_data.reset_index(drop=True,inplace=True)
            #further cleaning
            col0=summary_data.columns[0]
            total_idx=summary_data[summary_data[col0].fillna("").str.lower().str.strip().str.contains("total", na=False)].index
            if not total_idx.empty:
                cutoff=total_idx[0]
                summary_data=summary_data.iloc[:cutoff].copy()
            
            # collapse first 3 cols in 1
            if len(summary_data.columns)>=3:
                c0,c1,c2=summary_data.columns[0],summary_data.columns[1],summary_data.columns[2]
                summary_data["non-billable"]=(summary_data[c0].fillna("") + " " +summary_data[c1].fillna("") + " " +summary_data[c2].fillna("")).str.strip()
                summary_data.drop(columns=[c0, c1,c2],inplace=True)
                new_cols=["non-billable"]+[col for col in summary_data.columns if col!="non-billable"]
                summary_data=summary_data[new_cols]

        if not project_data.empty and len(project_data) > 1:
            project_data = project_data.drop(project_data.index[0]).copy()

        # log
        metrics["project_rows"]=len(project_data)
        metrics["summary_rows"]=len(summary_data)
        if not summary_data.empty:
            metrics["has_summary"]=1

        # alot was drawn inspo from this
        # https://www.youtube.com/watch?v=-ARI4Cz-awo

        rel_path=os.path.relpath(file_path, input_base)
        subdir=os.path.dirname(rel_path)
        proj_out_folder = os.path.join(output_base, subdir, "Projects")
        sum_out_folder = os.path.join(output_base,subdir, "Summaries")
        os.makedirs(proj_out_folder,exist_ok=True)
        os.makedirs(sum_out_folder,exist_ok=True)

        # create file safe name
        file_safe_name=re.sub(r"\W+","_",employee_name)
        file_safe_month =re.sub(r"\W+","_",month_year)
        base_name=f"{file_safe_name}_{file_safe_month}"
        projects_csv=os.path.join(proj_out_folder,f"{base_name}_projects.csv")
        summary_csv=os.path.join(sum_out_folder,f"{base_name}_summary.csv")

        project_data.to_csv(projects_csv,index=False)
        if not summary_data.empty:
            summary_data.to_csv(summary_csv,index=False)
            print(f"[SAVED] {projects_csv}")
            print(f"[SAVED] {summary_csv}")
        else:
            print(f"[SAVED] {projects_csv} (no summary rows)")

        return metrics
    except Exception as e:
        error_logger.error(f"Error processing {file_path}: {e}")
        raise

# main loop
input_directory="Timekeeping"
output_base="Cleaned_Timekeeping"

#log
total_files=0
successful_files=0
error_files=0
errored_files=[]
missing_name_count=0
missing_date_count=0
total_project_rows=0
total_summary_rows=0
files_with_summary=0

all_files=[]
for year_folder in os.listdir(input_directory):
    # check if the folder name is a valid year,month
    if not year_folder.isdigit():
        continue
    year=int(year_folder)
    if year<2004 or year>2025:
        continue
    year_path=os.path.join(input_directory,year_folder)
    if not os.path.isdir(year_path):
        continue
    for month_folder in os.listdir(year_path):
        month_path=os.path.join(year_path,month_folder)
        if not os.path.isdir(month_path):
            continue
        for file in glob.glob(os.path.join(month_path,"*.xls*")):
            if "~$" in os.path.basename(file).lower(): #weird fragmented data
                continue
            all_files.append(file)

#print(f"Found {len(all_files)} files in {input_directory}")
print(f"Total files found: {len(all_files)}")

for file in all_files:
    total_files+=1
    try:
        metrics=process_file(file,input_directory,output_base)
        successful_files+=1
        if metrics["missing_name"]:
            missing_name_count+=1
        if metrics["missing_date"]:
            missing_date_count+=1
        total_project_rows+=metrics["project_rows"]
        total_summary_rows+=metrics["summary_rows"]
        files_with_summary+=metrics["has_summary"]
    except Exception as exc:
        error_files+=1
        errored_files.append(file)
        print(f"Error processing {file}: {exc}")

print("\nProcessing Summary:")
print(f"Total files processed: {total_files}")
print(f"Successfully processed: {successful_files}")
print(f"Files with errors: {error_files}")

if errored_files:
    print("Errored files:")
    for f in errored_files:
        print("  ",f)

print(f"Files with missing name: {missing_name_count}")
print(f"Files with missing month/year: {missing_date_count}")
print(f"Total project rows processed: {total_project_rows}")
print(f"Total summary rows processed: {total_summary_rows}")
print(f"Files with summary rows: {files_with_summary}")

# create a summary file, for personal purpose and future reference
processing_summary_folder="Processing_Summaries"
os.makedirs(processing_summary_folder,exist_ok=True)
timestamp=datetime.now().strftime("%Y%m%d_%H%M%S")
summary_filename=f"processing_summary_{timestamp}.txt"
summary_filepath=os.path.join(processing_summary_folder,summary_filename)


with open(summary_filepath,"w") as f:
    f.write("Processing Summary:\n")
    f.write(f"Timestamp: {datetime.now()}\n")
    f.write(f"Total files processed: {total_files}\n")
    f.write(f"Successfully processed: {successful_files}\n")
    f.write(f"Files with errors: {error_files}\n")
    if errored_files:
        f.write("Errored files:\n")
        for ef in errored_files:
            f.write(f"  {ef}\n")
    f.write(f"Files with missing name: {missing_name_count}\n")
    f.write(f"Files with missing month/year: {missing_date_count}\n")
    f.write(f"Total project rows processed: {total_project_rows}\n")
    f.write(f"Total summary rows processed: {total_summary_rows}\n")
    f.write(f"Files with summary rows: {files_with_summary}\n")


# print("report")
#print("Processing Summary:")
#print(f"Total files processed: {total_files}")


print(f"Processing summary saved to {summary_filepath}")
