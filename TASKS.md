# Task Board - Project Manager Aktionsbereich

> **Für Project Manager Agent**: Dieser Bereich ist dein primäres Arbeitsfeld.
> Halte diese Datei aktuell und gib klare Anweisungen an andere Agents.

---

## Codebase Status (Stand: 2026-03-23)

| Kategorie | Bewertung | Anmerkung |
|-----------|-----------|-----------|
| Architektur | 8/10 | Saubere Multi-Process Trennung |
| Code Qualität | 6/10 | Typ-Hints inkonsistent |
| Test Coverage | 4/10 | ~40% Coverage |
| Produktions-reif | 5/10 | Braucht Härtung |

---

## Aktuelle Tasks

### 🔴 Priorität 0 - SOFORT (Blocker)

| ID | Task | Agent | Status | Details |
|----|------|-------|--------|---------|
| ~~P0-1~~ | ~~IK Dataclass Mismatch fix~~ | developer | **✅ DONE** | `LegAngles` umbenannt zu `coxa/femur/tibia`. Config-Mapping in SAL hinzugefügt. |
| ~~P0-2~~ | ~~Gait API fix~~ | developer/tester | **✅ DONE** | `set_gait()` Methode hinzugefügt, Tests korrigiert. |

### 🔴 Priorität 1 - HOCH

| ID | Task | Agent | Status | Details |
|----|------|-------|--------|---------|
| ~~P1-0~~ | ~~BT Factory Tests fix~~ | developer | **✅ DONE** | `params` optional in `ParameterLeaf`, `set_look_at` in MockGait, Test-Fixtures verbessert. Alle 35 Tests bestanden. |
| ~~P1-1~~ | ~~Vision Watchdog/Restart~~ | developer | **✅ DONE** | `_check_vision_watchdog()` und `_restart_vision()` in `IntelligenceController`. Config-Optionen hinzugefügt. |
| ~~P1-3~~ | ~~Gait Transformation Tests~~ | tester | **✅ DONE** | 36 Tests: Body Rotation, Turn Compensation, Additive Layers, Auto-Gait. **91 Tests bestanden!** |
| ~~P1-3~~ | ~~Gait Transformation Tests~~ | tester | **✅ DONE** | 36 Tests: Body Rotation, Turn Compensation, Additive Layers, Auto-Gait. **91 Tests bestanden!** |
| ~~P1-4~~ | ~~Queue Consumer Timeout~~ | developer | **✅ DONE** | Queue mit Timeout (0.01s) und Item-Limit (3 pro Update). Config-Optionen hinzugefügt. |
| ~~P1-5~~ | ~~Social Memory File Locking~~ | developer | **✅ DONE** | Threading.Lock + atomares Schreiben (temp file + rename). Verhindert JSON Corruption. |

### 🟡 Priorität 2 - MITTEL (Backend)

| ID | Task | Agent | Status | Details |
|----|------|-------|--------|---------|
| ~~P2-1~~ | ~~Behavior Tree YAML Parsing Tests~~ | tester | **✅ DONE** | 34 Tests: Selector, Sequence, Parallel, WeightedSelector, ParameterLeaf, YAML Parsing. |
| ~~P2-2~~ | ~~MQTT Integration Tests~~ | tester | **✅ DONE** | 28 Tests: Connection, Discovery, Publish, Command Routing. |
| ~~P2-3~~ | ~~Magic Numbers → Config~~ | developer | **✅ DONE** | Face Recognition Thresholds aus Config: `face_match_threshold`, `face_new_angle_threshold`, `face_embedding_alpha`, `face_max_templates`. |

### 🟡 Priorität 3 - NIEDRIG (Frontend)

| ID | Task | Agent | Status | Details |
|----|------|-------|--------|---------|
| ~~P3-1~~ | ~~Dashboard UI Testen~~ | frontend_tester | **✅ DONE** | 36 API/UI/Vision Tests erstellt, Manuelle Test-Checkliste. 166 Tests bestanden. |
| ~~P3-2~~ | ~~Control Panel Verbessern~~ | frontend_dev | **✅ DONE** | Error Handling für alle fetch() calls, Loading States für Save-Buttons, Toast-Benachrichtigungen. |
| ~~P3-3~~ | ~~Vision Panel UI Verbesserungen~~ | frontend_dev | **✅ DONE** | Camera-Status-Indikator, FPS-Anzeige, Face Detection Overlay, /api/status mit detected_face. |

### 🟢 Priorität 4 - BACKLOG

| ID | Task | Agent | Status | Details |
|----|------|-------|--------|---------|
| ~~P4-1~~ | ~~Plugin Architektur~~ | developer | **✅ DONE** | Plugin-System erstellt, DanceBehavior Beispiel-Plugin, 18 Tests bestanden |
| ~~P4-2~~ | ~~Systemd Service File~~ | developer | **✅ DONE** | Service-Datei mit Auto-Restart, Graceful Shutdown, Setup-Script, 11 Tests bestanden |
| ~~P4-3~~ | ~~API Dokumentation~~ | developer | **✅ DONE** | OpenAPI 3.0.3 Spec erstellt, alle Endpoints dokumentiert, 13 Tests bestanden |
| ~~P4-4~~ | ~~Battery Low-Voltage Protection~~ | developer | **✅ DONE** | `is_critical()` Methode, config-basierte Thresholds, Auto-Warnungen, 10 Tests bestanden |
| P4-5 | MockIMU Dynamic Data | developer | backlog | Camera Stabilization testbar machen mit realistischen IMU-Daten |
| P4-6 | Queue Timeout Validation | developer | backlog | Main Loop Queue-Blocking Risk eliminieren |
| P4-7 | Thread-Safe Config | developer | backlog | Config Hot-Reload thread-safe machen |

### 🟢 Priorität 5 - CODE QUALITY (LSP Warnings)

| ID | Task | Agent | Status | Details |
|----|------|-------|--------|---------|
| ~~P5-1~~ | ~~LSP Warnings main.py beheben~~ | developer | **✅ DONE** | config moved before use, hasattr checks, battery voltage safety |
| ~~P5-2~~ | ~~LSP Warnings ik.py beheben~~ | developer | **✅ DONE** | `limits: Optional[dict] = None` |
| ~~P5-3~~ | ~~LSP Warnings behaviors.py beheben~~ | developer | **✅ DONE** | `math` importiert, gait None-Checks |
| ~~P5-4~~ | ~~LSP Warnings bt_factory.py beheben~~ | developer | **✅ DONE** | Idle mit `self.context` statt `gait`, alle 34 BT-Tests bestanden |
| ~~P5-5~~ | ~~Type Hints konsistent machen~~ | developer | **✅ DONE** | Optional imports hinzugefügt |

---

## Risiko-Analyse

### HIGH RISK (behoben)
1. ~~**Race Condition Vision Shutdown**~~ - ✅ P1-1 Watchdog
2. ~~**IK Math Domain Errors**~~ - ✅ P1-2 Tests decken ab
3. ~~**Face DB Corruption**~~ - ✅ P1-5 File Locking implementiert

## QA Review Sprint 1 (2026-03-23)

### ✅ Tests
- 91/91 bestanden

### ✅ Code Quality
- Type Hints auf public Methods
- Error Handling mit Logging
- Config-Werte für Magic Numbers
- Keine hardcoded secrets

### 🔧 Behandelte Anmerkungen
- [x] IK Kommentar "Coxa" → "Shoulder" korrigiert
- [x] Vision Watchdog Boot-Phase Schutz (grace period 60s)
- [x] Fehlende Docstrings ergänzt (API-Methoden in gait.py, intelligence.py)

### Potential Issue ✅ FIXED
- Vision Watchdog Boot-Phase: Neue `vision_boot_timeout` Config (60s grace period)
  - Verhindert premature restarts bei langsamer Kamera-Initialisierung
  - Watchdog prüft erst nach 60s ob Process alive ist

### Dokumentation verbessert
- Docstrings hinzugefügt:
  - movement/gait.py: reset, set_target_speed, update, get_phases
  - brain/intelligence.py: load, save, update_exposure, rename_face, delete_face, start, stop

### Empfohlene Sprint 2 Tasks
1. P2-1: Behavior Tree YAML Tests
2. P2-2: MQTT Integration Tests
3. P2-3: Magic Numbers aufräumen

### MEDIUM RISK (Diese Woche)
4. ~~**MockIMU Static Data**~~ → P4-5 (backlog)
5. ~~**Queue Blocking Risk**~~ → P4-6 (backlog)
6. ~~**Config Hot-Reload**~~ → P4-7 (backlog)

---

## Nächste Schritte (empfohlene Reihenfolge)

```
1. P0-1: IK Dataclass fix → Developer
2. P0-2: Gait API fix → Developer
3. P0-1/2: Tests laufen lassen → Tester (verifizieren)
4. P1-1: Vision Watchdog → Developer
5. P1-2: IK Tests erweitern → Tester
6. P1-3: Gait Tests → Tester
```

---

## Letzte Anweisungen an Agents

### An Developer (Backend)
```
Sprint 1 abgeschlossen! 91 Tests bestanden.
Nächster Task: P2-1 (Behavior Tree YAML Tests)
```

### An Tester (Backend)
```
Sprint 1 Tests abgeschlossen.
Nächste Aufgabe: P2-1 Tests vorbereiten (Behavior Tree YAML Parsing)
```

### An Frontend_Dev
```
Sprint 1 Backend abgeschlossen.
Bereit für Sprint 2 Frontend Tasks: P2-4 (Dashboard UI Testen)
```

### An Frontend_Tester
```
Frontend Agenten neu erstellt.
Bereit für P2-4 (Dashboard UI Testen) wenn Frontend_Dev fertig ist.
```

### An QA
```
Sprint 1 reviewed und approved.
Frontend Review kommt in Sprint 2.
```

---

## Workflow - Multi-Agent Prozess

### Post-Task Schritte (Backend)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  DEVELOPER                                                            │
│  ─────────                                                            │
│  1. Task implementieren                                               │
│  2. Lokale Tests: python -m pytest tests/ -v                           │
│  3. Commit erstellen mit klarer Message                                │
│  4. TASKS.md aktualisieren (Status → "Dev Done")                      │
│  5. NOTIFY: Tester über fertigen Task                                 │
└─────────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────────┐
│  TESTER                                                               │
│  ─────                                                               │
│  1. Code reviewen                                                     │
│  2. Neue Tests für Edge Cases schreiben                               │
│  3. Alle Tests: python -m pytest tests/ -v --tb=short                │
│  4. Coverage prüfen: python -m pytest tests/ --cov=.                 │
│  5. Falls Fehler: Developer benachrichtigen                           │
│  6. TASKS.md aktualisieren (Status → "Tests Pass")                   │
│  7. NOTIFY: QA für Code Review                                        │
└─────────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────────┐
│  QA                                                                   │
│  ──                                                                   │
│  1. Code Review: Brain/intelligence.py, Movement/ik.py, etc.          │
│  2. Security Check: Keine hardcoded secrets, I2C Safety               │
│  3. Docstrings + Type Hints prüfen                                    │
│  4. Error Handling: Try/Except mit Logging?                           │
│  5. Falls Fehler: Developer benachrichtigen                            │
│  6. ✅ WENN ZUFRIEDEN:                                                │
│     - TASKS.md aktualisieren (Status → "QA Approved")               │
│     - Commit erstellen                                                │
│     - NOTIFY: Project Manager für nächsten Task                        │
└─────────────────────────────────────────────────────────────────────────┘
```

### Post-Task Schritte (Frontend)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  FRONTEND_DEV                                                         │
│  ─────────────                                                        │
│  1. Task implementieren (HTML/CSS/JS)                                │
│  2. Manuelles Testen im Browser                                       │
│  3. Responsive-Check (Desktop, Tablet, Mobile)                        │
│  4. Commit erstellen mit klarer Message                                │
│  5. TASKS.md aktualisieren (Status → "Dev Done")                      │
│  6. NOTIFY: Frontend_Tester über fertigen Task                        │
└─────────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────────┐
│  FRONTEND_TESTER                                                      │
│  ──────────────                                                       │
│  1. UI testen: Layout, Farben, Schriften                              │
│  2. API Integration prüfen (curl oder Browser Console)                │
│  3. Accessibility prüfen (Keyboard, Screenreader)                      │
│  4. Responsive Design testen (Browser DevTools)                        │
│  5. Falls Fehler: Frontend_Dev benachrichtigen                         │
│  6. TASKS.md aktualisieren (Status → "Tests Pass")                   │
│  7. NOTIFY: QA für UI Review                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────────┐
│  QA (Frontend Review)                                                 │
│  ───────────────────────                                             │
│  1. UI/UX Review: Konsistenz, Nutzerfreundlichkeit                    │
│  2. Security: Keine XSS, Input Validation                             │
│  3. Performance: Keine langsamen Requests, sinnvolle Loading-States   │
│  4. ✅ WENN ZUFRIEDEN:                                                │
│     - TASKS.md aktualisieren (Status → "QA Approved")               │
│     - Commit erstellen                                                │
│     - NOTIFY: Project Manager für nächsten Task                        │
└─────────────────────────────────────────────────────────────────────────┘
```
┌─────────────────────────────────────────────────────────────────────────┐
│  DEVELOPER                                                            │
│  ─────────                                                            │
│  1. Task implementieren                                               │
│  2. Lokale Tests: python -m pytest tests/ -v                           │
│  3. Linting checken (falls vorhanden)                                  │
│  4. Commit erstellen mit klarer Message                                │
│  5. TASKS.md aktualisieren (Status → "Dev Done")                      │
│  6. NOTIFY: Tester über fertigen Task                                 │
└─────────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────────┐
│  TESTER                                                               │
│  ─────                                                               │
│  1. Branch mergen oder Code reviewen                                  │
│  2. Neue Tests für Edge Cases schreiben                               │
│  3. Alle Tests: python -m pytest tests/ -v --tb=short                │
│  4. Coverage prüfen: python -m pytest tests/ --cov=.                 │
│  5. Falls Fehler: Bug-Ticket erstellen, Developer benachrichtigen    │
│  6. TASKS.md aktualisieren (Status → "Tests Pass")                   │
│  7. NOTIFY: QA für Code Review                                        │
└─────────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────────┐
│  QA                                                                   │
│  ──                                                                   │
│  1. Code Review: Brain/intelligence.py, Movement/ik.py, etc.          │
│  2. Security Check: Keine hardcoded secrets, I2C Safety               │
│  3. Docstrings prüfen: Public Methods dokumentiert?                   │
│  4. Type Hints: Alle public Methoden mit korrekten Typen?             │
│  5. Error Handling: Try/Except mit Logging?                           │
│  6. Kommentare prüfen: Fehlende/veraltete Kommentare korrigieren    │
│  7. Dokumentation prüfen: Docs aktuell? ggf. aktualisieren           │
│  8. Falls Fehler: Developer benachrichtigen                            │
│  9. ✅ WENN ZUFRIEDEN:                                                │
│     - TASKS.md aktualisieren (Status → "QA Approved")               │
│     - Commit erstellen                                                │
│     - NOTIFY: Project Manager für nächsten Task                        │
└─────────────────────────────────────────────────────────────────────────┘
```

### Project Manager - Nächsten Task zuweisen

```
Wenn QA den vorherigen Task approved und committed hat:
1. TASKS.md prüfen: Nächsten Task mit Status "backlog" finden
2. Priorität prüfen (P0 > P1 > P2 > P3)
3. Agent zuweisen und NOTIFY
4. Sprint Fortschritt aktualisieren
```
┌─────────────────────────────────────────────────────────────────────────┐
│  DEVELOPER                                                            │
│  ─────────                                                            │
│  1. Task implementieren                                               │
│  2. Lokale Tests: python -m pytest tests/ -v                           │
│  3. Linting checken (falls vorhanden)                                  │
│  4. Commit erstellen mit klarer Message                                │
│  5. TASKS.md aktualisieren (Status → "Dev Done")                      │
│  6. NOTIFY: Tester über fertigen Task                                 │
└─────────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────────┐
│  TESTER                                                               │
│  ─────                                                               │
│  1. Branch mergen oder Code reviewen                                  │
│  2. Neue Tests für Edge Cases schreiben                               │
│  3. Alle Tests: python -m pytest tests/ -v --tb=short                │
│  4. Coverage prüfen: python -m pytest tests/ --cov=.                 │
│  5. Falls Fehler: Bug-Ticket erstellen, Developer benachrichtigen     │
│  6. TASKS.md aktualisieren (Status → "Tests Pass")                    │
│  7. NOTIFY: QA für Code Review                                        │
└─────────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────────┐
│  QA                                                                   │
│  ──                                                                   │
│  1. Code Review: Brain/intelligence.py, Movement/ik.py, etc.          │
│  2. Security Check: Keine hardcoded secrets, I2C Safety               │
│  3. Docstrings prüfen: Public Methods dokumentiert?                   │
│  4. Type Hints: Alle public Methoden mit korrekten Typen?             │
│  5. Error Handling: Try/Except mit Logging?                           │
│  6. TASKS.md aktualisieren (Status → "QA Approved")                   │
│  7. Sprint Review: Alle P0-P1 DONE? → Sprint abschließen              │
└─────────────────────────────────────────────────────────────────────────┘
```

### Sprint Starten

```
1. Project Manager: Sprint Planning in TASKS.md
2. Prioritäten setzen (P0 → P1 → P2 → P3)
3. Agenten zuweisen (Developer, Tester, QA)
4. Sprint Goals dokumentieren
```

### Sprint Abschließen

```
1. Alle P0-P1 Tasks DONE?
2. Test Coverage ≥ 70%?
3. QA Approval für alle kritischen Features?
4. Commit History Review
5. CHANGELOG.md aktualisieren
6. Nächsten Sprint planen
```

---

## Notizen

**Analyse abgeschlossen**: 2026-03-23
- Codebase ist solide Basis, braucht Test-Coverage und Edge-Case Handling
- IK Mismatch und fehlgeschlagene Tests sind immediate Blocker
- Architecture ist gut, Produktions-Reife需要 Härtung

**Updates 2026-03-23 (Sprint 1)**:
- P0-1: IK Dataclass umbenannt (joint_1/2/3 → shoulder/thigh/shin)
- P0-2: Gait set_gait() hinzugefügt, Tests korrigiert
- P1-0: BT ParameterLeaf params optional, MockGait erweitert
- P1-1: Vision Watchdog implementiert mit Auto-Restart
- P1-2: IK Tests erweitert + neue Winkel-Konvention (0° = Straight Down)
- P1-3: Gait Tests erweitert (Body Rotation, Turn Compensation, Additive Layers)
- P1-4: Queue Consumer Timeout implementiert
- P1-5: Social Memory File Locking implementiert
- **91 Tests bestanden!**
- Sprint 1 abgeschlossen!
