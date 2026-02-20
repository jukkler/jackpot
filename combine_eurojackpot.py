import pandas as pd
import os

# Liste deiner Dateien (Pass die Namen ggf. an)
dateien = ['EJ_bis_2021.xlsx', 'EJ_ab_2022.xlsx'] 
alle_zahlen = []

for datei_name in dateien:
    if not os.path.exists(datei_name):
        print(f"Überspringe: '{datei_name}' nicht gefunden.")
        continue

    print(f"Lese Datei: {datei_name}...")
    xls = pd.ExcelFile(datei_name)

    for blatt_name in xls.sheet_names:
        # Wir lesen erstmal nur die erste Zelle, um das Layout zu checken
        test_df = pd.read_excel(xls, sheet_name=blatt_name, nrows=1, header=None)
        erste_zelle = str(test_df.iloc[0, 0])
        
        nur_zahlen = pd.DataFrame()

        # ---------------------------------------------------------
        # FALL A: Das NEUE Format (Dein 2. Bild)
        # Erkennungsmerkmal: Zelle A1 enthält "Datum"
        # ---------------------------------------------------------
        if "Datum" in erste_zelle:
            print(f"  -> Erkenne NEUES Format in Blatt '{blatt_name}'")
            # Header ist in Zeile 0 (Standard), Daten ab Zeile 1
            df = pd.read_excel(xls, sheet_name=blatt_name)
            
            # Zahlen sind in Spalten B bis H (Index 1 bis 8 exklusiv)
            nur_zahlen = df.iloc[:, 1:8]

        # ---------------------------------------------------------
        # FALL B: Das ALTE Format (Dein 1. Bild)
        # Erkennungsmerkmal: Zelle A1 ist "Eurojackpot" oder leer/anders
        # ---------------------------------------------------------
        else:
            print(f"  -> Erkenne ALTES Format in Blatt '{blatt_name}'")
            # Wir müssen 7 Zeilen Header überspringen
            df = pd.read_excel(xls, sheet_name=blatt_name, skiprows=7, header=None)
            
            # Zahlen sind in Spalten D bis J (Index 3 bis 10 exklusiv)
            nur_zahlen = df.iloc[:, 3:10]

        # ---------------------------------------------------------
        # Gemeinsame Reinigung für beide Formate
        # ---------------------------------------------------------
        # Spalten einheitlich benennen
        if nur_zahlen.shape[1] == 7: # Sicherheitscheck: Haben wir 7 Spalten?
            nur_zahlen.columns = ['Zahl_1', 'Zahl_2', 'Zahl_3', 'Zahl_4', 'Zahl_5', 'Euro_1', 'Euro_2']
            
            # Alles zu Zahlen machen und Leeres löschen
            for col in nur_zahlen.columns:
                nur_zahlen[col] = pd.to_numeric(nur_zahlen[col], errors='coerce')
            
            nur_zahlen = nur_zahlen.dropna()
            
            # Zur großen Liste hinzufügen
            alle_zahlen.append(nur_zahlen)
        else:
            print(f"  Warnung: Konnte Spalten in '{blatt_name}' nicht korrekt zuordnen.")

# Alles zusammenfügen
if alle_zahlen:
    df_gesamt = pd.concat(alle_zahlen, ignore_index=True)
    print("\nFertig! Alle Zahlen kombiniert.")
    print(df_gesamt.tail()) # Zeigt die letzten Einträge (aus der neuen Datei)
    
    # Speichern
    df_gesamt.to_excel("Alle_Eurojackpot_Zahlen.xlsx", index=False)
else:
    print("Keine Daten gefunden.")