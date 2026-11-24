"""Holt den letzten verfügbaren Kurs der Briefing-Beobachtungsliste und schreibt sie als CSV.

kurse.csv     aktueller Stand (eine Zeile je Ticker), wird vom Morning Briefing gelesen
historie.csv  fortlaufende Historie (ticker + datum eindeutig)

Quelle 1: Yahoo Finance (yfinance). Quelle 2 (nur London, optional): Alpha Vantage,
Schlüssel aus der Umgebungsvariable ALPHAVANTAGE_API_KEY (GitHub Secret).
"""

import csv
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import yfinance as yf

TICKER = [
    "SPISI.SW", "VONN.SW", "SQN.SW", "NUCL.SW", "CSSMI.SW", "BCOM.SW", "CCUSAS.SW",
    "RRU.DE",
    "BGEO.L",
    "3350.T",
    "HIVE", "TSLA",
]

FELDER = ["ticker", "datum", "kurs", "vortag", "tag_prozent", "waehrung", "quelle", "abgerufen_utc"]
HIER = Path(__file__).parent
JETZT = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


SCHLUSS = {".SW": ("Europe/Zurich", 17, 35), ".DE": ("Europe/Berlin", 17, 35),
           ".L": ("Europe/London", 16, 40), ".T": ("Asia/Tokyo", 15, 35)}
US = ("America/New_York", 16, 5)  # Ticker ohne Börsenendung


def ist_offen(ticker, bar_zeit):
    """True, wenn der letzte Bar vom heutigen Börsentag stammt und der Schluss noch nicht erreicht ist."""
    regel = next((r for e, r in SCHLUSS.items() if ticker.endswith(e)), None)
    if regel is None:
        if "." in ticker:
            return False
        regel = US
    zone, std, minute = regel
    jetzt = datetime.now(ZoneInfo(zone))
    schluss = jetzt.replace(hour=std, minute=minute, second=0, microsecond=0)
    return bar_zeit.tz_convert(zone).date() == jetzt.date() and jetzt < schluss


def von_yahoo(ticker):
    t = yf.Ticker(ticker)
    h = t.history(period="15d", interval="1d", auto_adjust=False)
    # Letzter verfügbarer Kurs zählt, auch während die Börse offen ist (kein offizieller Schluss nötig).
    # Yahoo liefert manchmal einen Tagesbalken mit Umsatz, aber ohne Kurs: dann den letzten
    # Stundenkurs dieses Tages einsetzen.
    leer = h["Close"].isna() & (h["Volume"] > 0)
    if leer.any():
        stunde = t.history(period="15d", interval="1h", auto_adjust=False).dropna(subset=["Close"])
        for tag in h.index[leer]:
            s = stunde[stunde.index.tz_convert(tag.tz).date == tag.date()]
            if len(s):
                h.loc[tag, "Close"] = s["Close"].iloc[-1]
    h = h.dropna(subset=["Close"])
    if len(h) < 2:
        return None
    try:
        waehrung = t.fast_info.get("currency") or ""
    except Exception:
        waehrung = ""
    letzt, vor = h.iloc[-1], h.iloc[-2]
    return {
        "datum": h.index[-1].strftime("%Y-%m-%d"),
        "kurs": float(letzt["Close"]),
        "vortag": float(vor["Close"]),
        "waehrung": waehrung,
        "quelle": "yahoo",
    }


def von_alphavantage(ticker):
    schluessel = os.environ.get("ALPHAVANTAGE_API_KEY")
    if not schluessel or not ticker.endswith(".L"):
        return None
    symbol = ticker[:-2] + ".LON"
    url = ("https://www.alphavantage.co/query?function=TIME_SERIES_DAILY"
           f"&symbol={symbol}&apikey={schluessel}")
    with urllib.request.urlopen(url, timeout=30) as r:
        daten = json.load(r)
    reihe = daten.get("Time Series (Daily)") or {}
    tage = sorted(reihe)
    if len(tage) < 2:
        return None
    return {
        "datum": tage[-1],
        "kurs": float(reihe[tage[-1]]["4. close"]),
        "vortag": float(reihe[tage[-2]]["4. close"]),
        "waehrung": "",
        "quelle": "alphavantage",
    }


def main():
    zeilen = []
    for ticker in TICKER:
        wert = None
        for quelle in (von_yahoo, von_alphavantage):
            try:
                wert = quelle(ticker)
            except Exception as fehler:
                print(f"{ticker}: {quelle.__name__} fehlgeschlagen: {fehler}")
            if wert:
                break
        if not wert:
            print(f"{ticker}: kein Kurs")
            continue
        wert["tag_prozent"] = round((wert["kurs"] / wert["vortag"] - 1) * 100, 2)
        wert["kurs"] = round(wert["kurs"], 4)
        wert["vortag"] = round(wert["vortag"], 4)
        zeilen.append({"ticker": ticker, "abgerufen_utc": JETZT, **wert})
        print(f"{ticker}: {wert['datum']} {wert['kurs']} {wert['tag_prozent']} % ({wert['quelle']})")

    if not zeilen:
        raise SystemExit("Keine Kurse erhalten, Dateien bleiben unverändert.")

    with open(HIER / "kurse.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FELDER)
        w.writeheader()
        w.writerows(zeilen)

    historie = HIER / "historie.csv"
    alt = {}
    if historie.exists():
        with open(historie, newline="") as f:
            for z in csv.DictReader(f):
                alt[(z["ticker"], z["datum"])] = z
    for z in zeilen:
        alt[(z["ticker"], z["datum"])] = z
    with open(historie, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FELDER)
        w.writeheader()
        w.writerows(sorted(alt.values(), key=lambda z: (z["datum"], z["ticker"])))


if __name__ == "__main__":
    main()
