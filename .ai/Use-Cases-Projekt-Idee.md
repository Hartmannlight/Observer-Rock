Sehr gute Idee.
**Use-Cases sauber zu formulieren ist extrem wichtig**, weil sie später die Architektur validieren: Wenn ein Use-Case nur mit Hacks möglich ist, stimmt die Architektur nicht.

Ich formuliere die Use Cases bewusst **technikneutral** (fachlich), und erst danach implizit, welche Komponenten des Frameworks dafür gebraucht werden.

---

# 1. Use Case: Neues Gemeinderatsprotokoll entdecken und archivieren

## Ziel

Das System erkennt automatisch neue Gemeinderatsprotokolle, lädt sie herunter und speichert sie dauerhaft.

## Ablauf

1. Scheduler startet Monitor `gemeinderat_pfinztal`.
2. Source-Plugin durchsucht das Ratsportal.
3. Neue Einträge werden identifiziert (z. B. anhand Datum oder URL).
4. Für jedes neue Dokument:

   * PDF herunterladen
   * Hash berechnen
   * speichern
5. Dokument wird im Repository registriert.

## Ergebnis

* PDF im Archiv gespeichert
* Metadaten in DB gespeichert
* Versionierung vorhanden

## Wert

* vollständiges Archiv
* keine manuelle Suche
* reproduzierbare Quelle

## Benötigte Komponenten

* SourcePlugin
* FetchPlugin
* ArtifactStore
* DocumentRepository
* Deduplication

---

# 2. Use Case: Protokoll automatisch zusammenfassen

## Ziel

Zu jedem neuen Protokoll soll automatisch eine strukturierte Zusammenfassung erstellt werden.

## Ablauf

1. Dokument wird erkannt.
2. Text wird aus PDF extrahiert.
3. Analyseprofil `meeting_summary` wird ausgeführt.
4. LLM erhält den Text und ein Prompt-Template.
5. LLM liefert strukturiertes JSON:

```json
{
  "date": "2026-03-11",
  "participants": ["..."],
  "topics": [
    {
      "title": "Bebauungsplan Hauptstraße",
      "summary": "..."
    }
  ]
}
```

6. JSON wird validiert (Pydantic).
7. Ergebnis wird gespeichert.

## Ergebnis

* strukturierte JSON-Zusammenfassung
* später durchsuchbar

## Wert

* schneller Überblick
* maschinenlesbare Daten
* Grundlage für spätere Analysen

## Benötigte Komponenten

* Normalizer
* AnalysisPlugin
* SchemaValidator
* ArtifactStore

---

# 3. Use Case: Relevante Themen erkennen und Alarm auslösen

## Ziel

Wenn im Protokoll ein bestimmtes Thema vorkommt (z. B. Hauptstraße), soll eine Discord-Benachrichtigung mit Ping erfolgen.

## Ablauf

1. Analyse `street_mentions` wird ausgeführt.
2. LLM extrahiert alle erwähnten Straßennamen.
3. Regel-Engine prüft:

```
if mention == "Hauptstraße"
```

4. Renderer erzeugt Discord-Nachricht.
5. DiscordNotifier sendet Nachricht mit Ping.

## Beispielnachricht

```
⚠️ Gemeinderat erwähnt Hauptstraße

Kontext:
Sanierung der Hauptstraße wird beschlossen.

Datum:
11.03.2026
```

## Ergebnis

* sofortige Benachrichtigung

## Wert

* relevante Themen werden nicht übersehen

## Benötigte Komponenten

* AnalysisPlugin
* RuleEngine
* Renderer
* Notifier

---

# 4. Use Case: Sitzungsübersicht automatisch posten

## Ziel

Für jede Sitzung wird automatisch eine Übersicht gepostet.

## Ablauf

1. Analyse `meeting_summary`.
2. Renderer `toc_digest`.
3. Discord-Nachricht ohne Ping:

```
Gemeinderat Pfinztal – Sitzung 11.03.2026

TOP 1 Haushaltsplanung
TOP 2 Verkehrskonzept Hauptstraße
TOP 3 Bebauungsplan Blumenstraße
```

## Ergebnis

* regelmäßiger Überblick

## Wert

* leichter Überblick über Themen

---

# 5. Use Case: Archiv durchsuchen

## Ziel

Der Nutzer möchte später Fragen stellen wie:

> „Zeige alle Protokolle, in denen Blumenstraße erwähnt wurde.“

## Ablauf

1. QueryEngine durchsucht Analysis-Resultate.
2. Treffer werden aufgelistet.

## Beispieloutput

```
Blumenstraße erwähnt in:

- Gemeinderat 11.03.2026
- Gemeinderat 14.01.2026
- Gemeinderat 18.11.2025
```

## Ergebnis

* schnelle Recherche

## Wert

* langfristige Wissensdatenbank

## Benötigte Komponenten

* MetadataRepository
* QueryService
* strukturierte Analyseergebnisse

---

# 6. Use Case: Änderungen an Dokumenten erkennen

## Ziel

Falls eine Quelle ein Dokument still austauscht, soll das erkannt werden.

## Ablauf

1. Discovery erkennt erneut dasselbe Dokument.
2. Fetch lädt Datei erneut.
3. Hash wird verglichen.
4. Wenn unterschiedlich:

   * neue Version speichern
   * Analyse erneut ausführen.

## Ergebnis

* Version 1 und Version 2 existieren
* Änderungen nachvollziehbar

## Wert

* Transparenz
* Quellenkritik

---

# 7. Use Case: Quellen mit Login überwachen

## Ziel

Zeitungen oder Portale mit Login überwachen.

## Ablauf

1. SourcePlugin nutzt Session oder BrowserAutomation.
2. Login erfolgt automatisch.
3. PDF wird heruntergeladen.

## Ergebnis

* geschützte Quellen sind nutzbar

## Wert

* mehr Datenquellen

---

# 8. Use Case: mehrere Analysen parallel durchführen

## Ziel

Ein Dokument soll gleichzeitig:

* Zusammenfassung
* Entity-Extraktion
* Legalitätsprüfung

durchlaufen.

## Ablauf

Pipeline:

```
Document
   → summary_analysis
   → entity_extraction
   → legality_check
```

Ergebnisse werden separat gespeichert.

## Ergebnis

ein Dokument hat mehrere Analyseobjekte.

---

# 9. Use Case: regelmäßige Zeitungsanalyse

## Ziel

Täglich neue Zeitungs-PDFs analysieren.

## Ablauf

1. Scheduler startet täglich.
2. SourcePlugin prüft:

   * neue Ausgabe vorhanden?
3. PDF herunterladen.
4. LLM extrahiert relevante Artikel.

## Ergebnis

* JSON mit Artikelliste

---

# 10. Use Case: tägliche Audio-Zusammenfassung erzeugen

## Ziel

Alle neuen Ereignisse des Tages als Audio zusammenfassen.

## Ablauf

1. QueryService sammelt neue Ereignisse.
2. Renderer erzeugt Text.
3. TTS-Plugin erzeugt Audio.

## Ergebnis

```
daily_briefing_2026_03_13.mp3
```

---

# 11. Use Case: automatische Legalitätsprüfung von AStA-Protokollen

## Ziel

Protokolle sollen automatisch auf mögliche Verstöße geprüft werden.

Beispiele:

* fehlende Datenschutzpassagen
* fehlende Beschlussprotokolle
* fehlende Teilnehmerliste

## Ablauf

1. Protokoll wird analysiert.
2. LLM klassifiziert mögliche Probleme.
3. Ergebnis wird strukturiert gespeichert.

## Beispiel

```json
{
  "issues": [
    {
      "type": "missing_attendance_list",
      "confidence": 0.8
    }
  ]
}
```

## Ergebnis

* mögliche Probleme sichtbar

---

# 12. Use Case: mehrere Interessenprofile

## Ziel

Mehrere Nutzer interessieren sich für unterschiedliche Themen.

## Beispiel

User A:

* Verkehr
* Bauprojekte

User B:

* Finanzen
* Haushalt

## Ablauf

Analyse extrahiert Themen.

RuleEngine prüft Interessenprofil.

## Ergebnis

verschiedene Benachrichtigungen.

---

# 13. Use Case: neue Quellen schnell hinzufügen

## Ziel

Neue Quelle hinzufügen ohne Framework zu ändern.

## Ablauf

1. Plugin hinzufügen.
2. YAML-Monitor definieren.

## Ergebnis

Neue Quelle läuft sofort.

---

# 14. Use Case: KI-Analyse reproduzierbar halten

## Ziel

Ergebnisse später nachvollziehen.

## Speicherung

* Modell
* Prompt
* Version
* Input
* Output

## Wert

wissenschaftlich nachvollziehbar.

---

# 15. Use Case: Monitoring-Dashboard

## Ziel

Überblick über Systemstatus.

## Anzeige

* letzte Runs
* Fehler
* neue Dokumente
* gesendete Benachrichtigungen

---

# Die wichtigsten Kategorien der Use Cases

Man sieht, dass sich alles in fünf Gruppen einordnen lässt:

### 1. Quellenüberwachung

* neue Dokumente erkennen
* Änderungen erkennen
* Login-Portale

### 2. Archivierung

* Speicherung
* Versionierung
* Metadaten

### 3. Analyse

* Zusammenfassung
* Extraktion
* Klassifikation

### 4. Regelbasierte Aktionen

* Alerts
* Digest
* Filter

### 5. Ausgabe

* Discord
* JSON
* TTS
* API

---

# Der wichtigste Architektur-Test

Eine Architektur ist gut, wenn **jeder dieser Use Cases ohne Sonderlogik implementierbar ist**.

Also:

* kein Spezialcode für einzelne Quellen
* keine Notifier-Logik in Analysen
* keine KI-Logik in Fetchern
* keine YAML-Magie

---

✅ Wenn du willst, kann ich als nächsten Schritt noch etwas sehr Wertvolles machen:

* **die minimalen Kernobjekte (Domain Model) definieren**
* also die Datenmodelle für
  `Document`, `Artifact`, `Analysis`, `Run`, `Rule`, `Notification`

Das ist der Punkt, der später **über Erfolg oder Chaos des Projekts entscheidet.**
