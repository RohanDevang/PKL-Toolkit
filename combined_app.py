import streamlit as st
import pandas as pd
import io
import sys

# ---------------------------
# Streamlit UI
# ---------------------------
st.set_page_config(layout="wide", page_title="Kabaddi QC Tool")

# st.title("Kabaddi Data Processing & QC Tool - Old Dashboard")
st.markdown(
    '<h1>Kabaddi Data Processing & QC tool - <span style="color:yellow;">New DashBoard</span></h1>',
    unsafe_allow_html=True
)

st.markdown("")

# --- Upload CSV ---
uploaded_file = st.file_uploader("Upload raw Kabaddi CSV, process it, and download the cleaned output.", type=["csv"])

if uploaded_file:
    # Store raw_df in session_state for safe access
    st.session_state.raw_df = pd.read_csv(
        uploaded_file, delimiter=';', header=None, dtype=str, skiprows=1
    )

    # --- Show Total Rows and Columns ---
    rows, cols = st.session_state.raw_df.shape if st.session_state.raw_df is not None else (0, 0)
    st.write(f"**Total rows:** `{rows}` | **Total columns:** `{cols}`")

    # --- Show first 5 rows of raw file ---
    st.subheader("Raw File Preview")
    st.dataframe(st.session_state.raw_df.head())


    # CSS to style the Process button
    st.markdown(
    """
    <style>
    div.stButton>button {
        color: yellow !important;
        font-weight: bolder !important;
        font-size: 30px !important;  /* Increase font size */
        background-color: black !important;
        border: none !important;
        padding: 10px 20px !important; /* Makes button bigger */
    }
    </style>
    """,
    unsafe_allow_html=True)

    # --- Process Button ---
    if st.button("Process CSV", use_container_width=True):

        st.subheader("Quality Check Logs")
        log_output = io.StringIO()
        sys.stdout = log_output  # Capture all print statements

        try:
            # Save uploaded file temporarily in Streamlit environment
            temp_file_path = "temp_raw.csv"
            with open(temp_file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            raw_file_name = temp_file_path
            output_file_name = "processed_output.csv"

            # --- Match Metadata ---
            tour_id = "T001"
            seas_id = "S12"
            match_no = "02"
            match_id = 6465

            # Define raw_df before using it
            raw_df = st.session_state.raw_df.copy()

            # Step 2: Find the row where the first column is strictly "Name"
            header_row_idx_search = raw_df[raw_df.iloc[:, 0].astype(str).str.strip() == "Name"].index

            if header_row_idx_search.empty:
                print("❌ Could not find a row strictly equal to 'Name'.")
                sys.exit()

            header_row_idx = header_row_idx_search[0]

            # Step 3: Use that row as the header, and keep only the rows below it
            df = raw_df.copy()
            df.columns = df.iloc[header_row_idx].astype(str).str.strip()
            df = df.iloc[header_row_idx + 1:].reset_index(drop=True)

            # Step 4: Keep only rows where first column strictly starts with "Raid "
            df = df[df.iloc[:, 0].astype(str).str.strip().str.startswith("Raid ")].reset_index(drop=True)

            if df.empty:
                print("❌ No rows found strictly starting with 'Raid '.")
                sys.exit()

            # Step 5: Rename Columns
            new_col_names = [
                'Name','Time','Start','Stop','Team','Player','Raid 1','Raid 2','Raid 3',
                'D1','D2','D3','D4','D5','D6','D7','Successful','Empty','Unsuccessful',
                'Bonus','No Bonus','Z1','Z2','Z3','Z4','Z5','Z6','Z7','Z8','Z9','RT0',
                'RT1','RT2','RT3','RT4','RT5','RT6','RT7','RT8','RT9','DT0','DT1','DT2',
                'DT3','DT4','Hand touch','Running hand touch','Toe touch','Running Kick',
                'Reverse Kick','Side Kick','Def self out','Body hold','Ankle hold','Single Thigh hold',
                'Push','Dive','DS0','DS1','DS2','DS3','In Turn','Out Turn','Create Gap','Jump','Dubki',
                'Struggle','Release','Block','Chain_def','Follow','Technical Point','All Out',
                'RL1','RL2','RL3','RL4','RL5','RL6','RL7','RL8','RL9','RL10','RL11','RL12','RL13','RL14',
                'RL15','RL16','RL17','RL18','RL19','RL20','RL21','RL22','RL23','RL24','RL25','RL26','RL27',
                'RL28','RL29','RL30','Raider self out','Running Bonus','Centre Bonus','LCorner','LIN',
                'LCover','Center','RCover','RIN','RCorner','Flying Touch','Double Thigh Hold',
                'Flying Reach','Clean','Not Clean',
                # Extra 7 columns
                'Yes','No','Z10','Z11','Right','Left','Centre'
            ]

            if len(df.columns) == len(new_col_names):
                df.columns = new_col_names
            else:
                print(f"❌ Column mismatch: got {len(df.columns)}, expected {len(new_col_names)}")
                sys.exit()

            # =========================================================================
            # START: Part 2 - Transformation and QCs
            # This part now uses the 'df' from above instead of reading a new file.
            # =========================================================================

            # --- Helper function to safely convert columns to numeric ---
            def safe_to_numeric(df_in, cols):
                for col in cols:
                    if col in df_in.columns:
                        df_in[col] = pd.to_numeric(df_in[col], errors='coerce')
                return df_in

            # ---------------- Drop unused columns ----------------
            df.drop(['Time', 'Team'], axis=1, inplace=True)

            # ---------------- Raid_Number ----------------
            df = safe_to_numeric(df, ['Raid 1', 'Raid 2', 'Raid 3']) # ERROR FIX
            df['Raid 2'] = df['Raid 2'].replace(1, 2)
            df['Raid 3'] = df['Raid 3'].replace(1, 3)
            df['Raid_1'] = (
                df['Raid 1'].fillna(0).astype(int) +
                df['Raid 2'].fillna(0).astype(int) +
                df['Raid 3'].fillna(0).astype(int)
            )
            df = df.drop(['Raid 1', 'Raid 2', 'Raid 3'], axis=1).rename(columns={ # Dropped Raid 1 here
                'Raid_1': 'Raid_Number',
                'Name': 'Event_Number',
                'Technical Point': 'Technical_Point',
                'All Out': 'All_Out'
            })

            # ---------------- Number_of_Defenders ----------------
            defender_cols = ['D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7']
            df = safe_to_numeric(df, defender_cols) # ERROR FIX
            for idx, col in enumerate(defender_cols, 1):
                df[col] = df[col].replace(1, idx)
            df['Number_of_Defenders'] = df[defender_cols].fillna(0).sum(axis=1).astype(int)
            df.drop(columns=defender_cols, inplace=True)

            # ---------------- Outcome ----------------
            # Using string keys {'1', '0'} because data is read as string initially
            df['Successful'] = df['Successful'].replace({'1': 'Successful', '0': ''})
            df['Empty'] = df['Empty'].replace({'1': 'Empty', '0': ''})
            df['Unsuccessful'] = df['Unsuccessful'].replace({'1': 'Unsuccessful', '0': ''})
            df['Outcome'] = df['Successful'].fillna('') + df['Empty'].fillna('') + df['Unsuccessful'].fillna('')
            df.drop(['Successful', 'Unsuccessful', 'Empty'], axis=1, inplace=True)

            # ------ Bonus ------
            df_bonus = df[['Bonus', 'No Bonus', 'Centre Bonus', 'Running Bonus']].copy()
            df_bonus['Bonus'] = df_bonus[['Bonus', 'Centre Bonus', 'Running Bonus']].eq(1).any(axis=1).replace({True: 'Yes', False: ''})
            df_bonus['No Bonus'] = df_bonus['No Bonus'].replace({1: "No", 0: ''})
            df_bonus['Bonus'] = df_bonus['Bonus'] + df_bonus['No Bonus']
            df_bonus.loc[(df[['Bonus', 'No Bonus', 'Centre Bonus', 'Running Bonus']] == 0).all(axis=1), 'Bonus'] = 'No'
            df_bonus['Bonus'] = df_bonus['Bonus'].str.strip()
            df_bonus.drop(columns=['No Bonus', 'Centre Bonus', 'Running Bonus'], inplace=True)

            # ------ Type_of_Bonus ------
            cols = ['Bonus', 'Centre Bonus', 'Running Bonus']
            for col in cols:
                df[col] = df[col].replace({1: col, 0: ''})
            df['Type_of_Bonus'] = df['Bonus'] + df['Centre Bonus'] + df['Running Bonus']
            df.drop(columns=['Bonus', 'No Bonus', 'Centre Bonus', 'Running Bonus'], inplace=True)
            df = pd.concat([df_bonus, df], axis=1)

            # ---------------- Zone_of_Action ----------------
            cols = ['Z1', 'Z2', 'Z3', 'Z4', 'Z5', 'Z6', 'Z7', 'Z8', 'Z9', 'Z10', 'Z11']
            for col in cols:
                df[col] = df[col].replace({'1': col, '0': ""}) # ERROR FIX
            df['Zone_of_Action'] = df[cols].fillna('').sum(axis=1)
            df.drop(columns=cols, inplace=True)

            # ---------------- Raiding_Team_Points ----------------
            cols = [f'RT{i}' for i in range(10)]
            df = safe_to_numeric(df, cols) # ERROR FIX
            for col in cols:
                num = int(col.replace("RT", ""))
                df[col] = df[col].replace(1, num)
            df['Raiding_Team_Points'] = df[cols].fillna(0).sum(axis=1).astype(int)
            df.drop(columns=cols, inplace=True)

            # ---------------- Defending_Team_Points ----------------
            cols = [f'DT{i}' for i in range(5)]
            df = safe_to_numeric(df, cols) # ERROR FIX
            for col in cols:
                num = int(col.replace('DT', ''))
                df[col] = df[col].replace(1, num)
            df['Defending_Team_Points'] = df[cols].fillna(0).astype(int).sum(axis=1)
            df.drop(columns=cols, inplace=True)

            # ---------------- Attacking_Skill ----------------
            cols = ['Hand touch', 'Running hand touch', 'Toe touch', 'Running Kick', 'Reverse Kick',
                    'Side Kick', 'Def self out', 'Flying Touch']
            for col in cols:
                df[col] = df[col].replace({'1': col, '0': ''}) # ERROR FIX
            df[cols] = df[cols].fillna('')
            df['Attacking_Skill'] = df[cols].apply(lambda x: ', '.join(filter(None, x)), axis=1)
            df.drop(columns=cols, inplace=True)

            # ---------------- Defensive_Skill ----------------
            cols = ['Body hold', 'Ankle hold', 'Single Thigh hold', 'Double Thigh Hold', 'Push',
                    'Dive', 'Block', 'Chain_def', 'Follow', 'Raider self out']
            for col in cols:
                df[col] = df[col].replace({'1': col, '0': ''}) # ERROR FIX
            df[cols] = df[cols].fillna('')
            df['Defensive_Skill'] = df[cols].apply(lambda x: ', '.join(filter(None, x)), axis=1)
            df.drop(columns=cols, inplace=True)

            # ---------------- Defenders_Self_Out ----------------
            cols = ['DS0', 'DS1', 'DS2', 'DS3']
            df = safe_to_numeric(df, cols) # ERROR FIX
            for col in cols:
                num = int(col.replace('DS', ''))
                df[col] = df[col].replace(1, num)
            df['Number_of_Defenders_Self_Out'] = df[cols].fillna(0).astype(int).sum(axis=1)
            df.drop(columns=cols, inplace=True)

            # ---------------- Counter_Action_Skill ----------------
            cols = ['In Turn', 'Out Turn', 'Create Gap', 'Jump', 'Dubki', 'Struggle', 'Release', 'Flying Reach']
            for col in cols:
                df[col] = df[col].replace({'1': col, '0': ''}) # ERROR FIX
            df[cols] = df[cols].fillna('')
            df['Counter_Action_Skill'] = df[cols].apply(lambda x: ', '.join(filter(None, x)), axis=1)
            df.drop(columns=cols, inplace=True)

            # ---------------- Raid_Length ----------------
            cols = [f'RL{i}' for i in range(1, 31)]
            df = safe_to_numeric(df, cols) # ERROR FIX
            for col in cols:
                num = int(col.replace('RL', ''))
                df[col] = df[col].replace(1, num)
            df['Raid_Length'] = 30 - df[cols].fillna(0).astype(int).sum(axis=1)
            df.drop(columns=cols, inplace=True)

            # ------ Defender_Position ------
            cols = ['LCorner', 'LIN', 'LCover', 'Center', 'RCover', 'RIN', 'RCorner']
            for col in cols:
                df[col] = df[col].replace({1: col, 0: ''})
            df[cols] = df[cols].fillna('')
            df['Defender_Position'] = df[cols].apply(lambda x: ', '.join(filter(None, x)), axis=1)
            df.drop(columns=cols, inplace=True)

            # ------ QoD_Skill ------
            cols = ['Clean', 'Not Clean']
            for col in cols:
                df[col] = df[col].replace({1: col, 0: ''})
            df[cols] = df[cols].fillna('')
            df['QoD_Skill'] = df[cols].apply(lambda x: ', '.join(filter(None, x)), axis=1)
            df.drop(columns=cols, inplace=True)
            
            # ---------------- Tie Break Raids ----------------
            cols = ['Yes', 'No']
            for col in cols:
                df[col] = df[col].replace({1: col, 0: ''})
            df[cols] = df[cols].fillna('')
            df['Tie_Break_Raids'] = df[cols].apply(lambda x: ', '.join(filter(None, x)), axis=1)
            df.drop(columns=cols, inplace=True)

            # ---------------- Add Identifiers ----------------
            n = len(df)
            df['Tournament_ID'] = tour_id
            df['Season_ID'] = seas_id
            df['Match_No'] = match_no
            df['Match_ID'] = match_id
            df['Match_Raid_Number'] = range(1, n + 1)

            # ---------------- Raider & Defenders Names ----------------
            # Split the 'Player' column by '|'
            parts = df['Player'].str.split(r'\s*\|\s*', expand=True)
            
            # Remove jersey numbers for ALL players (handles nulls automatically)
            parts = parts.apply(lambda col: col.str.split('-', n=1).str[1].str.strip().str.title())
            
            # Ensure there are always 8 columns (1 Raider + 7 Defenders)
            while parts.shape[1] < 8:
                parts[parts.shape[1]] = None
            
            # Rename columns
            names = parts.iloc[:, :8].rename(columns={
                0: 'Raider_Name', 1: 'Defender_1_Name', 2: 'Defender_2_Name',
                3: 'Defender_3_Name', 4: 'Defender_4_Name', 5: 'Defender_5_Name',
                6: 'Defender_6_Name', 7: 'Defender_7_Name'
            })
            
            # Merge back into the dataframe
            df = df.drop(columns='Player').join(names)

            # ---------------- Start & Stop Time ----------------
            df['Start'] = df['Start'].str.split(',').str[0]
            df['Stop'] = df['Stop'].str.split(',').str[0]
            
            def parse_time(t):
                if pd.isna(t): return pd.NaT
                parts = list(map(int, t.split(":")))
                return pd.Timedelta(minutes=parts[0], seconds=parts[1]) if len(parts) == 2 else pd.Timedelta(hours=parts[0], minutes=parts[1], seconds=parts[2])
            
            df['start_td'] = df['Start'].apply(parse_time)
            df['stop_td'] = df['Stop'].apply(parse_time)
            df['Time'] = (df['stop_td'] - df['start_td']).dt.total_seconds().apply(lambda x: f"{int(x//60):02}:{int(x%60):02}" if pd.notna(x) else None)
            df.drop(columns=['start_td', 'stop_td', 'Stop', 'Start'], inplace=True)

            # ---------------- New Columns ----------------
            new_columns = [
                # --- Extra Columns ---
                'Video_Link', 'Video', 'Event', 'YC_Extra',                     # 4

                # --- TEAM RAID NUMBERING ---
                'Team_Raid_Number',                                             # 1

                # --- TEAMS & PLAYERS IDENTIFICATION ---
                'Raiding_Team_ID', 'Raiding_Team_Name',
                'Defending_Team_ID', 'Defending_Team_Name',
                'Player_ID', 'Raider_ID',                                       # 6

                # --- POINTS BREAKDOWN ---
                'Raiding_Team_Points_Pre', 'Defending_Team_Points_Pre',
                'Raiding_Touch_Points', 'Raiding_Bonus_Points',
                'Raiding_Self_Out_Points', 'Raiding_All_Out_Points',
                'Defending_Capture_Points', 'Defending_Bonus_Points',
                'Defending_Self_Out_Points', 'Defending_All_Out_Points',         # 10

                # --- RAID ACTION DETAILS ---
                'Number_of_Raiders', 'Raider_Self_Out',
                'Defenders_Touched_or_Caught', 'Half'                            # 4
            ]

            # Add empty new columns
            for col in new_columns:
                df[col] = None


            # ---------------- New Logical Order ----------------
            new_order = [

                # 1. Raid Details & Identification
                "Season_ID", "Tournament_ID", "Match_No",
                "Match_ID", "Event_Number", "Match_Raid_Number",
                "Team_Raid_Number", "Raid_Number",
                "Half", "Time", "Raid_Length",                                                              # 11

                # 2. Raid Outcome & Scoring
                "Outcome", "All_Out", "Bonus", "Type_of_Bonus", "Technical_Point", "Raider_Self_Out",
                "Raiding_Touch_Points", "Raiding_Bonus_Points",
                "Raiding_Self_Out_Points", "Raiding_All_Out_Points", "Raiding_Team_Points",
                "Defending_Capture_Points", "Defending_Bonus_Points",
                "Defending_Self_Out_Points", "Defending_All_Out_Points", "Defending_Team_Points",
                "Number_of_Raiders", "Defenders_Touched_or_Caught",
                "Raiding_Team_Points_Pre", "Defending_Team_Points_Pre", "Zone_of_Action",                     # 21

                # 3. Player & Team Info
                "Raider_Name", "Player_ID",
                "Raider_ID", "Raiding_Team_ID",
                "Raiding_Team_Name", "Defending_Team_ID",
                "Defending_Team_Name",                                                                        # 7

                # 4. Defenders’ Info
                "Number_of_Defenders", "Defender_Position",
                "Defender_1_Name", "Defender_2_Name",
                "Defender_3_Name", "Defender_4_Name",
                "Defender_5_Name", "Defender_6_Name", "Defender_7_Name",
                "Number_of_Defenders_Self_Out",                                                               # 10
            
                # 5. Skills & Actions
                "Attacking_Skill", "Defensive_Skill", "QoD_Skill",
                "Counter_Action_Skill", "Tie_Break_Raids",                                                    # 5

                # 6. Video & Event Metadata
                "Video_Link", "Video", "Event", "YC_Extra"                                                    # 4
            ]

            df = df.reindex(columns = new_order) # Use reindex to avoid errors if a column is missing

            # ---------------- Points Calculation ----------------
            df = safe_to_numeric(df, ['All_Out']) # ERROR FIX
            df["Raiding_Bonus_Points"] = (df["Bonus"] == "Yes").astype(int)
            defender_cols_list = ['Defender_1_Name', 'Defender_2_Name', 'Defender_3_Name', 'Defender_4_Name', 'Defender_5_Name', 'Defender_6_Name', 'Defender_7_Name']
            df['Raiding_Touch_Points'] = 0
            mask = df['Outcome'] == 'Successful'
            df.loc[mask, 'Raiding_Touch_Points'] = df.loc[mask, defender_cols_list].notna().sum(axis=1) - df.loc[mask, 'Number_of_Defenders_Self_Out']
            df["Raiding_All_Out_Points"] = (((df['Outcome'] == 'Successful') & (df["All_Out"] == 1)).astype(int) * 2)
            df['Raiding_Self_Out_Points'] = df['Number_of_Defenders_Self_Out']
            df['Defending_Bonus_Points'] = (((df['Number_of_Defenders'] <= 3) & (df['Outcome'] == 'Unsuccessful')).astype(int))
            df["Raider_Self_Out"] = (df["Defensive_Skill"] == "Raider self out (lobby, time out, empty raid 3)").astype(int)
            df['Defending_Capture_Points'] = (((df['Outcome'] == 'Unsuccessful') & (df['Raider_Self_Out'] == 0)).astype(int))
            df["Defending_All_Out_Points"] = (((df['Outcome'] == 'Unsuccessful') & (df["All_Out"] == 1)).astype(int) * 2)
            df['Defending_Self_Out_Points'] = df["Raider_Self_Out"]


            # ---------------- Quality Checks ----------------

            # QC 1: Empty Columns
            cols = ['Raid_Length', 'Outcome', 'Bonus', 'All_Out', 'Raid_Number', 'Raider_Name', 'Number_of_Defenders']
            mask = df[cols].isna() | df[cols].eq('')
            invalid_rows = df[mask.any(axis=1)]
            if not invalid_rows.empty:
                for idx, row in invalid_rows.iterrows():
                    empty_cols = mask.loc[idx][mask.loc[idx]].index.tolist()
                    print(f"❌ Event {row['Event_Number']}: Empty in columns → {', '.join(empty_cols)}. Please check and update.\n")
            else:
                print("QC 1: ✅ All rows are completely filled. Thank you!\n")

            # QC 2: Outcome Empty consistency
            cols_qc1 = [
                'Defender_1_Name', 'Defender_2_Name', 'Defender_3_Name', 'Defender_4_Name',
                'Defender_5_Name', 'Defender_6_Name', 'Defender_7_Name',
                'Attacking_Skill', 'Defensive_Skill', 'Counter_Action_Skill', 'Zone_of_Action'
            ]
            
            # Replace empty strings or whitespace with NA
            df_clean = df[cols_qc1].replace(r'^\s*$', pd.NA, regex=True)
            cols_empty_qc1 = df_clean.isna().all(axis=1)
            
            mask_qc1_invalid = (
                (df['Outcome'] == 'Empty') & ~(
                    cols_empty_qc1 &
                    (df['All_Out'].fillna(0) == 0) &
                    (df['Raiding_Team_Points'].fillna(0) == 0) &
                    (df['Defending_Team_Points'].fillna(0) == 0) &
                    (df['Bonus'].fillna('No') == 'No')
                )
            )
            
            if mask_qc1_invalid.any():
                for idx, row in df.loc[mask_qc1_invalid].iterrows():
                    non_empty_cols = row[cols_qc1].replace(r'^\s*$', pd.NA, regex=True).dropna().index.tolist()
                    print(f"❌ {row['Event_Number']}: → When Outcome is 'Empty', these columns should be empty: {', '.join(non_empty_cols)}.\n")
            else:
                print("QC 2: ✅ All rows meet QC 1 conditions for Outcome = 'Empty'.\n")


            # QC 3: Successful / Unsuccessful with Bonus = No & Raider_Self_Out = 0
            cols_qc2 = ['Defender_1_Name', 'Number_of_Defenders', 'Zone_of_Action']
            non_empty_outcomes = (
                df['Outcome'].isin(['Successful', 'Unsuccessful'])
            ) & (df['Bonus'] == 'No') & (df['Raider_Self_Out'] == 0)
            cols_filled_qc2 = df[cols_qc2].replace('', pd.NA).notna().all(axis=1)
            mask_qc2_invalid = non_empty_outcomes & ~cols_filled_qc2
            if mask_qc2_invalid.any():
                for idx, row in df[mask_qc2_invalid].iterrows():
                    empty_cols = row[cols_qc2].replace('', pd.NA).isna()
                    missing_cols = empty_cols[empty_cols].index.tolist()
                    print(f"❌ {row['Event_Number']}: When Outcome='{row['Outcome']}', Bonus='No', Raider_Self_Out=0 → Missing: {', '.join(missing_cols)}.\n")
            else:
                print("QC 3: ✅ All rows are Valid.\n")

            # QC 4: Raid_Number = 3 must have Outcome 'Empty'
            mask_invalid = (df['Raid_Number'] == 3) & (df['Outcome'] == 'Empty')
            if mask_invalid.any():
                for idx, row in df[mask_invalid].iterrows():
                    print(f"❌ {row['Event_Number']}: → Outcome is 'Empty' but Raid_No = 3. Please check and update.\n")
            else:
                print("QC 4: ✅ All Raid_Number = 3 rows have valid Outcomes.\n")

            # QC 5: Attacking & Defensive Points match
            def check_points(cols, total_col, label):
                # print(f"\nChecking {label} → '{total_col}'")
                mismatch = df[cols].sum(axis=1) != df[total_col]
                if mismatch.any():
                    for idx, row in df[mismatch].iterrows():
                        print(f"❌ {row['Event_Number']}: → {label} mismatch (Expected: {df.loc[idx, cols].sum()}, Found: {row[total_col]})\n")
                else:
                    print(f"QC 5: ✅ All rows are correct for {label}\n")

            check_points(
                ['Raiding_Touch_Points','Raiding_Bonus_Points','Raiding_Self_Out_Points','Raiding_All_Out_Points'],
                'Raiding_Team_Points',
                label="Attacking Points"
            )
            check_points(
                ['Defending_Capture_Points','Defending_Bonus_Points','Defending_Self_Out_Points','Defending_All_Out_Points'],
                'Defending_Team_Points',
                label="Defensive Points"
            )

            # QC 6: Outcome Successful/Unsuccessful must have points
            def check_points_nonzero(df, outcome, cols, team_name):
                outcome_mask = df['Outcome'].eq(outcome)
                zero_points = df[cols].fillna(0).sum(axis=1).eq(0)
                problem_mask = outcome_mask & zero_points
                if problem_mask.any():
                    for raid_no in df.loc[problem_mask, 'Event_Number'].astype(str):
                        print(f"❌ {team_name}: Raid {raid_no} — Outcome is '{outcome}', but no points were given.\n")
                else:
                    print(f"QC 6: ✅ All {team_name} ({outcome}) rows are correct.\n")

            check_points_nonzero(
                df, 'Successful',
                ['Raiding_Touch_Points', 'Raiding_Bonus_Points', 'Raiding_Self_Out_Points', 'Raiding_All_Out_Points'], 'Raiding'
            )
            check_points_nonzero(
                df, 'Unsuccessful',
                ['Defending_Capture_Points', 'Defending_Bonus_Points', 'Defending_Self_Out_Points', 'Defending_All_Out_Points'], 'Defending'
            )

            # QC 7: Defending_Self_Out_Points > 1
            mismatch = df['Defending_Self_Out_Points'] > 1
            if mismatch.any():
                for msg in "❌ " + df.loc[mismatch, 'Event_Number'].astype(str) + "  Check 'Raider self out' column and Update it\n":
                    print(msg)
            else:
                print('QC 7: ✅ All rows are correct.\n')

            # QC 8: Successful Outcome must reset Raid_Number
            success_rows = df.index[df['Outcome'] == 'Successful']
            mismatches = []
            for idx in success_rows:
                success_event = df.loc[idx, 'Event_Number']
                check_idx = idx + 2
                if check_idx in df.index:
                    if df.loc[check_idx, 'Raid_Number'] != 1:
                        mismatches.append((success_event, df.loc[check_idx, 'Event_Number']))
            if mismatches:
                for s, c in mismatches:
                    print(f"❌ Outcome: 'Successful' {s}, --> {c} should have Raid_Number = 1.\n")
            else:
                print("QC 8: ✅ All rows are correct.\n")

            # QC 9: Empty Raid Consistency
            errors_found = False
            for idx, row in df.iterrows():
                if row['Raid_Number'] == 2 and row['Outcome'] == 'Empty':
                    if idx >= 2:
                        prev_row = df.loc[idx - 2]
                        if prev_row['Raid_Number'] == 1 and prev_row['Outcome'] != 'Empty':
                            print(f"❌ {row['Event_Number']}: Previous raid not Empty\n")
                            errors_found = True
            if not errors_found:
                print("QC 9: ✅ All rows are correct.\n")

            # QC 10: Raid_Length should be > 2
            errors_found = False
            for idx, row in df.iterrows():
                if row['Raid_Length'] <= 2:
                    print(f"⚠️ {row['Event_Number']}: Raid_Length is {row['Raid_Length']}\n")
                    errors_found = True
            if not errors_found:
                print("QC 10: ✅ All rows have valid Raid_Length values.\n")

            # QC 11: Successful, No Bonus -> Defensive & Counter Action Skill consistency
            filtered_df = df[
                (df['Outcome'] == 'Successful') &
                (df['Bonus'] == 'No') &
                (df['Raiding_Touch_Points'] > 0)
            ]
            mismatched_events = filtered_df.loc[
                (filtered_df['Defensive_Skill'].replace('', pd.NA).isna()) !=
                (filtered_df['Counter_Action_Skill'].replace('', pd.NA).isna()),
                'Event_Number'
            ]
            if not mismatched_events.empty:
                for event_num in mismatched_events:
                    print(f"\n❌ {event_num}: -'Defensive_Skill' or 'Counter_Action_Skill' missing.\n")
            else:
                print("QC 11: ✅ All rows are correct.\n")

            # QC 12: Successful, No Bonus, No Defenders Self Out
            fil_df = df[
                (df['Outcome'] == 'Successful') &
                (df['Bonus'] == 'No') &
                (df['Number_of_Defenders_Self_Out'] == 0)
            ].copy()
            for col in ['Attacking_Skill', 'Defensive_Skill', 'Counter_Action_Skill']:
                fil_df[col] = fil_df[col].replace('', pd.NA)
            cond1 = (fil_df['Attacking_Skill'].isna() &
                    (fil_df['Defensive_Skill'].isna() | fil_df['Counter_Action_Skill'].isna()))
            cond2 = (fil_df['Attacking_Skill'].notna() &
                    (fil_df['Defensive_Skill'].notna() | fil_df['Counter_Action_Skill'].notna()))
            qc_wrong_rows = fil_df.loc[cond1 | cond2, 'Event_Number']
            if not qc_wrong_rows.empty:
                for event in qc_wrong_rows:
                    print(f"⚠️ {event}: 'Attacking_Skill' & 'Defensive & Counter_Action_Skill' - all 3 Present Check once.\n")
            else:
                print("QC 12: ✅ All rows are correct.\n")

            # QC 13: Outcome = Unsuccessful -> Defensive_Skill must NOT be empty
            qc_violations = df[
                (df['Outcome'] == 'Unsuccessful') &
                (df['Defensive_Skill'].isna() | (df['Defensive_Skill'].str.strip() == ''))
            ]
            if not qc_violations.empty:
                for idx, row in qc_violations.iterrows():
                    print(f"❌ {row['Event_Number']}: Outcome is 'Unsuccessful' and 'Defensive_Skill' is empty.\n")
            else:
                print("QC 13: ✅ All rows are correct.\n")

            # QC 14: Check Raid_Number sequence

            def kabaddi_raid_number_qc_grouped(df):
                """
                QC to validate Raid_Number using Match_Raid_Number for sorting.
                Prints custom messages for mismatches or success message if no errors.

                Required columns:
                ['Match_Raid_Number', 'Event_Number', 'Outcome', 'Raiding_Team_Name', 'Raid_Number']
                """
                # Sort by Match_Raid_Number to ensure chronological order
                df = df.sort_values(by='Match_Raid_Number').reset_index(drop=True)

                grouped = df.groupby('Raiding_Team_Name')
                error_found = False  # Flag to check if any errors occur

                for team, team_df in grouped:
                    empty_count = 0  # Track consecutive empty raids for this team

                    for _, row in team_df.iterrows():
                        outcome = row['Outcome']
                        raid_num = row['Raid_Number']
                        event_number = row['Event_Number']

                        # ---- Determine expected Raid_Number ----
                        if empty_count == 0:
                            expected = 1
                        elif empty_count == 1:
                            expected = 2
                        else:
                            expected = 3  # Do-or-Die

                        # ---- Check for errors ----
                        if raid_num != expected:
                            print(
                                f"❌ {event_number}: Outcome is '{outcome}' and 'Raid_Number' is {raid_num}. "
                                f"Expected 'Raid_Number': {expected}. Please check and update."
                            )
                            error_found = True

                        # ---- Update empty_count ----
                        if outcome == "Empty":
                            empty_count += 1
                        else:
                            empty_count = 0  # Reset on Successful or Unsuccessful

                # Final message if no errors found
                if not error_found:
                    print("QC 14: ✅ All rows are correct.\n")

            kabaddi_raid_number_qc_grouped(df)

            # --- QC 15: Defender without Position ---
            qc_failed = df[(df["Defender_1_Name"].notna()) & (df["Defender_Position"].isna() | (df["Defender_Position"] == ""))]
            if qc_failed.empty:
                print("\nQC 15: ✅ All defenders have positions.\n")
            else:
                for event in qc_failed['Event_Number']:
                    print(f"\n❌ {event}: Defender(s) present but 'Defender_Position' is empty.\n")

            # --- QC 16: Defensive_Skill & QoD_Skill Alignment ---
            qc_failed_1 = df[(df["Defensive_Skill"].fillna("").str.strip() != "") & (df["QoD_Skill"].fillna("").str.strip() == "")]
            qc_failed_2 = df[(df["QoD_Skill"].fillna("").str.strip() != "") & (df["Defensive_Skill"].fillna("").str.strip() == "")]
            if qc_failed_1.empty and qc_failed_2.empty:
                print("QC 16: ✅ Defensive_Skill and QoD_Skill are aligned correctly.")
            else:
                if not qc_failed_1.empty:
                    print(f"❌ [Type 1]: {qc_failed_1['Event_Number'].tolist()} → Defensive_Skill present but QoD_Skill missing.")
                if not qc_failed_2.empty:
                    print(f"❌ [Type 2]: {qc_failed_2['Event_Number'].tolist()} → QoD_Skill present but Defensive_Skill missing.")


            # ============================================================================

            # Example: saving final processed dataframe
            df.to_csv(output_file_name, index=False)

            # Reset stdout back to default
            sys.stdout = sys.__stdout__

            # --- Show QC logs in scrollable box ---
            qc_text = log_output.getvalue()

            st.markdown(
                f"""
                <div style="height:400px; overflow-y:scroll; border:2px solid yellow;
                            border-radius:8px; padding:10px; background-color:#1E1E1E; color:white;">
                    <pre>{qc_text}</pre>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.markdown("")
            st.markdown("")
            # --- Show Total Rows and Columns for PROCESSED file ---
            final_rows, final_cols = df.shape if df is not None else (0, 0)
            st.write(f"**Total rows:** `{final_rows}` | **Total columns:** `{final_cols}`")

            # Show first 5 rows of final CSV
            st.subheader("Processed File Preview")
            st.dataframe(df.head())


            # CSS to style the download button
            st.markdown(
            """
            <style>
            div.stDownloadButton>button {
                color: yellow !important;
                font-weight: bolder !important;
                font-size: 30px !important;  /* Increase font size */
                background-color: black !important;
                border: none !important;
                padding: 10px 20px !important; /* Makes button bigger */
            }
            </style>
            """,
            unsafe_allow_html=True)

            # Download button
            with open(output_file_name, "rb") as f:
                st.download_button(
                    label="Download Processed CSV",
                    data=f,
                    file_name="processed_output.csv",
                    mime="text/csv",
                    use_container_width=True
                )

        except Exception as e:
            sys.stdout = sys.__stdout__
            st.error(f"❌ An error occurred: {e}")

