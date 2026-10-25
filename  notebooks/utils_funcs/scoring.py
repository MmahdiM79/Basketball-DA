import pandas as pd
from sklearn.preprocessing import StandardScaler


def calculate_score(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    scaler = StandardScaler()
    df[["vorp_z", "bpm_z", "ws_z"]] = scaler.fit_transform(df[["vorp", "bpm", "ws"]])
    df["score"] = 0.5 * df["vorp_z"] + 0.3 * df["bpm_z"] + 0.2 * df["ws_z"]
    return df
