Ja — **so ein Framework ist absolut machbar**.

Und zwar nicht nur als lose Script-Sammlung, sondern als **sauberes, generisches Dokument-Monitoring-Framework** mit Plugins, strukturierter Pipeline, klarer Persistenz und austauschbaren Ausgabekanälen.

Der wichtigste Punkt ist aber:

> **Ihr solltet das Problem nicht als „Fetcher-Framework“ modellieren, sondern als „Framework für beobachtbare Dokument-Quellen mit Analyse- und Benachrichtigungs-Pipelines“.**

Denn „fetching“ ist nur ein Teil. Eigentlich wollt ihr:

1. Quellen beobachten
2. neue oder geänderte Dokumente entdecken
3. sie zuverlässig herunterladen
4. den Inhalt normalisieren
5. ihn strukturiert analysieren
6. Regeln darauf anwenden
7. passende Outputs erzeugen
8. alles nachvollziehbar speichern

Wenn man das sauber trennt, wird das Projekt erweiterbar. Wenn nicht, endet man bei 20 Spezial-Fetchern mit Copy-Paste.

---

# Mein Gesamturteil

## Das Projekt ist gut machbar, wenn ihr drei Dinge konsequent durchzieht

### 1. **Deklarative Config, keine Logik in YAML**

YAML soll beschreiben, **was** passieren soll, nicht **wie** es implementiert wird.

Also gut:

* welcher Monitor
* welches Plugin
* welcher Zeitplan
* welches Modell
* welches Prompt-Profil
* welche Notification-Regel
* welcher Output

Schlecht:

* Python-Ausdrücke in YAML
* CSS-Selector-Logik überall direkt inline
* Benachrichtigungslogik als freie Textmagie
* komplexe Sonderfälle als YAML-Monster

---

### 2. **Plugin-System statt Spezialskripte**

Ein `GemeinderatPfinztalFetcher` kann sinnvoll sein — aber nur als **dünnes Quell-Plugin**, das auf generischen Framework-Bausteinen aufsetzt.

Also nicht:

* jedes Projekt eigenes halbes Framework

Sondern:

* **ein Core**
* viele **Plugins / Adapters / Profiles**
* evtl. mehrere **Config-Repositories / Workspaces**

---

### 3. **KI nie als einzige Wahrheitsschicht**

KI ist sehr nützlich für:

* Zusammenfassungen
* Tagging
* Klassifikation
* Extraktion strukturierter Daten
* flexible Relevanzbewertung

Aber:

* **Deduplikation**
* **Versionierung**
* **Retry-Logik**
* **Speicherung**
* **Scheduling**
* **Rule-Evaluation**
* **Benachrichtigungsauswahl**
* **State Management**

sollten **deterministisch** im Framework liegen.

LLM-Ergebnisse sollten möglichst **strukturierte Outputs** liefern, die dann mit Pydantic validiert werden.

---

# Was das eigentliche Kernobjekt sein sollte

Nicht `Fetcher`.

Sondern eher:

## **Document Monitor**

Ein Monitor beobachtet eine Quelle und produziert Dokumente bzw. Dokument-Versionen.

Das eigentliche Kernmodell ist eher sowas wie:

* **Source**
  Eine beobachtbare Quelle, z. B. „Gemeinderat Pfinztal“, „AStA Uni X“, „Lokalzeitung PDF-Ausgabe“.

* **Candidate Item**
  Ein potenzielles neues Dokument, z. B. Link aus RSS, HTML-Seite, PDF-URL, Download-Eintrag.

* **Document**
  Das fachliche Dokument, z. B. „Protokoll Gemeinderat 2026-03-11“.

* **Document Version**
  Falls die Quelle dasselbe PDF still austauscht oder HTML aktualisiert.

* **Artifact**
  Konkrete gespeicherte Dateien:

  * Original-PDF
  * HTML-Snapshot
  * extrahierter Text
  * OCR-Text
  * JSON-Zusammenfassung
  * Inhaltsverzeichnis
  * Notification-Payload

* **Analysis Result**
  Strukturierte Ergebnisse einer Analyse-Pipeline.

* **Rule Decision**
  Ob benachrichtigt werden soll, mit Ping oder ohne Ping, an welchen Kanal, mit welchem Renderer.

Das ist viel stabiler als „ein Fetcher lädt etwas runter“.

---

# Die richtige Architektur

Ich würde das als Mischung aus **Ports-and-Adapters** und **pluginbasierter Pipeline** bauen.

## Oben: fachliche Core-Schicht

Dort lebt die Logik, die immer gleich bleibt:

* Monitor-Definitionen
* Laufsteuerung
* Deduplikation
* Versionierung
* State-Management
* Persistenz
* Retry / Backoff
* Analysis-Orchestrierung
* Rule Engine
* Renderer
* Notification Dispatch
* Event- und Run-Historie

## Unten: austauschbare Adapter / Plugins

Dort steckt alles, was je Quelle, Format oder Dienst anders ist:

* RSS-Discovery
* HTML-Listing-Discovery
* Browser-Automation / Login
* PDF-Download
* HTML-Content-Extraction
* PDF-Text-Extraction
* OCR
* Discord-Notifier
* Mail-Notifier
* Webhook-Notifier
* TTS-Output
* OpenAI / Anthropic / lokales Modell
* Spezifische Portale wie „Gemeinderat Pfinztal“

---

# Die zentrale Pipeline

Ich würde die Pipeline fachlich so trennen:

```text
Scheduler
  -> Monitor Run
    -> Discover
    -> Resolve Candidates
    -> Fetch Artifacts
    -> Normalize / Extract Text
    -> Identify Document + Version
    -> Persist
    -> Run Analyses
    -> Validate Outputs
    -> Evaluate Rules
    -> Render Outputs
    -> Notify / Export / Store
```

Diese Reihenfolge ist extrem wichtig, weil sie Wiederverwendbarkeit schafft.

---

# Welche Plugin-Typen ihr wahrscheinlich braucht

## 1. Source / Discovery Plugins

Sie finden heraus, **welche Dokumente existieren**.

Beispiele:

* RSSFeedDiscovery
* HtmlListDiscovery
* SitemapDiscovery
* SearchPortalDiscovery
* AuthenticatedPortalDiscovery
* GemeinderatPfinztalDiscovery

Output:

* Liste von `CandidateItem`

---

## 2. Fetch / Acquisition Plugins

Sie holen das konkrete Material.

Beispiele:

* HttpDownloader
* BrowserDownloader
* SessionPdfDownloader
* HtmlSnapshotFetcher

Output:

* rohe `Artifact`s wie PDF, HTML, JSON

---

## 3. Normalizer / Extractor Plugins

Sie machen Inhalte analysierbar.

Beispiele:

* HtmlToTextNormalizer
* ReadabilityExtractor
* PdfTextExtractor
* OCRExtractor
* MetadataExtractor
* TOCExtractor

Output:

* `NormalizedDocument` oder weitere Artifacts

---

## 4. Analysis Plugins

Sie erzeugen fachliche Ergebnisse.

Beispiele:

* KeywordMatcher
* RegexEntityExtractor
* LlmStructuredExtraction
* LlmRelevanceClassifier
* LegalityChecker
* MeetingSummaryExtractor

Output:

* validiertes JSON mit Schema

---

## 5. Rule Plugins / Rule Engine

Sie entscheiden, was passiert.

Beispiele:

* `contains_mention("Hauptstraße")`
* `if summary.importance >= 0.8`
* `if legality_flags contains "possible data privacy issue"`
* `if toc has section "Bebauungsplan"`

---

## 6. Renderers

Sie bauen aus strukturierten Ergebnissen eine Ausgabeform.

Beispiele:

* full_markdown_summary
* discord_short_alert
* discord_toc_only
* email_digest
* json_export
* ssml_briefing

Das ist wichtig: **Renderer sind nicht dasselbe wie Notifier**.

---

## 7. Notification / Delivery Plugins

Sie verschicken oder veröffentlichen etwas.

Beispiele:

* DiscordNotifier
* EmailNotifier
* WebhookNotifier
* FileSink
* TTSApiPublisher

---

# Warum Renderer und Notifier getrennt sein sollten

Das ist einer der Architekturpunkte, die später viel Ärger ersparen.

## Falsch

Discord-Plugin baut selbst die Nachricht zusammen.

Dann koppelt ihr:

* Business-Entscheidung
* Textaufbereitung
* Transport

alles aneinander.

## Besser

* **Analysis** liefert strukturierte Daten
* **Rule Engine** entscheidet, ob etwas relevant ist
* **Renderer** erzeugt z. B. Markdown / Plaintext / SSML / JSON
* **Notifier** sendet das über Discord / Mail / API

Dann könnt ihr denselben Inhalt:

* in Discord posten
* als E-Mail senden
* in eine API schreiben
* als TTS vorlesen lassen

ohne alles neu zu bauen.

---

# Meine klare Empfehlung zur Projektstruktur

## Nicht: ein komplett eigenes Projekt pro Quelle

Das wäre am Anfang bequem, wird aber später teuer:

* doppelte Retry-Logik
* doppelte Speicherschicht
* doppelte Config-Strukturen
* doppelte KI-Integration
* doppelte Notification-Implementierungen

## Besser:

### **Ein Framework-Core**

und darauf:

* **ein oder mehrere Plugin-Pakete**
* **ein Workspace pro Deployment / Nutzer / Themenfeld**

Also ungefähr so:

```text
protocol-watch/
  core/
  domain/
  orchestration/
  storage/
  notifications/
  ai/
  plugins/
    generic/
    municipal/
    university/
    media/
  cli/
  schemas/

workspaces/
  my-watchers/
    services.yml
    monitors.yml
    prompts/
    schemas/
    data/
```

So könnt ihr z. B. später haben:

* ein Workspace für Studierendenschaft
* ein Workspace für Gemeinderäte
* ein Workspace für lokale Medien

ohne das Framework zu duplizieren.

---

# Zwei YAML-Dateien sind sinnvoll — aber nicht die ganze Wahrheit

Deine Idee mit zwei YAMLs ist gut.

Ich würde aber fachlich sagen:

## 1. `services.yml`

Definiert wiederverwendbare Dienste / Accounts / Modelle / Ziele

Beispielinhalt:

* Discord-Accounts / Channel-Ziele
* Mail-Konfiguration
* Modellprovider
* API-Endpunkte
* Secret-Referenzen
* ggf. Storage-Backends

Wichtig:
**Secrets nicht direkt ins YAML**, sondern per Env-Referenz oder Secret-Backend.

Beispiel:

```yaml
notification_services:
  discord_alerts:
    plugin: discord
    token_env: DISCORD_ALERTS_TOKEN
    channel_id: "1234567890"
    allow_ping: true

  discord_digest:
    plugin: discord
    token_env: DISCORD_DIGEST_TOKEN
    channel_id: "9876543210"
    allow_ping: false

model_services:
  openai_fast:
    plugin: openai_chat
    api_key_env: OPENAI_API_KEY
    model: gpt-5.4-mini

  openai_strong:
    plugin: openai_chat
    api_key_env: OPENAI_API_KEY
    model: gpt-5.4
```

---

## 2. `monitors.yml`

Definiert die eigentlichen Beobachter / Jobs

Beispiel:

```yaml
monitors:
  - id: gemeinderat-pfinztal
    enabled: true
    schedule: "0 12 * * *"

    source:
      plugin: gemeinderat_pfinztal

    storage:
      namespace: municipality/pfinztal/council

    analyses:
      - id: street_mentions
        plugin: llm_extract
        model_service: openai_fast
        prompt_ref: prompts/street_mentions.md
        output_schema: schemas/street_mentions.schema.json
        retries: 3

      - id: session_summary
        plugin: llm_extract
        model_service: openai_strong
        prompt_ref: prompts/session_summary.md
        output_schema: schemas/session_summary.schema.json
        retries: 3

    notifications:
      - id: alert_hauptstrasse
        service: discord_alerts
        renderer: discord_ping_alert
        when:
          analysis: street_mentions
          condition: mention_equals("Hauptstraße")

      - id: toc_digest
        service: discord_digest
        renderer: toc_only
        when:
          analysis: session_summary
          condition: always
```

---

## 3. Prompt-Dateien und Schemas als Dateien, nicht inline

Das würde ich **nicht** alles in YAML stopfen.

Besser:

* `prompts/*.md`
* `schemas/*.json`
* evtl. `templates/*.j2`

Warum?

Weil Prompts:

* versioniert werden sollen
* separat getestet werden sollen
* nicht zwischen 200 YAML-Zeilen versteckt sein sollen

---

# Ein extrem wichtiger Architekturpunkt: Analyse-Profile statt freie Prompts

Ich würde nicht sagen:

> „Job referenziert einfach irgendeine Markdown-Datei“

sondern eher:

## **Analysis Profile**

Ein Profil definiert:

* Plugin-Typ
* Prompt-Template
* Modell
* Schema
* Retry-Strategie
* Temperatur / Max Tokens
* Output-Normalisierung
* evtl. Fallback-Modell

Dann referenziert der Monitor nur noch das Profil.

Warum das besser ist:

* weniger Wiederholung
* leichter versionierbar
* reproduzierbar
* sauberer Rollout neuer Prompts

Beispiel:

```yaml
analysis_profiles:
  street_mentions_v1:
    plugin: llm_extract
    model_service: openai_fast
    prompt_ref: prompts/street_mentions.md
    output_schema: schemas/street_mentions.schema.json
    retries: 3

  council_summary_v2:
    plugin: llm_extract
    model_service: openai_strong
    prompt_ref: prompts/council_summary.md
    output_schema: schemas/council_summary.schema.json
    retries: 3
```

Dann im Monitor nur:

```yaml
analyses:
  - profile: street_mentions_v1
  - profile: council_summary_v2
```

---

# So würde ich KI einbauen

Nicht als diffuses „hier ein Prompt“.

Sondern als **strukturierte Analyse-Engine**.

## Jede KI-Analyse sollte:

* ein klares Input-Objekt bekommen
* ein klar definiertes Schema haben
* validiert werden
* bei Fehlern bis zu 3x repariert werden
* das Roh-LLM-Output zusätzlich abspeichern
* Modell, Prompt-Version und Laufzeitmetadaten mitschreiben

## Sehr guter Standard-Output

Jedes KI-Ergebnis sollte zusätzlich immer Metadaten enthalten wie:

* `confidence`
* `schema_version`
* `model`
* `prompt_version`
* `source_artifacts`
* `warnings`

---

# Ganz wichtig: Notification-Regeln nicht direkt an freien Fließtext koppeln

Das wäre langfristig fragil.

## Schlecht

„Wenn die Zusammenfassung irgendwie nach Hauptstraße klingt, benachrichtige.“

## Besser

Ein Analyseprofil liefert z. B.:

```json
{
  "mentions": [
    {
      "term": "Hauptstraße",
      "context": "Sanierung des Straßenabschnitts",
      "relevance": 0.93
    }
  ]
}
```

Dann arbeitet die Regel-Engine darauf.

Das heißt:

* KI extrahiert Fakten
* Regel-Engine entscheidet
* Renderer formatiert
* Notifier sendet

So muss man nicht jedes Mal natürlichsprachlich raten, ob gepingt werden soll.

---

# Wie ich die Klassen bzw. Interfaces schneiden würde

Ich würde eher auf **Komposition und kleine Interfaces** setzen als auf tiefe Vererbung.

## Kerninterfaces

### SourcePlugin

Verantwortlich für Discovery.

```text
discover(context) -> list[CandidateItem]
```

---

### FetchPlugin

Holt rohe Inhalte.

```text
fetch(candidate, context) -> list[Artifact]
```

---

### NormalizerPlugin

Macht Inhalte analysierbar.

```text
normalize(artifacts, context) -> NormalizedDocument
```

---

### AnalysisPlugin

Erzeugt strukturiertes Ergebnis.

```text
analyze(document, profile, context) -> AnalysisResult
```

---

### RuleEvaluator

Entscheidet, ob Folgeaktionen ausgelöst werden.

```text
evaluate(document, analysis_results, rule, context) -> Decision
```

---

### Renderer

Erzeugt Ausgabeformate.

```text
render(decision, document, analysis_results, template) -> RenderedOutput
```

---

### Notifier

Verschickt die Ausgabe.

```text
send(rendered_output, service_config, context) -> DeliveryResult
```

---

### Repository / Store

Persistiert alles.

```text
save_run(...)
save_document(...)
save_artifact(...)
save_analysis(...)
save_notification(...)
```

---

# Welche Klassen ihr fachlich vermutlich wirklich haben wollt

## Fachobjekte

* `MonitorDefinition`
* `SourceDefinition`
* `CandidateItem`
* `DocumentIdentity`
* `DocumentVersion`
* `ArtifactRef`
* `NormalizedDocument`
* `AnalysisProfile`
* `AnalysisResult`
* `NotificationRule`
* `DeliveryTarget`
* `RenderedOutput`
* `RunRecord`

## Infrastruktur

* `Scheduler`
* `RunOrchestrator`
* `PluginRegistry`
* `ConfigLoader`
* `SecretResolver`
* `ArtifactStore`
* `MetadataRepository`
* `ModelRouter`
* `PromptRegistry`
* `RuleEngine`
* `NotificationDispatcher`

---

# Wie ein spezieller Source-Plugin aussehen sollte

Nehmen wir `gemeinderat_pfinztal`.

Das Plugin sollte **nicht** alles selbst machen.

Es sollte eher nur die quellspezifischen Teile enthalten:

* welche Startseite / Portal
* wie dort Sitzungen gefunden werden
* wie Dokumentlinks erkannt werden
* wie Titel / Datum / Sitzungstyp identifiziert werden
* evtl. Login / Session-Besonderheiten

Es sollte **nicht** selbst machen:

* Dateispeicherung
* Versionierung
* Notification-Versand
* LLM-Aufrufe
* Retry-Mechanik
* JSON-Validierung
* Discord-Formatierung

Genau dadurch spart ihr später massiv Duplikate.

---

# Der wichtigste Architekturtrick gegen Copy-Paste

## Trennt „Quelle“ von „Mechanismus“

Beispiel:

### Mechanismen

* RSS-Liste lesen
* HTML-Liste parsen
* PDF herunterladen
* Browser-Login
* HTML zu Text extrahieren
* PDF-Text extrahieren

### Quellen

* AStA Uni X
* Gemeinderat Y
* Zeitung Z

Viele Quellen nutzen dieselben Mechanismen in anderer Kombination.

Darum sollte ein Source-Plugin oft nur eine **Komposition vorhandener Bausteine** sein.

---

# Persistenz: So würde ich speichern

Hier würde ich **klein, aber sauber** anfangen.

## Empfehlung für den Start

* **SQLite** für Metadaten / States / Runs / Indizes
* **Filesystem** für Artefakte

Das reicht sehr weit.

## Später optional

* Postgres statt SQLite
* S3/MinIO/Object Storage statt lokales FS

---

## Was gespeichert werden sollte

### Metadatenbank

* Monitore
* Runs
* Candidate-Items
* Dokumente
* Dokument-Versionen
* Artifacts
* Analysis-Runs
* Notification-Runs
* Fehler
* Caches / ETags / Last-Seen-Daten

### Dateisystem / Blob-Store

* Original-PDF
* Original-HTML
* Text-Extrakte
* OCR-Texte
* LLM-Rohantworten
* validierte JSON-Ergebnisse
* gerenderte Nachrichten
* Screenshots / Snapshots bei Fehlern

---

## Unbedingt: immutable speichern

Nichts still überschreiben.

Wenn ein PDF sich ändert:

* neue Version anlegen
* alten Hash behalten
* neue Analysis-Runs erzeugen, falls nötig

Denn gerade bei öffentlichen Protokollen kann es Korrekturen geben.

---

# Deduplikation und Versionierung

Das ist eine der wichtigsten technischen Fragen.

Ihr braucht **mindestens zwei Ebenen**:

## 1. Identity

„Ist das fachlich dasselbe Dokument?“
Beispiel:

* Gemeinderat Pfinztal
* Sitzung vom 2026-03-11
* öffentliches Protokoll

## 2. Content Version

„Ist der Inhalt wirklich identisch?“
Beispiel:

* gleicher Titel
* gleiche Quelle
* aber PDF wurde korrigiert

Dafür würde ich verwenden:

* kanonische URL, falls stabil
* fachlicher Identifier, wenn vorhanden
* Content-Hash auf Datei / extrahiertem Kerninhalt

---

# Scheduling und Läufe

Ihr wollt viele Quellen mit unregelmäßigen Updates. Deshalb braucht ihr:

## Pro Monitor

* Cron-ähnlichen Schedule
* Backoff bei Fehlern
* optionalen Jitter
* Timeout
* Concurrency-Limit
* „skip if already running“

## Pro Run

* Run-ID
* Start / Ende
* Status
* Anzahl gefundener Kandidaten
* Anzahl neuer Dokumente
* Anzahl geänderter Versionen
* Anzahl Benachrichtigungen
* Fehlermeldungen

Das macht Debugging später viel leichter.

---

# Fehlerbehandlung

Ich würde Fehler auf drei Ebenen unterscheiden:

## 1. Discovery-Fehler

Quelle nicht erreichbar, HTML geändert, Login fehlgeschlagen

## 2. Processing-Fehler

PDF kaputt, Extraktion fehlgeschlagen, OCR problematisch

## 3. Analysis-Fehler

LLM-Output nicht valide, Schemafehler, Halluzination, Timeout

Und für jede Ebene:

* Retry-Policy
* klare Fehlerklasse
* persistenter Fehlerreport
* optional Fehlerbenachrichtigung

---

# Für LLM-Ausgaben: Reparatur-Schleife ist sinnvoll

Deine Idee mit 3 Retries ist gut.

Ich würde aber unterscheiden:

## Retry-Typen

### Technischer Retry

* API Timeout
* Rate Limit
* Netzwerkfehler

### Validierungs-Retry

* Schema ungültig
* Feld fehlt
* unerlaubter Typ

### Repair-Retry

* Framework baut automatisch eine Reparaturaufforderung:

  * „Hier ist dein ungültiges JSON“
  * „Liefere nur gültiges JSON nach Schema X“

Das ist besser als einfach blind drei Mal denselben Prompt zu schicken.

---

# Zukunftssicherheit für MCP / Query / API

Du hast völlig recht: Das muss man **jetzt schon mitdenken**, aber **noch nicht implementieren**.

## Der Trick:

Die Pipeline darf nicht bloß Dateien ablegen.
Sie muss eine **abfragbare interne Wissensschicht** erzeugen.

Deshalb braucht ihr intern eine saubere Service-Schicht wie:

* `DocumentService`
* `AnalysisService`
* `SearchService`
* `SourceService`

Später kann ein MCP-Server oder API-Layer genau diese Services exponieren.

Dann könnt ihr später Fragen stellen wie:

* „Zeige alle Protokolle, in denen Blumenstraße erwähnt wurde“
* „Welche Gemeinderatssitzungen hatten das Tag Verkehr?“
* „Gib mir die Zusammenfassung vom 11.03.2026“

Ohne die Fetcher neu anzufassen.

---

# TTS und API-Ausgabe

Auch das spricht dafür, Ausgabe **nicht** als bloßen Text zu modellieren.

Ich würde intern mit einem **Output-Payload-Modell** arbeiten.

Beispiel:

* `title`
* `summary`
* `highlights`
* `toc`
* `metadata`
* `speech_summary`
* `markdown_body`
* `plain_text_body`

Dann kann ein Renderer daraus:

* Discord Markdown
* E-Mail Text
* JSON API Response
* SSML / TTS-Text

machen.

Das ist viel sauberer als „Discord-Text erzeugen und später irgendwie wiederverwenden“.

---

# Was ich ausdrücklich **nicht** so bauen würde

## 1. Einen riesigen `BaseFetcher`

Das wird schnell zur God Class.

Besser:

* Discovery
* Fetch
* Normalize
* Analyze
* Notify

sauber trennen.

---

## 2. Logik in YAML verstecken

Kein Python in YAML.
Keine komplexen Selector-Ketten in 40 Inline-Zeilen.

Wenn etwas nicht mehr angenehm lesbar ist, gehört es in ein Plugin oder Profil.

---

## 3. KI direkt über Rohtexte entscheiden lassen, ob gepingt wird

Besser:

* erst strukturieren
* dann Regeln darauf

---

## 4. Alles quellspezifisch machen

Viele Dinge sind generisch:

* RSS
* HTML-Listen
* PDFs
* Auth-Sessions
* LLM-Summaries
* Discord-Notifications

Die Speziallogik sollte der kleine Rest sein.

---

## 5. Rohdaten überschreiben

Immer versionieren. Immer Hashes speichern.

---

## 6. Notifier selbst Texte zusammenbauen lassen

Renderer und Notifier trennen.

---

# Was ich als „low-regret architecture“ empfehlen würde

Perfekt im absoluten Sinn gibt es nicht.
Aber es gibt eine Architektur, bei der man **später wenig bereut**.

Die wäre für mich:

## Core

* `domain/`
* `orchestration/`
* `storage/`
* `rules/`
* `rendering/`
* `notifications/`
* `ai/`
* `config/`

## Plugin-Typen

* source plugins
* fetch plugins
* normalize plugins
* analysis plugins
* notifier plugins
* renderer plugins

## Persistenz

* SQLite + Filesystem zuerst

## Config

* `services.yml`
* `monitors.yml`
* `prompts/`
* `schemas/`
* optional `analysis_profiles.yml`

## Designprinzipien

* deklarativ
* immutable artifacts
* structured outputs
* composition over inheritance
* plugins over forks
* deterministic orchestration
* LLM only where it adds value

---

# Mein konkreter Architekturvorschlag in einem Satz

> **Baut ein pluginbasiertes Dokument-Monitoring-Framework mit einer stabilen Core-Pipeline für Discovery, Acquisition, Normalization, Analysis, Rule Evaluation, Rendering und Delivery — und haltet YAML rein deklarativ, während alle quellspezifischen Besonderheiten in dünnen Plugins oder Profilen kapsuliert werden.**

---

# Wie ich anfangen würde

Nicht implementieren, aber als Architektur-Festlegung:

## Phase 1: Kernmodell festziehen

Vor jeder Implementierung definieren:

* welche fachlichen Objekte es gibt
* welche States ein Dokument / Run haben kann
* welche Plugin-Typen es gibt
* wie die Pipeline exakt aussieht

## Phase 2: Config-Schema definieren

Saubere Pydantic-Modelle für:

* services
* monitors
* analysis profiles
* rules
* storage
* schedules

## Phase 3: Minimaler End-to-End-Fall

Nur ein sehr einfacher Use Case:

* HTML oder RSS
* PDF speichern
* Text extrahieren
* eine strukturierte LLM-Zusammenfassung
* Discord-Notification

## Phase 4: Erst dann komplexe Quellen

* Login
* schwierige Portale
* mehrere Analyseprofile
* Regelkombinationen
* TTS / API / MCP später

---

# Mein wichtigstes Fazit

Deine Intuition ist richtig:

* **ein Framework statt vieler Einzellösungen**
* **spezifische Source-Plugins statt YAML-Magie**
* **zentrale Speicherung**
* **mehrere Analysen pro Dokument**
* **strukturierte LLM-Ausgaben**
* **Benachrichtigungen als Folge von Regeln**
* **Ausgabeform und Versand trennen**
* **MCP später auf gespeicherten Daten aufsetzen**

Wenn ihr das so angeht, habt ihr eine Architektur, die sowohl für:

* Studierendenschaftsprotokolle
* AStA anderer Unis
* lokale Ratsprotokolle
* Login-geschützte PDFs
* Zeitungsquellen
* Relevanzfilter
* Zusammenfassungen
* TTS
* spätere Such- und Frage-APIs

sauber tragfähig ist.

Als nächsten sinnvollen Schritt würde ich das jetzt in ein **konkretes Architektur-Dokument mit Modulen, Interfaces, Datenmodellen und Beispiel-Config** gießen.
