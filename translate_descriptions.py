#!/usr/bin/env python3
"""
Translate Description_no EJ_ÖVERSATT rows from Swedish to Norwegian.
Runs in batches of 25, saves checkpoint after each batch.
"""

import pandas as pd
import anthropic
import json
import os
import time
import sys

CHECKPOINT_FILE = "translation_checkpoint.json"
OUTPUT_FILE = "Descriptions_NO_translated.xlsx"
BATCH_SIZE = 10
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

client = anthropic.Anthropic(api_key=API_KEY or None)

# ── Load source data ──────────────────────────────────────────────────────────
print("Läser källfil...")
df = pd.read_excel("Produkter-SV-NO.xlsx")

desc_no_missing = df["Description_no"].isna() | (df["Description_no"].astype(str).str.strip() == "")
desc_same = (~desc_no_missing) & (
    df["Description_no"].astype(str).str.strip() == df["Description_sv"].astype(str).str.strip()
)

to_translate = df[desc_same][["ID", "Name_sv", "Description_sv"]].copy().reset_index(drop=True)
print(f"Rader att översätta: {len(to_translate)}")

# ── Load checkpoint ───────────────────────────────────────────────────────────
if os.path.exists(CHECKPOINT_FILE):
    with open(CHECKPOINT_FILE) as f:
        checkpoint = json.load(f)
    translations = checkpoint.get("translations", {})  # id -> translated_text
    print(f"Återupptar från checkpoint: {len(translations)} redan klara")
else:
    translations = {}

# ── Batch translation ─────────────────────────────────────────────────────────
def translate_batch(rows):
    """rows: list of dicts with keys id, name_sv, desc_sv"""
    items_json = json.dumps(
        [{"n": r["i"], "name": r["name_sv"], "text": r["desc_sv"]} for r in rows],
        ensure_ascii=False
    )
    prompt = f"""Du är en professionell översättare specialiserad på ATV, UTV, motorsport och terrängfordon.

Översätt följande svenska produktbeskrivningar till norska (bokmål).

Regler:
- Bevara ALL HTML-formatering exakt (taggar, attribut, entiteter som &amp;)
- Översätt ENBART texten inuti taggarna, inte taggarna själva
- Tekniska termer, produktnamn, artikelnummer och märkesnamn ska INTE översättas
- Måttenheter, modellbeteckningar och specifikationer behålls oförändrade
- Returnera ett JSON-objekt med samma "n"-nycklar som input, och det översatta värdet

Input (JSON-array):
{items_json}

Svar: returnera ENBART ett JSON-objekt, t.ex. {{"1":"översatt text","2":"översatt text"}}"""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=16000,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = response.content[0].text.strip()

    # Strip markdown code block if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    result = json.loads(raw)
    # Ibland returnerar modellen en array av objekt – normalisera till dict
    if isinstance(result, list):
        normalized = {}
        for item in result:
            if isinstance(item, dict):
                # Försök hitta n/id-nyckel och text/translation-nyckel
                n = str(item.get("n", item.get("id", item.get("ID", ""))))
                text = item.get("text", item.get("translation", item.get("translated", "")))
                if n and text:
                    normalized[n] = text
        result = normalized
    return result

# Filter out already done
remaining = to_translate[~to_translate["ID"].astype(str).isin(translations.keys())].copy()
total = len(to_translate)
done = total - len(remaining)
print(f"Återstår: {len(remaining)} rader\n")

errors = []

for batch_start in range(0, len(remaining), BATCH_SIZE):
    batch = remaining.iloc[batch_start : batch_start + BATCH_SIZE]
    rows = [
        {"i": str(row["ID"]), "name_sv": str(row["Name_sv"]), "desc_sv": str(row["Description_sv"])}
        for _, row in batch.iterrows()
    ]

    batch_num = batch_start // BATCH_SIZE + 1
    total_batches = (len(remaining) + BATCH_SIZE - 1) // BATCH_SIZE
    pct = (done + batch_start + len(batch)) / total * 100
    print(f"Batch {batch_num}/{total_batches} | {done+batch_start+len(batch)}/{total} ({pct:.1f}%)...", end=" ", flush=True)

    for attempt in range(4):
        try:
            result = translate_batch(rows)
            # Store results
            for row_id_str, translated in result.items():
                translations[row_id_str] = translated
            # Save checkpoint
            with open(CHECKPOINT_FILE, "w") as f:
                json.dump({"translations": translations}, f, ensure_ascii=False)
            print("OK")
            time.sleep(2)   # paus för att hålla sig under rate limit
            break
        except anthropic.RateLimitError:
            wait = 60 * (attempt + 1)
            print(f"Rate limit, väntar {wait}s...", end=" ", flush=True)
            time.sleep(wait)
        except Exception as e:
            wait = 5 * (attempt + 1)
            print(f"Fel ({type(e).__name__}: {str(e)[:80]}), väntar {wait}s...", end=" ", flush=True)
            if attempt == 3:
                print("MISSLYCKADES – hoppar över batch")
                errors.append({"batch_start": batch_start, "error": str(e)})
            time.sleep(wait)

# ── Build output ──────────────────────────────────────────────────────────────
print(f"\nBygger resultatfil...")
print(f"Lyckade översättningar: {len(translations)}")
print(f"Misslyckade batcher:    {len(errors)}")

# Create output df: only translated rows, keep ID + Name_sv + translated Description_no
result_rows = []
for _, row in to_translate.iterrows():
    id_str = str(row["ID"])
    if id_str in translations:
        result_rows.append({
            "ID": row["ID"],
            "Name_sv": row["Name_sv"],
            "Description_no": translations[id_str],
        })

df_out = pd.DataFrame(result_rows)
df_out.to_excel(OUTPUT_FILE, index=False)
print(f"Sparat: {OUTPUT_FILE} ({len(df_out)} rader)")

if errors:
    print(f"\nFel i följande batcher (batch_start-index): {[e['batch_start'] for e in errors]}")
    print("Kör skriptet igen för att försöka om misslyckade batcher.")
