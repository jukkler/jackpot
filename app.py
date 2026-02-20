import streamlit as st
import pandas as pd
import plotly.express as px
from itertools import combinations
from collections import Counter
import numpy as np
import random

# -----------------------------------------------------------------------------
# 1. KONFIGURATION & DATEN LADEN
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Eurojackpot Profi-Analyse", layout="wide", page_icon="🎰")

@st.cache_data
def load_data():
    """Lädt die Excel-Datei und sortiert die Zahlenreihen aufsteigend."""
    try:
        df = pd.read_excel("Alle_Eurojackpot_Zahlen.xlsx")
    except FileNotFoundError:
        return None, None
    
    # Spaltennamen definieren
    cols_50 = ['Zahl_1', 'Zahl_2', 'Zahl_3', 'Zahl_4', 'Zahl_5']
    
    # Sicherstellen, dass die Zahlen pro Ziehung aufsteigend sortiert sind (wichtig für Abstände)
    # Beispiel: Aus [45, 2, 10...] wird [2, 10, 45...]
    df[cols_50] = np.sort(df[cols_50].values, axis=1)
    
    return df, cols_50

# Daten laden
df, cols_50 = load_data()

# Fehlerbehandlung, falls Datei fehlt
if df is None:
    st.error("❌ Datei 'Alle_Eurojackpot_Zahlen.xlsx' nicht gefunden! Bitte führe zuerst das Python-Skript zum Erstellen der Daten aus.")
    st.stop()

# -----------------------------------------------------------------------------
# 2. HILFSFUNKTIONEN (CACHED FÜR PERFORMANCE)
# -----------------------------------------------------------------------------

@st.cache_data
def get_combinations(df, r):
    """Findet alle Paare (r=2) oder Drillinge (r=3) und zählt sie."""
    alle_kombis = []
    # Iteriere durch jede Ziehung
    for row in df[cols_50].values:
        alle_kombis.extend(list(combinations(row, r)))
    
    # Zählen
    counts = Counter(alle_kombis)
    
    # DataFrame erstellen
    df_kombi = pd.DataFrame(counts.items(), columns=['Kombination', 'Anzahl'])
    
    # Tuple in schönen String umwandeln: (5, 10) -> "5 - 10"
    df_kombi['Kombination'] = df_kombi['Kombination'].apply(lambda x: " - ".join(map(str, x)))
    
    return df_kombi.sort_values('Anzahl', ascending=False)

def generate_median_based_tip(df):
    """Generiert einen Tipp basierend auf medianen Abständen + Zufallsfaktor (Jitter)."""
    # 1. Mediane Abstände zwischen den Positionen berechnen (Zahl1->Zahl2, Zahl2->Zahl3...)
    median_diffs = []
    for i in range(4):
        col_a = cols_50[i]
        col_b = cols_50[i+1]
        diff = df[col_b] - df[col_a]
        median_diffs.append(int(diff.median()))
    
    # Versuchsschleife (falls Zahlen > 50 generiert werden, neu versuchen)
    for _ in range(100): 
        # Startzahl zufällig (1 bis 15), damit Platz nach oben bleibt
        current = random.randint(1, 15)
        nums = [current]
        
        valid = True
        for dist in median_diffs:
            # Jitter: Kleiner Zufallsfaktor (-2 bis +4), damit es nicht statisch ist
            jitter = random.randint(-2, 4)
            next_num = current + dist + jitter
            
            # Regeln: Muss <= 50 sein und größer als die vorherige Zahl
            if next_num > 50 or next_num <= current:
                valid = False
                break
            nums.append(next_num)
            current = next_num
            
        if valid and len(set(nums)) == 5:
            return nums, median_diffs
            
    return [0,0,0,0,0], median_diffs # Fallback

# -----------------------------------------------------------------------------
# 3. DAS DASHBOARD LAYOUT
# -----------------------------------------------------------------------------

st.title("🎰 Eurojackpot Analyse & Simulation")
st.markdown(f"Datenbasis: **{len(df)} Ziehungen** | *Analyse für Vorlesungs-Demo*")

# Tabs erstellen
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Häufigkeiten", 
    "📏 Abstände (Median)", 
    "🔗 Paare (2er)", 
    "🧩 Drillinge (3er)", 
    "🔮 Generatoren (Demo)"
])

# --- TAB 1: Häufigkeiten ---
with tab1:
    st.header("Welche Zahlen kommen am häufigsten?")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Hauptzahlen (5 aus 50)")
        # Alle Zahlen in eine lange Liste werfen und zählen
        main_counts = pd.Series(df[cols_50].values.flatten()).value_counts().reset_index()
        main_counts.columns = ['Zahl', 'Anzahl']
        
        fig = px.bar(main_counts, x='Zahl', y='Anzahl', color='Anzahl', 
                     color_continuous_scale='Blues', title="Verteilung 1-50")
        fig.update_layout(xaxis=dict(tickmode='linear', dtick=2)) # X-Achse lesbar machen
        st.plotly_chart(fig, use_container_width=True)
        
    with col2:
        st.subheader("Eurozahlen (2 aus 12)")
        euro_counts = pd.Series(df[['Euro_1', 'Euro_2']].values.flatten()).value_counts().reset_index()
        euro_counts.columns = ['Zahl', 'Anzahl']
        
        fig_euro = px.bar(euro_counts, x='Zahl', y='Anzahl', color='Anzahl', 
                          color_continuous_scale='Oranges', title="Verteilung Eurozahlen")
        fig_euro.update_layout(xaxis=dict(tickmode='linear', dtick=1))
        st.plotly_chart(fig_euro, use_container_width=True)

# --- TAB 2: Abstände ---
with tab2:
    st.header("Analyse der Abstände (Distanz zwischen Zahlen)")
    st.info("Hier untersuchen wir die Lücken zwischen den sortierten Zahlen einer Ziehung. Ist der Abstand zufällig oder gibt es Muster?")

    # DataFrame für Abstände bauen
    df_dist = df.copy()
    diff_cols = []
    for i in range(4):
        col_name = f'Abstand_{i+1}_{i+2}'
        diff_cols.append(col_name)
        df_dist[col_name] = df_dist[cols_50[i+1]] - df_dist[cols_50[i]]

    # Statistik Tabelle
    stats = df_dist[diff_cols].describe().T[['mean', '50%', 'min', 'max', 'std']]
    stats.columns = ['Durchschnitt', 'Median', 'Min', 'Max', 'Std.Abw.']
    
    col_d1, col_d2 = st.columns([1, 2])
    with col_d1:
        st.write("### Statistik")
        st.dataframe(stats)
        st.caption("Der Median ist hier oft aussagekräftiger als der Durchschnitt, da er weniger anfällig für Ausreißer ist.")
        
    with col_d2:
        st.write("### Verteilung (Boxplot)")
        fig_box = px.box(df_dist[diff_cols], title="Wie groß sind die Lücken normalerweise?")
        st.plotly_chart(fig_box, use_container_width=True)

# --- TAB 3: Paare ---
with tab3:
    st.header("Häufigste Zahlen-Paare")
    
    df_pairs = get_combinations(df, 2)
    
    col_p1, col_p2 = st.columns([2, 1])
    with col_p1:
        fig_pairs = px.bar(df_pairs.head(20), x='Kombination', y='Anzahl', 
                           title="Top 20 Paare", color='Anzahl', color_continuous_scale='Viridis')
        st.plotly_chart(fig_pairs, use_container_width=True)
    with col_p2:
        st.dataframe(df_pairs, use_container_width=True, height=500)

# --- TAB 4: Drillinge ---
with tab4:
    st.header("Häufigste 3er-Kombinationen")
    
    df_triplets = get_combinations(df, 3)
    
    col_t1, col_t2 = st.columns([2, 1])
    with col_t1:
        fig_triplets = px.bar(df_triplets.head(15), x='Kombination', y='Anzahl', 
                              title="Top 15 Drillinge", color='Anzahl', color_continuous_scale='Plasma')
        st.plotly_chart(fig_triplets, use_container_width=True)
    with col_t2:
        st.dataframe(df_triplets, use_container_width=True, height=500)

# --- TAB 5: Generatoren (DEMO) ---
with tab5:
    st.header("🔮 Vorlesungs-Demo: Generatoren")
    st.markdown("Drei Ansätze, um 'die nächsten Zahlen' vorherzusagen.")
    
    col_g1, col_g2, col_g3 = st.columns(3)
    
    # 1. Der Statistiker
    with col_g1:
        st.subheader("1. Der Statistiker")
        st.info("**Ansatz:** Wählt stur die Zahlen, die historisch am häufigsten fielen ('Hot Numbers').")
        
        if st.button("Erzeuge Statistik-Tipp"):
            # Häufigste 5 Zahlen
            all_nums = pd.Series(df[cols_50].values.flatten()).value_counts()
            top_5 = sorted(all_nums.head(5).index.tolist())
            
            # Häufigste 2 Eurozahlen
            all_euros = pd.Series(df[['Euro_1', 'Euro_2']].values.flatten()).value_counts()
            top_2_euro = sorted(all_euros.head(2).index.tolist())
            
            st.success(f"🎱 {top_5}")
            st.warning(f"🇪🇺 {top_2_euro}")
            st.caption("Hinweis: Diese Zahlen ändern sich fast nie, da sich die Langzeit-Statistik nur sehr langsam bewegt.")

    # 2. Der Zufall
    with col_g2:
        st.subheader("2. Der Zufall")
        st.info("**Ansatz:** Völliges Chaos. Ignoriert die Vergangenheit komplett (Laplace-Experiment).")
        
        if st.button("Erzeuge Zufalls-Tipp"):
            rand_5 = sorted(random.sample(range(1, 51), 5))
            rand_2 = sorted(random.sample(range(1, 13), 2))
            
            st.success(f"🎲 {rand_5}")
            st.warning(f"🇪🇺 {rand_2}")
            st.caption("Jede Zahl hat exakt die gleiche Chance.")

    # 3. Median Abweichung
    with col_g3:
        st.subheader("3. Der Smart-Bot")
        st.info("**Ansatz:** Simuliert die *Struktur* einer typischen Ziehung basierend auf Median-Abständen + Jitter.")
        
        if st.button("Erzeuge Smart-Tipp"):
            smart_5, median_refs = generate_median_based_tip(df)
            rand_2 = sorted(random.sample(range(1, 13), 2)) # Eurozahlen bleiben zufällig
            
            st.success(f"🤖 {smart_5}")
            st.warning(f"🇪🇺 {rand_2}")
            
            # Erklärung anzeigen
            diffs_current = [smart_5[i+1]-smart_5[i] for i in range(4)]
            st.markdown(f"**Analyse dieses Tipps:**")
            st.code(f"Abstände Generiert: {diffs_current}\nAbstände Historisch (Median): {median_refs}")
            st.caption("Der Bot versucht, die historischen Abstände grob einzuhalten, variiert aber leicht.")