import streamlit as st
import pandas as pd
import io

# ==============================================================================
# --- Function for Mode 1: Raw Data Cleaner ---
# ==============================================================================
def process_csv(df_raw):
    # Step 1: Locate the row where the first column starts with "Raid"
    header_row_idx = df_raw[df_raw.iloc[:, 0].astype(str).str.strip().str.startswith("Raid")].index
    if header_row_idx.empty:
        raise ValueError("❌ Could not find data rows starting with 'Raid'. Please check the CSV format.")
    
    # Keep only "Raid ..." rows
    df = df_raw.loc[header_row_idx].reset_index(drop=True)

    # Step 2: Define expected new column names
    new_col = [
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

    # Step 3: Validate column count before renaming
    if len(df.columns) != len(new_col):
        raise ValueError(f"Column count mismatch: The filtered data has {len(df.columns)} columns, but {len(new_col)} were expected.")
    
    df.columns = new_col
    return df

# ==============================================================================
# --- Function for Mode 2: Process Cleaned Data with QC ---
# ==============================================================================
def process_and_qc(df):
    """
    This function contains all the data processing and quality check logic
    from the original script.
    It takes a raw DataFrame and returns the processed DataFrame and a list of QC messages.
    """
    qc_log = []

    # ------ Make a copy to avoid modifying the original uploaded df ------
    df = df.copy()

    # ------ Define IDs (Hardcoded as in the original script) ------
    tour_id = "T001"
    seas_id = "pm_24-25"
    match_no = "01"
    match_id = "M001"

    # ------ Initial Cleanup ------
    if 'Time' in df.columns and 'Team' in df.columns:
        df.drop(['Time', 'Team'], axis=1, inplace=True)

    # ------ Raid_Number ------
    df['Raid 2'] = df['Raid 2'].replace(1, 2)
    df['Raid 3'] = df['Raid 3'].replace(1, 3)
    df['Raid 1'] = df['Raid 1'].astype(int) + df['Raid 2'].astype(int) + df['Raid 3'].astype(int)
    df = df.drop(['Raid 2', 'Raid 3'], axis=1).rename(columns={
        'Raid 1': 'Raid_Number',
        'Name': 'Event_Number',
        'Technical Point': 'Technical_Point',
        'All Out': 'All_Out'
    })

    # ------ Number_of_Defenders ------
    cols = ['D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7']
    for idx, col in enumerate(cols, 1):
        df[col] = df[col].replace(1, idx)
    df['Number_of_Defenders'] = df[cols].astype(int).sum(axis=1)
    df.drop(columns=cols, inplace=True)

    # ------ Outcome ------
    df['Successful'] = df['Successful'].replace({1: 'Successful', 0: ''})
    df['Empty'] = df['Empty'].replace({1: 'Empty', 0: ''})
    df['Unsuccessful'] = df['Unsuccessful'].replace({1: 'Unsuccessful', 0: ''})
    df['Outcome'] = df['Successful'] + df['Empty'] + df['Unsuccessful']
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

    # ------ Zone_of_Action ------
    cols = ['Z1', 'Z2', 'Z3', 'Z4', 'Z5', 'Z6', 'Z7', 'Z8', 'Z9', 'Z10', 'Z11']
    for col in cols:
        df[col] = df[col].replace({1: col, 0: ""})
    df['Zone_of_Action'] = df[cols].sum(axis=1)
    df.drop(columns=cols, inplace=True)

    # ------ Raiding_Team_Points ------
    cols = ['RT0', 'RT1', 'RT2', 'RT3', 'RT4', 'RT5', 'RT6', 'RT7', 'RT8', 'RT9']
    for col in cols:
        num = int(col.replace("RT", ""))
        df[col] = df[col].replace(1, num)
    df['Raiding_Team_Points'] = df[cols].astype(int).sum(axis=1)
    df.drop(columns=cols, inplace=True)

    # ------ Defending_Team_Points ------
    cols = ['DT0', 'DT1', 'DT2', 'DT3', 'DT4']
    for col in cols:
        num = int(col.replace("DT", ""))
        df[col] = df[col].replace(1, num)
    df['Defending_Team_Points'] = df[cols].astype(int).sum(axis=1)
    df.drop(columns=cols, inplace=True)

    # ------ Attacking_Skill ------
    cols = ['Hand touch', 'Running hand touch', 'Toe touch', 'Running Kick', 'Reverse Kick', 'Side Kick', 'Def self out', 'Flying Touch']
    for col in cols:
        df[col] = df[col].replace({1: col, 0: ''})
    df['Attacking_Skill'] = df[cols].apply(lambda x: ', '.join(filter(None, x)), axis=1)
    df.drop(columns=cols, inplace=True)

    # ------ Defensive_Skill ------
    cols = ['Body hold', 'Ankle hold', 'Single Thigh hold', 'Double Thigh Hold', 'Push', 'Dive', 'Block', 'Chain_def', 'Follow', 'Raider self out']
    for col in cols:
        df[col] = df[col].replace({1: col, 0: ''})
    df['Defensive_Skill'] = df[cols].apply(lambda x: ', '.join(filter(None, x)), axis=1)
    df.drop(columns=cols, inplace=True)

    # ------ No_of_Defenders_Self_Out ------
    cols = ['DS0', 'DS1', 'DS2', 'DS3']
    for col in cols:
        num = int(col.replace('DS', ''))
        df[col] = df[col].replace(1, num)
    df['No_of_Defenders_Self_Out'] = df[cols].astype(int).sum(axis=1)
    df.drop(columns=cols, inplace=True)

    # ------ Counter_Action_Skill ------
    cols = ['In Turn', 'Out Turn', 'Create Gap', 'Jump', 'Dubki', 'Struggle', 'Release', 'Flying Reach']
    for col in cols:
        df[col] = df[col].replace({1: col, 0: ''})
    df['Counter_Action_Skill'] = df[cols].apply(lambda x: ', '.join(filter(None, x)), axis=1)
    df.drop(columns=cols, inplace=True)

    # ------ Defender_Positions ------
    cols = ['LCorner', 'LIN', 'LCover', 'Center', 'RCover', 'RIN', 'RCorner']
    for col in cols:
        df[col] = df[col].replace({1: col, 0: ''})
    df['Defender_Pos'] = df[cols].apply(lambda x: ', '.join(filter(None, x)), axis=1)
    df.drop(columns=cols, inplace=True)

    # ------ QoD_Skill ------
    cols = ['Clean', 'Not Clean']
    for col in cols:
        df[col] = df[col].replace({1: col, 0: ''})
    df['QoD_Skill'] = df[cols].apply(lambda x: ', '.join(filter(None, x)), axis=1)
    df.drop(columns=cols, inplace=True)

    # ------ Raiding Length ------
    cols = [f'RL{i}' for i in range(1, 31)]
    for col in cols:
        num = int(col.replace('RL', ''))
        df[col] = df[col].replace(1, num)
    df['Raid_Length'] = 30 - df[cols].astype(int).sum(axis=1)
    df.drop(columns=cols, inplace=True)

    # ------ Side of Raid --------
    cols = ['Right', 'Left', 'Centre']
    for col in cols:
        df[col] = df[col].replace({1: col, 0: ''})
    df['Side_of_Raid'] = df[cols].apply(lambda x: ', '.join(filter(None, x)), axis=1)
    df.drop(columns=cols, inplace=True)

    # ------- Golden Raid --------
    cols = ['Yes', 'No']
    for col in cols:
        df[col] = df[col].replace({1: col, 0: ''})
    df['Golden_Raid'] = df[cols].apply(lambda x: ', '.join(filter(None, x)), axis=1)
    df.drop(columns=cols, inplace=True)


    # ------ Match Metadata ------
    n = len(df)
    df['Tournament_ID'] = tour_id
    df['Season_ID'] = seas_id
    df['Match_No'] = match_no
    df['Match_ID'] = match_id
    df['Match_Raid_No'] = range(1, n + 1)

    # ------ Raider & Defenders Names ------
    parts = df['Player'].str.split(r'\s*\|\s*', expand=True)
    names = parts.apply(lambda s: s.str.split('-', n=1).str[1].str.strip())
    needed_cols = 8
    if names.shape[1] < needed_cols:
        for _ in range(needed_cols - names.shape[1]):
            names[names.shape[1]] = None
    names = names.iloc[:, :needed_cols]
    names.columns = ['Raider_Name', 'Defender_1', 'Defender_2', 'Defender_3', 'Defender_4', 'Defender_5', 'Defender_6', 'Defender_7']
    df.drop(columns='Player', inplace=True)
    df = df.join(names)

    # ------ Start & End Time ------
    df['Start'] = df['Start'].str.split(',').str[0]
    df['Stop'] = df['Stop'].str.split(',').str[0]
    df['start_dt'] = pd.to_datetime(df['Start'], format='%M:%S')
    df['stop_dt'] = pd.to_datetime(df['Stop'], format='%M:%S')
    df['duration'] = df['stop_dt'] - df['start_dt']
    df['total_secs'] = df['duration'].dt.total_seconds()
    df['Time'] = df['total_secs'].apply(lambda x: f"{int(x//60):02}:{int(x%60):02}")
    df.drop(columns=['start_dt', 'stop_dt', 'duration', 'Start', 'Stop', 'total_secs'], inplace=True)

    # ------ Add New Empty Columns ------
    new_columns = ['Video_Link', 'Video', 'Event', 'YC_Extra', 'Team_Raid_Number', 'Raiding_Team_ID', 'Raiding_Team_Name', 'Defending_Team_ID', 'Defending_Team_Name', 'Player_ID', 'Raider_ID', 'Raiding_Team_Points_Pre', 'Defending_Team_Points_Pre', 'Raiding_Touch_Points', 'Raiding_Bonus_Points', 'Raiding_Self_Out_Points', 'Raiding_All_Out_Points', 'Defending_Capture_Points', 'Defending_Bonus_Points', 'Defending_Self_Out_Points', 'Defending_All_Out_Points', 'Number_of_Raiders', 'Raider_Self_Out', 'Defenders_Touched_or_Caught', 'Half']
    for col in new_columns:
        df[col] = None

    # ------ New Logical Order ------
    new_order = ["Season_ID", "Tournament_ID", "Match_No", "Match_ID", "Event_Number", "Match_Raid_No", "Team_Raid_Number", "Raid_Number", "Side_of_Raid", "Golden_Raid", "Half", "Time", "Raid_Length", "Outcome", "All_Out", "Bonus", "Type_of_Bonus", "Technical_Point", "Raider_Self_Out", "Raiding_Touch_Points", "Raiding_Bonus_Points", "Raiding_Self_Out_Points", "Raiding_All_Out_Points", "Raiding_Team_Points", "Defending_Capture_Points", "Defending_Bonus_Points", "Defending_Self_Out_Points", "Defending_All_Out_Points", "Defending_Team_Points", "Number_of_Raiders", "Defenders_Touched_or_Caught", "Raiding_Team_Points_Pre", "Defending_Team_Points_Pre", "Zone_of_Action", "Raider_Name", "Player_ID", "Raider_ID", "Raiding_Team_ID", "Raiding_Team_Name", "Defending_Team_ID", "Defending_Team_Name", "Number_of_Defenders", "Defender_Pos", "Defender_1", "Defender_2", "Defender_3", "Defender_4", "Defender_5", "Defender_6", "Defender_7", "No_of_Defenders_Self_Out", "Attacking_Skill", "Defensive_Skill", "QoD_Skill", "Counter_Action_Skill", "Video_Link", "Video", "Event", "YC_Extra"]
    df = df[new_order]

    # ------ Updating Points Columns ------
    df["Raiding_Bonus_Points"] = (df["Bonus"] == "Yes").astype(int)
    defender_cols = ['Defender_1', 'Defender_2', 'Defender_3', 'Defender_4', 'Defender_5', 'Defender_6', 'Defender_7']
    df['Raiding_Touch_Points'] = 0
    mask = df['Outcome'] == 'Successful'
    df.loc[mask, 'Raiding_Touch_Points'] = (df.loc[mask, defender_cols].notna().sum(axis=1) - df.loc[mask, 'No_of_Defenders_Self_Out'])
    df["Raiding_All_Out_Points"] = (((df['Outcome'] == 'Successful') & (df["All_Out"] == 1)).astype(int) * 2)
    df['Raiding_Self_Out_Points'] = df['No_of_Defenders_Self_Out']
    df['Defending_Bonus_Points'] = (((df['Number_of_Defenders'] <= 3) & (df['Outcome'] == 'Unsuccessful')).astype(int))
    df["Raider_Self_Out"] = (df["Defensive_Skill"] == "Raider self out (lobby, time out, empty raid 3)").astype(int)
    df['Defending_Capture_Points'] = (((df['Outcome'] == 'Unsuccessful') & (df['Raider_Self_Out'] == 0)).astype(int))
    df["Defending_All_Out_Points"] = (((df['Outcome'] == 'Unsuccessful') & (df["All_Out"] == 1)).astype(int) * 2)
    df['Defending_Self_Out_Points'] = df["Raider_Self_Out"]

    #########################################
    ######## VALIDATION OF OUTPUT #########
    #########################################
    qc_log.append("--- QC Checks Initiated ---\n")

    # --- QC Checks for Empty Values ---
    cols = ['Raid_Length', 'Outcome', 'Bonus', 'All_Out', 'Raid_Number', 'Raider_Name', 'Number_of_Defenders']
    mask = df[cols].isna() | df[cols].eq('')
    if mask.any(axis=1).any():
        for idx, row in df[mask.any(axis=1)].iterrows():
            empty_cols = mask.loc[idx][mask.loc[idx]].index.tolist()
            qc_log.append(f"❌ QC Failed: Raid_No: {row['Event_Number']}  → Empty in columns: {', '.join(empty_cols)}. Please check and update.\n")
    else:
        qc_log.append("QC 1: All key columns have values. ✅")

    # --- QC Checks for Outcome = 'Empty' ---
    cols_to_check = ['Defender_1', 'Defender_2', 'Defender_3', 'Defender_4', 'Defender_5', 'Defender_6', 'Defender_7', 'Attacking_Skill', 'Defensive_Skill', 'Counter_Action_Skill', 'Zone_of_Action']
    empty_mask = (df['Outcome'] == 'Empty') & ~(df[cols_to_check].replace('', pd.NA).isna().all(axis=1) & (df['All_Out'] == 0) & (df['Raiding_Team_Points'] == 0) & (df['Defending_Team_Points'] == 0) & (df['Bonus'] == 'No'))
    if empty_mask.any():
        for idx, row in df[empty_mask].iterrows():
            non_empty_cols = row[cols_to_check][row[cols_to_check].replace('', pd.NA).notna()].index.tolist()
            qc_log.append(f"❌ QC Failed: Raid_No: {row['Event_Number']} → When Outcome is 'Empty', these columns should be empty: {', '.join(non_empty_cols)}. Please check and update.\n")
    else:
        qc_log.append("QC 2: All rows meet conditions when Outcome = 'Empty'. ✅")

    # --- QC: Raid_Number = 3 & Outcome = 'Empty' ---
    mask_invalid = (df['Raid_Number'] == 3) & (df['Outcome'] == 'Empty')
    if mask_invalid.any():
        for idx, row in df[mask_invalid].iterrows():
            qc_log.append(f"❌ QC Failed: Raid_No: {row['Event_Number']} → Outcome is 'Empty' but Raid_Number = 3. Please check and update.")
    else:
        qc_log.append("QC 3: All Raid_Number = 3 rows have valid Outcomes. ✅")

    # --- QC for Attacking and Defensive Points ---
    def check_points(df, cols, total_col, label, log):
        log.append(f"\n--- Checking {label} → '{total_col}' ---")
        mismatch = df[cols].sum(axis=1) != df[total_col]
        if mismatch.any():
            for idx, row in df[mismatch].iterrows():
                log.append(f"❌ QC Failed: Raid_No: {row['Event_Number']} → {label} mismatch (Expected: {df.loc[idx, cols].sum()}, Found: {row[total_col]})")
        else:
            log.append(f"All rows are correct for {label}. ✅")

    check_points(df, ['Raiding_Touch_Points','Raiding_Bonus_Points','Raiding_Self_Out_Points','Raiding_All_Out_Points'], 'Raiding_Team_Points', "Attacking Points", qc_log)
    check_points(df, ['Defending_Capture_Points','Defending_Bonus_Points','Defending_Self_Out_Points','Defending_All_Out_Points'], 'Defending_Team_Points', "Defensive Points", qc_log)

    # --- QC for Outcome = ['Successful'] & ['Unsuccessful'] ---
    def check_points_outcome(df, outcome, cols, team_name, log):
        problem_mask = df['Outcome'].eq(outcome) & df[cols].fillna(0).sum(axis=1).eq(0)
        if problem_mask.any():
            for raid_no in df.loc[problem_mask, 'Event_Number'].astype(str):
                log.append(f"❌ QC Failed: {team_name}: Raid {raid_no} — Outcome is '{outcome}', but no points were given . Please check and update the data.")
        else:
            log.append(f"All {team_name} ({outcome}) rows are correct. ✅")

    qc_log.append("\n--- Checking Points vs. Outcome Alignment ---")
    check_points_outcome(df, 'Successful', ['Raiding_Touch_Points', 'Raiding_Bonus_Points', 'Raiding_Self_Out_Points', 'Raiding_All_Out_Points'], 'Raiding', qc_log)
    check_points_outcome(df, 'Unsuccessful', ['Defending_Capture_Points', 'Defending_Bonus_Points', 'Defending_Self_Out_Points', 'Defending_All_Out_Points'], 'Defending', qc_log)

    # --- QC: Defending_Self_Out_Points > 1 ---
    mismatch = df['Defending_Self_Out_Points'] > 1
    if mismatch.any():
        for msg in df.loc[mismatch, 'Event_Number'].astype(str):
            qc_log.append(f"❌ QC Failed: Raid No: {msg} → Check 'Raider self out' column and Update it.")
    else:
        qc_log.append('All rows are correct for Defending_Self_Out_Points. ✅')

    # --- QC: Defender without Position ---
    qc_failed = df[(df["Defender_1"].notna()) & (df["Defender_Pos"].isna() | (df["Defender_Pos"] == ""))]
    if qc_failed.empty:
        qc_log.append("\nQC Passed: All defenders have positions. ✅")
    else:
        qc_log.append(f"\n❌ QC Failed: Raid_No: {qc_failed['Event_Number'].tolist()} Some defenders are missing positions.")

    # --- QC: Defensive_Skill & QoD_Skill Alignment ---
    qc_failed_1 = df[(df["Defensive_Skill"].fillna("").str.strip() != "") & (df["QoD_Skill"].fillna("").str.strip() == "")]
    qc_failed_2 = df[(df["QoD_Skill"].fillna("").str.strip() != "") & (df["Defensive_Skill"].fillna("").str.strip() == "")]
    if qc_failed_1.empty and qc_failed_2.empty:
        qc_log.append("QC Passed: Defensive_Skill and QoD_Skill are aligned correctly. ✅")
    else:
        if not qc_failed_1.empty:
            qc_log.append(f"❌ QC Failed [Type 1]: Raid_No {qc_failed_1['Event_Number'].tolist()} → Defensive_Skill present but QoD_Skill missing.")
        if not qc_failed_2.empty:
            qc_log.append(f"❌ QC Failed [Type 2]: Raid_No {qc_failed_2['Event_Number'].tolist()} → QoD_Skill present but Defensive_Skill missing.")

    return df, qc_log

# ==============================================================================
# Streamlit UI
# ==============================================================================

st.set_page_config(
    layout="wide",
    page_title="Non-PKL Toolkit",
    page_icon="🤼‍♂️"
)
st.title("Kabaddi League Data App (Non-PKL)")

# ===========================
# Step 1: Choose mode
# ===========================
mode = st.radio(
    "Select a workflow:",
    ["📖 Raw Data Cleaner", "📊 Process Cleaned Data with QC"],
    index=0,
    help="Choose 'Raw Data Cleaner' for initial processing of raw, semi-colon delimited files. Choose 'Process Cleaned Data' for further transformation and quality checks on a standard CSV."
)
st.markdown("---")

# ==============================================================================
# --- WORKFLOW 1: Raw Data Cleaner ---
# ==============================================================================
if mode == "📖 Raw Data Cleaner":
    st.header("Workflow 1: Raw Data Cleaner")
    st.write("Upload a raw, semi-colon (;) delimited CSV file to clean and structure it.")
    
    if 'cleaned_df' not in st.session_state:
        st.session_state.cleaned_df = None

    # --- File uploader ---
    uploaded_file = st.file_uploader("Choose a raw CSV file", type="csv")

    if uploaded_file is not None:
        # Decode file as text lines
        raw_text = uploaded_file.getvalue().decode('utf-8').splitlines()

        # --- Raw Preview (first 5 rows as plain text) ---
        st.subheader("📄 Raw Data Preview (first 3 lines of file)")
        for line in raw_text[:3]:
            st.text(line)


        # --- Process File Button ---
        if st.button("Process Raw File", type="primary"):
            try:
                # Find the line number where header ("Name;...") starts
                header_line = None
                for i, line in enumerate(raw_text):
                    if line.strip().startswith("Name;"):
                        header_line = i
                        break
                if header_line is None:
                    raise ValueError("❌ Could not find a header row starting with 'Name;'. Please check the CSV format.")

                # Reload the file starting from header row
                string_data = io.StringIO("\n".join(raw_text[header_line:]))
                df_raw = pd.read_csv(
                    string_data,
                    delimiter=';',
                    header=0,   # now row with "Name;..." is header
                    dtype=str,
                    engine="python"
                )

                # Process only "Raid ..." rows
                with st.spinner('Cleaning data... Please wait.'):
                    cleaned_df = process_csv(df_raw)
                    st.session_state.cleaned_df = cleaned_df

                st.success("✅ Transformation complete!")

            except ValueError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")

    # --- Cleaned Data Preview and Download ---
    if st.session_state.cleaned_df is not None:
        st.markdown("---")
        st.header("🧹 Cleaned Data Preview")
        st.write(f"Final column count: {len(st.session_state.cleaned_df.columns)}")
        st.dataframe(st.session_state.cleaned_df.head())

        @st.cache_data
        def convert_df_to_csv(df):
            return df.to_csv(index=False).encode('utf-8')

        csv_data = convert_df_to_csv(st.session_state.cleaned_df)
        cleaned_filename = uploaded_file.name.replace('.csv', '') + "-CLEANED.csv"

        # Custom CSS
        m = st.markdown("""
        <style>
        div.stDownloadButton > button:first-child {
            background-color: #90EE90;
            color: black;
            border: 1px solid #3CB371;
        }
        div.stDownloadButton > button:first-child:hover {
            background-color: #3CB371;
            color: white;
            border: 1px solid #2E8B57;
        }
        </style>""", unsafe_allow_html=True)
        
        st.download_button(
            label="📥 Download Cleaned CSV",
            data=csv_data,
            file_name=cleaned_filename,
            mime='text/csv',
        )

# ==============================================================================
# --- WORKFLOW 2: Process Cleaned Data with QC ---
# ==============================================================================
if mode == "📊 Process Cleaned Data with QC":
    st.header("Workflow 2: Process Cleaned Data with Quality Checks")
    st.write("Upload the '-CLEANED.csv' file from Workflow 1 to perform transformations and run validation checks.")
    
    # Initialize session state variables
    if 'df_processed' not in st.session_state:
        st.session_state.df_processed = None
    if 'qc_results' not in st.session_state:
        st.session_state.qc_results = None
    if 'file_name' not in st.session_state:
        st.session_state.file_name = "final_output.csv"


    # File Uploader
    uploaded_file = st.file_uploader("Upload your CLEANED CSV file", type=["csv"])

    if uploaded_file is not None:
        try:
            raw_df = pd.read_csv(uploaded_file)
            st.success("File uploaded successfully!")
            st.write(f"Uploaded column count: {len(raw_df.columns)}")
            st.write("Uploaded Data Preview:")
            st.dataframe(raw_df.head())
            
            # Prepare processed filename
            base_name = uploaded_file.name.replace("-CLEANED", "").replace(".csv", "")
            st.session_state.file_name = f"{base_name}-PROCESSED.csv"

            # Processing Button
            st.markdown("---")
            if st.button("Process Data and Run QC Checks", type="primary"):
                with st.spinner("Processing data and running checks... This may take a moment."):
                    processed_df, qc_messages = process_and_qc(raw_df)
                    st.session_state.df_processed = processed_df
                    st.session_state.qc_results = qc_messages
                st.success("✅ Processing and QC complete!")

        except Exception as e:
            st.error(f"An error occurred while reading the file: {e}")
            st.error("Please ensure the uploaded file is a valid CSV with the expected columns from Workflow 1.")


    # Display QC results and Download button only after processing
    st.markdown("---")
    if st.session_state.qc_results:
        st.header("Quality Check (QC) Results")
        # Join the list of messages into a single string with newlines
        qc_output_string = "\n".join(st.session_state.qc_results)
        st.code(qc_output_string, language='text')

    if st.session_state.df_processed is not None:
        st.header("Download Final Processed Data")
        
        # --- Custom CSS for the green button ---
        m = st.markdown("""
        <style>
        div.stDownloadButton > button:first-child {
            background-color: #90EE90; /* Light Green */
            color: black;
            border: 1px solid #3CB371; /* Medium Sea Green for border */
        }
        div.stDownloadButton > button:first-child:hover {
            background-color: #3CB371; /* Medium Sea Green for hover */
            color: white;
            border: 1px solid #2E8B57; /* Sea Green for hover border */
        }
        </style>""", unsafe_allow_html=True)
        # -----------------------------------------

        # Convert DataFrame to CSV in memory
        @st.cache_data
        def convert_df_to_csv(df):
            return df.to_csv(index=False).encode('utf-8')

        csv_data = convert_df_to_csv(st.session_state.df_processed)

        st.download_button(
           label="📥 Download Processed CSV",
           data=csv_data,
           file_name=st.session_state.file_name,
           mime='text/csv',
        )
        st.write(f"Final column count: {len(st.session_state.df_processed.columns)}")
        st.write("Processed Data Preview:")
        st.dataframe(st.session_state.df_processed.head())
