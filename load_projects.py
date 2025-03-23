import sqlite3

# Connect to the database
conn = sqlite3.connect('timekeeping.db')
cur = conn.cursor()

cur.execute("DROP TABLE IF EXISTS projects")
conn.commit()

# Create the projects table if it doesn't exist
cur.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        project_no INTEGER PRIMARY KEY,
        project_name TEXT NOT NULL,
        project_captain TEXT NOT NULL
    )
    """)
conn.commit()

# Insert project information
projects = [
    (122, 'Sagebrook', 'A Mitchell'),
    (213, 'Port Royal (PR)', 'A Mitchell'),
    (219, 'Cortina', 'A Mitchell'),
    (234, 'Chancellor House', 'G McCutcheon'),
    (249, 'Indigo Townhouses', 'S Houwen'),
    (313, 'Argyll House West', 'G McCutcheon'),
    (314, 'Argyll House East', 'G McCutcheon'),
    (402, 'Folio', 'A Seppanen'),
    (405, 'SFU Lot 10', 'R Wolfe'),
    (411, '6th & Clarkson', 'A Chan'),
    (412, 'UBC Duplexes', 'A Seppanen'),
    (413, 'Chancellor 2', 'B Ramsay'),
    (414, 'Lee Residence', 'D Chies'),
    (420, 'UBC Design Studio', 'S Houwen'),
    (427, 'Trailmobile Collage', 'A Mitchell'),
    (504, 'Camera', 'T Winkler'),
    (508, 'PR Rowhouses', 'M Wodszynski'),
    (515, 'PR High Rise', 'A Seppanen'),
    (516, 'PR Float Homes', 'A Chan'),
    (517, 'PR Phase 3B', 'A Bolin'),
    (518, 'British Pacific Properties (BPP)', 'V Vukojevic'),
    (520, 'T Lee Residence', '0'),
    (607, 'PR Phase 3C', 'T Winkler'),
    (613, 'Mosaic Dominion St', 'S Hsu'),
    (615, 'Lot 62 North Vancouver', 'T Winkler'),
    (626, 'Mosaic Wilkie Ave', 'S Hsu'),
    (631, 'PR Commercial', 'A Chan'),
    (633, 'Reliance 8th St NW', 'A Chan'),
    (705, 'Billy Brown Apartments', 'G McCutcheon'),
    (712, 'PR - 4A - Rental', 'S Hsu'),
    (713, 'Aragon - Wall Street', 'V Vukojevic'),
    (721, 'Mosaic - Roxton Avenue', 'S Hsu'),
    (722, 'DHL - Ewen Avenue', 'T Winkler'),
    (731, 'Polygon - Highland Drive', 'A Chan'),
    (734, 'Mosaic - Clayton Avenue', 'S Hsu'),
    (809, 'Mosaic - S Bonson CC', 'A Bolin'),
    (811, 'Intracorp - Anavets - Market', 'T Winkler'),
    (812, '33rd & Mackenzie', 'A Chan'),
    (825, 'Intergulf - 2222 Burrard St', 'B Ramsay'),
    (831, 'Sikh Temple', 'T Winkler'),
    (833, 'Mt Seymour Seniors Centre', 'A Chan'),
    (906, 'UBCO Student Res Phase 4', 'A Seppanen'),
    (908, 'Mosaic - Baptist Church Site', 'A Mitchell'),
    (909, 'Mosaic - Wilkie Amendment', 'S Hsu'),
    (916, 'PR 3A', 'T Winkler'),
    (921, 'Guardian - Coast Meridian', 'S Hsu'),
    (1004, 'Mosaic - Foster Avenue', 'S Hsu'),
    (1007, 'Intracorp - 3rd and Lonsdale', 'A Chan'),
    (1008, 'PR - 4a - Lots G, H', 'A Chan'),
    (1009, 'PR - 4a - Lot J', 'Al Chan'),
    (1011, 'Mosaic - Como Lake', 'S Hsu'),
    (1014, 'Intracorp - Anavets - Rental', 'J Ralph'),
    (1020, 'Intracorp - Foster Ave - East', 'Kurt/Saeed'),
    (1021, 'Intracorp - Foster Ave - West', 'S Hsu'),
    (1022, 'Mosaic - Cambie Street', 'S Hsu'),
    (1024, 'Parklane -  Village at Bedford', 'A Mitchell'),
    (1104, 'Mosaic - Como Lake II', 'S Hsu'),
    (1106, 'Intracorp - Maywood Park', 'B Ramsay'),
    (1109, 'PR Phase 6 Apts', 'A Chan'),
    (1115, 'Mosaic - Yorkson TH', 'Jack Wu'),
    (1119, 'Intergulf - 4500 Cambie', 'B Ramsay'),
    (1207, 'BBP - The Peak', 'A Bolin'),
    (1220, 'Mosaic - Cambie & 50th', 'S Hsu'),
    (1317, 'Mosaic - 23rd Ave Surrey TH', 'S Hsu'),
    (1403, 'Mosaic - 156 East 35th', '0'),
    (1405, 'UBC Mixed Use', '0'),
    (1406, 'Intracorp - 375 West 59th', 'K McLaren'),
    (1415, 'Mosaic - 54th & Cambie', 'S Hsu'),
    (1417, 'UBC - Lot E', 'S Hsu'),
    (1503, 'Intergulf - Hunter St, N Van', 'C Ding'),
    (1505, 'PR - Phase 6C Apartments', 'A Chan'),
    (1507, 'IPL - Finnish Manor', 'S Hsu'),
    (1508, 'BBP - Lot 37 - Apartments', 'A Seppanen'),
    (1602, 'IPL - Hudson St TH', 'S Hsu'),
    (1604, 'Intergulf - SFU - Lot 17', 'S Hsu'),
    (1607, 'Intergulf Lower Lynn Town Ctre', 'J Heinmiller'),
    (1705, 'Mosaic - Forsythe', 'S Hsu'),
    (1709, 'Aragon - PR 6b CLT apts', 'B Ramsay'),
    (1714, 'Mosaic - SFU - Lot 19', 'S Hsu'),
    (1715, 'Beedie - Fraser Mills 7B; 8B', 'B Ramsay'),
    (1803, 'Qualex - Grange St, Burnaby', 'K McLaren'),
    (1806, 'Aragon - Cambie Station', 'Jack Wu'),
    (1901, 'Quadreal - Maplewood Gardens', 'A Seppanen'),
    (2003, 'IPL - Victoria & 11th', 'S Hsu'),
    (2010, 'NISD - Lot 19', 'B Ramsay'),
    (2011, 'NISD - Lot 17', 'B Ramsay'),
    (2013, 'Qualex - Harrison & Kemsley', 'A Seppanen'),
    (2017, 'Mosaic - Emery 3', 'S Hsu'),
    (2102, 'IPL - 33rd & Commercial', 'K McLaren'),
    (2304, 'Aragon - Two Waters - Lot 1,2', 'C.Ding'),
    (1013, 'Intracorp - Orizon', ''),
    (407, 'Rogers Creek', ''),
    (425, 'British Prop small lot', ''),
    (507, 'CMHC - Nan Hui', ''),
    (614, 'CMHC', ''),
    (622, 'Kamloops Daycare', ''),
    (603, 'P R 2A Rowhouses', ''),
    (429, 'Pringle Creek', ''),
    (630, 'Pringle Creek - Lots 73 - 75', ''),
    (612, 'Anton Street - Whistler', ''),
    (322, 'Quest University', ''),
    (625, 'Quest University - furniture', ''),
    (629, 'Townline - Thompsons Ldg', ''),
    (717, 'Davis Outlook', ''),
    (723, 'SW Coquitlam Housing Study', ''),
    (730, 'Intracorp - Chanc Row Duplex', ''),
    (735, 'UBCO Gateway', ''),
    (736, '800 Maclean Drive', ''),
    (808, 'Intracorp - Barker Highrise', ''),
    (807, 'Richmond - S Mclennan Study', ''),
    (824, 'Prussion - Commercial & 20th', ''),
    (826, 'Coquitlam - Zoning Study', ''),
    (827, 'Coquitlam - How to booklets', ''),
    (829, 'Lynn Valley Masterplan', ''),
    (910, 'Mosaic - Marquerite Study', ''),
    (911, 'Port Coquitlam Infill Housing Study', ''),
    (912, 'New Westminster Gas Works Site', ''),
    (914, 'Tsakumis - 17th Ave Surrey', ''),
    (915, 'City of Nanaimo Urban Design Study', ''),
    (1210, 'Intergulf - Howe Street', ''),
    (1216, 'Queens Hotel - Townhouse', ''),
    (1216, 'Queens Hotel - hourly', ''),
    (1503, 'Intergulf - Hunter Street Comm Ctre', '')
]

cur.executemany('''
INSERT OR IGNORE INTO projects (project_no, project_name, project_captain)
VALUES (?, ?, ?)
''', projects)

# Commit the transaction
conn.commit()

# Close the connection
conn.close()