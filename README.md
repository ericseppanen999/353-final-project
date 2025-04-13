## Project Dashboard

An interactive Streamlit dashboard built on a cleaned SQLite database, designed to explore employee utilization, project budgets, and time tracking insights.
- **Course**: CMPT 353
- **Project Title**: WORKFORCE AND PROJECT ANALYTICS - DATA PIPELINE & DASHBOARD 
- **Semester**: Spring 2025
- **Team Members**:
  - Annie Boltwood
  - Eric Seppanen

### Instructions To Run ###

First, clone the repository using:
```
git clone https://github.com/ericseppanen999/353-final-project
```
Install the necessary dependencies:
```
pip install -r requirements.txt
```
Then, open the directory on your machine and type:
```
cd Dashboard
```
Now, to run the dashboard:
```
streamlit run main.py
```
The data should already be loaded.

**Cleaning**:
should you want to inspect the cleaning process, you can view clean_test.py
**Loading**
should you want to inspect the loading process, you can view load_projects.py/load_test.py

I would warn against running either file, as they are very time consuming processes and the data is already loaded in the .db file.
