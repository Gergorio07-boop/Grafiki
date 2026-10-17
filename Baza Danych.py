import pandas as pd
import sqlite3
import matplotlib.pyplot as plt

pd.set_option("display.max_rows", None)
pd.set_option("display.max_columns", None)
pd.set_option("display.expand_frame_repr", False)

con = sqlite3.connect(r"C:\Users\grzeg\PyCharmMiscProject\grafik_anonim.db")
STAWKA = 30.50                       # zł netto za godzinę


# 1. Ranking: suma godzin każdego pracownika, od największej
def ranking():
    zapytanie = """
    SELECT g.pracownik, SUM(z.godziny) AS suma_godzin
    FROM grafik AS g
    JOIN zmiany AS z ON g.kod = z.kod
    GROUP BY g.pracownik
    ORDER BY suma_godzin DESC
    """
    return pd.read_sql(zapytanie, con)


# 2. Statystyki jednego pracownika + wynagrodzenie
def pracownik(fragment):
    # podsumowanie z całego okresu
    podsumowanie = """
    SELECT g.pracownik,
           COUNT(*) AS liczba_zmian,
           SUM(z.godziny) AS suma_godzin,
           ROUND(SUM(z.godziny) * ?, 2) AS wynagrodzenie_netto
    FROM grafik AS g
    JOIN zmiany AS z ON g.kod = z.kod
    WHERE g.pracownik LIKE ?
    GROUP BY g.pracownik
    """
    # to samo, ale osobno dla każdego miesiąca
    miesiecznie = """
    SELECT g.pracownik, g.miesiac,
           COUNT(*) AS liczba_zmian,
           SUM(z.godziny) AS suma_godzin,
           ROUND(SUM(z.godziny) * ?, 2) AS wynagrodzenie_netto
    FROM grafik AS g
    JOIN zmiany AS z ON g.kod = z.kod
    WHERE g.pracownik LIKE ?
    GROUP BY g.pracownik, g.miesiac
    """
    parametry = (STAWKA, f"%{fragment}%")
    print(pd.read_sql(podsumowanie, con, params=parametry))
    print()
    print(pd.read_sql(miesiecznie, con, params=parametry))


# 3. Ranking godzin w jednym miesiącu
def miesiac(nazwa):
    zapytanie = """
    SELECT g.pracownik, SUM(z.godziny) AS suma_godzin
    FROM grafik AS g
    JOIN zmiany AS z ON g.kod = z.kod
    WHERE g.miesiac LIKE ?
    GROUP BY g.pracownik
    ORDER BY suma_godzin DESC
    """
    return pd.read_sql(zapytanie, con, params=(f"%{nazwa}%",))


# pomocnicza: jakie miesiące są w bazie
def miesiace():
    return pd.read_sql("SELECT DISTINCT miesiac FROM grafik", con)


# 4. Lista alfabetyczna po nazwisku (nazwisko jest pierwsze w kolumnie pracownik)
def alfabetycznie():
    zapytanie = """
    SELECT g.pracownik, SUM(z.godziny) AS suma_godzin
    FROM grafik AS g
    JOIN zmiany AS z ON g.kod = z.kod
    GROUP BY g.pracownik
    ORDER BY g.pracownik
    """
    return pd.read_sql(zapytanie, con)


def wykres_top10():
    dane = ranking().head(10)                  # 10 pierwszych z rankingu
    dane = dane.sort_values("suma_godzin")     # od najmniejszej, żeby największy był na górze
    plt.figure(figsize=(9, 5))
    plt.barh(dane["pracownik"], dane["suma_godzin"])
    plt.xlabel("Suma godzin")
    plt.title("Top 10 pracowników według godzin w okresie Wrzesień 2025-2026")
    plt.tight_layout()
    plt.show()

def wykres_pracownicy(nazwiska):
        zapytanie = """
        SELECT g.miesiac, SUM(z.godziny) AS suma_godzin
        FROM grafik AS g
        JOIN zmiany AS z ON g.kod = z.kod
        WHERE g.pracownik LIKE ?
        GROUP BY g.miesiac
        """
        kolejnosc = miesiace()["miesiac"].tolist()  # miesiące w kolejności z Excela
        plt.figure(figsize=(10, 5))
        for nazwisko in nazwiska:
            dane = pd.read_sql(zapytanie, con, params=(f"%{nazwisko}%",))
            dane = dane.set_index("miesiac").reindex(kolejnosc, fill_value=0)
            plt.plot(dane.index, dane["suma_godzin"], marker="o", label=nazwisko)
        plt.ylabel("Suma godzin")
        plt.title("Godziny w miesiącu")
        plt.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()


# pomocnicza: ustawia wiersze w kolejności miesięcy z Excela, a nie alfabetycznie
def po_kolei(dane):
    kolejnosc = miesiace()["miesiac"].tolist()
    return dane.set_index("miesiac").reindex(kolejnosc).reset_index()


# pomocnicza: polskie nazwy miesięcy zamienione na numery (potrzebne do dat)
MIESIACE_PL = {"Styczeń": 1, "Luty": 2, "Marzec": 3, "Kwiecień": 4,
               "Maj": 5, "Czerwiec": 6, "Lipiec": 7, "Sierpień": 8,
               "Wrzesień": 9, "Październik": 10, "Listopad": 11, "Grudzień": 12}


# ---------------------------------------------------------------------
# 1. Koszt pracy w każdym miesiącu
# ---------------------------------------------------------------------
def koszt_miesiecznie():
    zapytanie = """
    SELECT g.miesiac,
           SUM(z.godziny) AS suma_godzin,
           ROUND(SUM(z.godziny) * ?, 2) AS koszt_netto
    FROM grafik AS g
    JOIN zmiany AS z ON g.kod = z.kod
    GROUP BY g.miesiac
    """
    dane = pd.read_sql(zapytanie, con, params=(STAWKA,))
    return po_kolei(dane)


def wykres_koszt():
    dane = koszt_miesiecznie()
    plt.figure(figsize=(10, 5))
    plt.bar(dane["miesiac"], dane["koszt_netto"])
    plt.ylabel("Koszt netto [zł]")
    plt.title(f"Koszt pracy w miesiącu (stawka {STAWKA} zł/h)")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


# ---------------------------------------------------------------------
# 2. Kierownicy kontra reszta
# ---------------------------------------------------------------------
def kierownicy_vs_reszta():
    zapytanie = """
    SELECT CASE WHEN p.kierownik IS NOT NULL THEN 'kierownicy' ELSE 'reszta' END AS grupa,
           COUNT(DISTINCT s.pracownik) AS liczba_osob,
           ROUND(AVG(s.godziny_w_miesiacu), 1) AS srednio_godzin_w_miesiacu
    FROM (
        SELECT g.pracownik, g.miesiac, SUM(z.godziny) AS godziny_w_miesiacu
        FROM grafik AS g
        JOIN zmiany AS z ON g.kod = z.kod
        GROUP BY g.pracownik, g.miesiac
    ) AS s
    JOIN pracownicy AS p ON s.pracownik = p.pracownik
    GROUP BY grupa
    """
    return pd.read_sql(zapytanie, con)


def wykres_kierownicy():
    dane = kierownicy_vs_reszta()
    plt.figure(figsize=(6, 5))
    plt.bar(dane["grupa"], dane["srednio_godzin_w_miesiacu"])
    plt.ylabel("Średnio godzin w miesiącu na osobę")
    plt.title("Kierownicy kontra reszta")
    plt.tight_layout()
    plt.show()


# ---------------------------------------------------------------------
# 3. Rodzaje zmian: kto robi ile R, P, X
# ---------------------------------------------------------------------
def rodzaje_zmian():
    zapytanie = """
    SELECT pracownik,
           SUM(CASE WHEN kod = 'R' THEN 1 ELSE 0 END) AS R,
           SUM(CASE WHEN kod = 'P' THEN 1 ELSE 0 END) AS P,
           SUM(CASE WHEN kod = 'X' THEN 1 ELSE 0 END) AS X,
           SUM(CASE WHEN kod NOT IN ('R', 'P', 'X') THEN 1 ELSE 0 END) AS inne,
           COUNT(*) AS wszystkie
    FROM grafik
    GROUP BY pracownik
    ORDER BY X DESC
    """
    return pd.read_sql(zapytanie, con)


def wykres_rodzaje_zmian():
    dane = rodzaje_zmian().sort_values("wszystkie").tail(10)  # 10 osób z największą liczbą zmian
    dane = dane.set_index("pracownik")[["R", "P", "X", "inne"]]
    dane.plot(kind="barh", stacked=True, figsize=(10, 6))
    plt.xlabel("Liczba zmian")
    plt.ylabel("")
    plt.legend(bbox_to_anchor=(1.01, 1), loc="upper left")  # legenda obok wykresu, nie na słupkach
    plt.title("Rodzaje zmian: 10 osób z największą liczbą zmian")
    plt.tight_layout()
    plt.show()


# ---------------------------------------------------------------------
# 5. Weekendy
# ---------------------------------------------------------------------
def z_datami():
    zapytanie = """
    SELECT g.pracownik, g.miesiac, g.dzien, g.kod, z.godziny
    FROM grafik AS g
    JOIN zmiany AS z ON g.kod = z.kod
    """
    dane = pd.read_sql(zapytanie, con)
    nazwa = dane["miesiac"].str.split().str[0]  # "Wrzesień 2026" -> "Wrzesień"
    rok = dane["miesiac"].str.split().str[-1]  # "Wrzesień 2026" -> "2026"
    daty = pd.DataFrame({"year": pd.to_numeric(rok),
                         "month": nazwa.map(MIESIACE_PL),
                         "day": pd.to_numeric(dane["dzien"])})
    dane["data"] = pd.to_datetime(daty, errors="coerce")
    dane["dzien_tygodnia"] = dane["data"].dt.dayofweek  # 0 = poniedziałek ... 6 = niedziela
    bledne = dane["data"].isna().sum()
    if bledne > 0:
        print(f"Uwaga: {bledne} wierszy bez daty, sprawdź nazwy miesięcy i dni")
    return dane


def weekendy():
    dane = z_datami()
    weekend = dane[dane["dzien_tygodnia"] >= 5]  # 5 = sobota, 6 = niedziela
    wynik = weekend.groupby("pracownik").agg(
        zmiany_weekendowe=("kod", "count"),
        godziny_weekendowe=("godziny", "sum"))
    return wynik.sort_values("zmiany_weekendowe", ascending=False).reset_index()


def wykres_weekendy():
    dane = weekendy().head(10).sort_values("zmiany_weekendowe")
    plt.figure(figsize=(9, 5))
    plt.barh(dane["pracownik"], dane["zmiany_weekendowe"])
    plt.xlabel("Liczba zmian w soboty i niedziele")
    plt.title("Top 10: praca w weekendy")
    plt.tight_layout()
    plt.show()



# ---------------------------------------------------------------------
# 6. Raport do Excela: wszystko w jednym pliku, każdy wynik w osobnym arkuszu
# ---------------------------------------------------------------------
def raport_excel(plik="raport_grafik.xlsx"):
    with pd.ExcelWriter(plik) as writer:
        ranking().to_excel(writer, sheet_name="Ranking", index=False)
        koszt_miesiecznie().to_excel(writer, sheet_name="Koszt", index=False)
        kierownicy_vs_reszta().to_excel(writer, sheet_name="Kierownicy", index=False)
        rodzaje_zmian().to_excel(writer, sheet_name="Rodzaje zmian", index=False)
        weekendy().to_excel(writer, sheet_name="Weekendy", index=False)

    print(f"Zapisano plik {plik}")





print("Dostępne komendy:")
print('  ranking()                 - suma godzin, od największej')
print('  pracownik("Witkowski")    - statystyki i wynagrodzenie jednej osoby')
print('  miesiace()                - jakie miesiące są w bazie')
print('  miesiac("Wrzesień")       - ranking godzin w danym miesiącu')
print('  alfabetycznie()           - lista po nazwisku A-Z')
print('  wykres_top10()            - wykres słupkowy top 10 pracowników')
print('  wykres_pracownicy(["Witkowski", "Zawadzki"]) - wykres liniowy pracowników')
print('  koszt_miesiecznie()       - koszt pracy w każdym miesiącu')
print('  kierownicy_vs_reszta()    - średnie godziny: kierownicy i reszta')
print('  rodzaje_zmian()           - ile R, P, X ma każda osoba')
print('  weekendy()                - kto najczęściej pracuje w weekendy')
print('  raport_excel()            - wszystko do jednego pliku .xlsx')
print('  wykres_koszt(), wykres_kierownicy(), wykres_rodzaje_zmian(),')
print('  wykres_weekendy(), wykres_nadgodziny()  - wykresy')
