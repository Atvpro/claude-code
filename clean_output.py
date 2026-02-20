#!/usr/bin/env python3
"""
Rensa Descriptions_NO_translated.xlsx:
- Extrahera bara "text"-fältet ur JSON i Description_no
- Rensa _x000D_ och onödiga blankrader
- Exportera med kolumner: Id, Name, Text3
"""

import pandas as pd
import json
import re

df = pd.read_excel("Descriptions_NO_translated.xlsx")

def extract_text(raw):
    raw = str(raw).strip()
    # Försök JSON (dubbla citationstecken)
    try:
        obj = json.loads(raw)
        return obj.get("text", "")
    except Exception:
        pass
    # Försök single-quote dict (Python repr)
    try:
        import ast
        obj = ast.literal_eval(raw)
        if isinstance(obj, dict):
            return obj.get("text", "")
    except Exception:
        pass
    # Fallback: returnera som är
    return raw

def clean_html(text):
    if not text:
        return ""
    # Ta bort Excel-artefakter
    text = text.replace("_x000D_", "").replace("\r\n", "\n").replace("\r", "\n")
    # Ta bort upprepade blankrader / tomma <p>-taggar i rad
    text = re.sub(r'(<p>\s*<br>\s*</p>\s*)+', '', text)
    text = re.sub(r'(<p>\s*</p>\s*)+', '', text)
    text = text.strip()
    return text

df["Text3"] = df["Description_no"].apply(extract_text).apply(clean_html)

df_out = pd.DataFrame({
    "Id":    df["ID"],
    "Name":  df["Name_sv"],
    "Text3": df["Text3"],
})

out_file = "Descriptions_NO_clean.xlsx"
df_out.to_excel(out_file, index=False)
print(f"Sparat: {out_file} ({len(df_out)} rader)")

# Visa ett par exempel
print("\nExempel:")
for i, row in df_out.head(3).iterrows():
    print(f"\nId:    {row['Id']}")
    print(f"Name:  {row['Name']}")
    print(f"Text3: {row['Text3'][:200]}")
