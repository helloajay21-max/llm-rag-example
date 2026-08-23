import pandas as pd


def fix_dataframe(df):
    # If only one column, try splitting manually
    if len(df.columns) == 1:
        col = df.columns[0]

        # Try comma split
        df = df[col].str.split(",", expand=True)

        df.columns = ["date", "heart_rate", "steps", "sleep_hours", "bp_systolic"]

    return df


def load_sample_data():
    try:
        df = pd.read_csv("data/sample_health.csv")
        df = fix_dataframe(df)
        return df

    except Exception as e:
        raise ValueError(f"Error loading sample data: {e}")


def load_uploaded_file(uploaded_file):
    try:
        df = pd.read_csv(uploaded_file)
        df = fix_dataframe(df)
        return df

    except Exception as e:
        raise ValueError(f"Error reading uploaded file: {e}")