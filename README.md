# briefing-kurse

Schlusskurse der Beobachtungsliste für das Morning Briefing (SIX, Xetra, London, Tokio, USA).

- Läuft täglich um 02:30 UTC (06:30 Tiflis) als GitHub Action, manuell über „Run workflow“.
- `kurse.csv`: aktueller Stand, eine Zeile je Ticker (Spalten: ticker, datum, kurs, vortag, tag_prozent, waehrung, quelle, abgerufen_utc). Das Briefing liest
  `https://raw.githubusercontent.com/kieselstark/briefing-kurse/main/kurse.csv`.
- `historie.csv`: fortlaufende Historie.
- Quelle Yahoo Finance; für London-Titel ersatzweise Alpha Vantage, falls das Secret `ALPHAVANTAGE_API_KEY` gesetzt ist.
- Ticker ändern: Liste `TICKER` in `kurse_holen.py`.
