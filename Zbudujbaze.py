import pandas as pd
import sqlite3

FOLDER = r"C:\Users\grzeg\PyCharmMiscProject"

arkusze = pd.read_excel(FOLDER + r"\Grafik__anonimowy.xlsx", sheet_name=None, header=1)

godziny = {"R": 8, "P": 8, "X": 12, "16/": 6, "/16": 6, "R/P": 16, "18/22": 4, "14/18": 4}

wszystkie = []
for nazwa, tabela in arkusze.items():
    tabela = tabela.rename(columns={"Unnamed: 0": "lp", "Unnamed: 1": "pracownik", "Unnamed: 2": "kierownik"})
    tabela = tabela[(tabela["pracownik"].notna()) & (tabela["pracownik"] != "LEGENDA")]
    dlugi = tabela.melt(id_vars=["lp", "pracownik", "kierownik"], var_name="dzien", value_name="kod")
    dlugi = dlugi[dlugi["kod"].notna()]
    dlugi["miesiac"] = nazwa
    wszystkie.append(dlugi)

grafik = pd.concat(wszystkie, ignore_index=True)
grafik = grafik[~grafik["kod"].isin(["X+", "+/16"])]

# NOWE: anonimizacja, każda osoba dostaje stały numer
nazwiska = grafik["pracownik"].unique()
nowe = {n: f"Pracownik {i:02d}" for i, n in enumerate(nazwiska, start=1)}
grafik["pracownik"] = grafik["pracownik"].map(nowe)

zmiany = pd.DataFrame(list(godziny.items()), columns=["kod", "godziny"])
pracownicy = grafik[["pracownik", "kierownik"]].drop_duplicates("pracownik")

con = sqlite3.connect(FOLDER + r"\grafik_anonim.db")   # NOWE: osobna baza, prawdziwa zostaje
grafik[["pracownik", "miesiac", "dzien", "kod"]].to_sql("grafik", con, if_exists="replace", index=False)
zmiany.to_sql("zmiany", con, if_exists="replace", index=False)
pracownicy.to_sql("pracownicy", con, if_exists="replace", index=False)
con.close()
print("Gotowe, zmian w bazie:", len(grafik))