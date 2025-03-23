import pandas as pd
import sqlite3
import os
import re
import glob
from datetime import datetime
db_path = "timekeeping.db"
conn = sqlite3.connect(db_path)
c = conn.cursor()
