# Software Architektur (Robot 2.0)

Dieses Dokument beschreibt die neue, modulare Architektur der Robot 2.0 Software.

## 1. Systemübersicht & Data-Flow
Das System basiert auf einer Multi-Prozess-Architektur, um zeitkritische Bewegungssteuerung (100Hz) von rechenintensiver Vision-KI zu trennen.

```mermaid
graph TD
    Main[Main Process (100Hz Loop)] -->|Update| SAL[Software Abstraction Layer]
    SAL -->|I2C| Servos[PCA9685 / Servos]
    SAL -->|I2C| IMU[MPU6050]
    SAL -->|I2C| Battery[ADS7830]
    
    Vision[Vision Process (Asynchron)] --- SharedIMU((Shared IMU Array))
    Main -->|Pushed Data| SharedIMU
    SharedIMU -->|Pull for DIS| Vision
    
    Vision -->|Detection Events / Face Vectors| Queue[(Result Queue)]
    Queue -->|Process Requests| Intel[Intelligence Controller]
    Intel -->|Identified Name| IdentQueue[(Identity Queue)]
    IdentQueue -->|Overlay Name| Vision
    Intel -->|Calculate Pose| Gait[Gait Sequencer]
    Gait -->|Target Coordinates| IK[IK Engine]
    IK -->|Angles| Main
```

## 2. Zentrale Komponenten
### A. Hardware Abstraction (SAL)
Alle Hardware-Zugriffe erfolgen über die `SalFactory`. Dies ermöglicht einen **Simulation-Mode**, in dem alle Treiber durch Mocks ersetzt werden, um die Logik auf dem PC zu testen.

### B. Zentralisierte Servo-Steuerung (Sicherheit)
**WICHTIG:** Im Gegensatz zur Legacy-Software erfolgt der Zugriff auf den I2C-Bus (PCA9685) ausschließlich über den Main-Loop. 
*   Die Vision-Pipeline sendet `tilt_request` Nachrichten via Queue.
*   Die `IntelligenceController.update()` Methode verarbeitet diese und schreibt die Werte sicher in den I2C-Bus.
*   Dies verhindert I2C-Bus-Contention und Race-Conditions.

### D. Social Memory & Perzeption
Ein zentraler Bestandteil der Intelligenz ist das **Soziale Gedächtnis** (`SocialMemory`):
*   **Multi-View Recognition:** Speicherung von bis zu 10 verschiedenen Gesichtswinkeln (embeddings) pro Person, um Erkennung bei Kopfdrehung zu stabilisieren.
*   **Trust-System:** Vertrauen baut sich über die Zeit auf (kubische Kurve).
*   **Persistent Storage:** Gesichter und zugehörige Fotos werden in `face_db.json` und einem `faces/` Verzeichnis dauerhaft gespeichert.
*   **Identity Feedback:** Sobald die KI eine Person identifiziert hat, wird der Name via `Identity Queue` zurück an den Vision-Prozess gesendet, um ihn im Video-Overlay anzuzeigen.
*   **Garbage Collection:** Automatische Löschung flüchtiger Detektionen (Stranger, <15s Kontakt) nach 2 Stunden Inaktivität.
*   **Konfigurierbare Thresholds:** Face Recognition nutzt Config-Parameter:
    *   `face_match_threshold`: L2-Distanz für Gesichtsabgleich (Standard: 1.0)
    *   `face_new_angle_threshold`: Distanz für neue Ansicht (Standard: 0.5)
    *   `face_embedding_alpha`: Update-Rate für Embedding-Anpassung (Standard: 0.01)
    *   `face_max_templates`: Max Templates pro Gesicht (Standard: 10)

### C. Vision Watchdog
Der IntelligenceController überwacht den Vision-Prozess:
*   **Watchdog-Timeout:** Neustart nach 30s Inaktivität (konfigurierbar)
*   **Boot-Grace-Period:** 60s Wartezeit während Kamera-Initialisierung
*   **Max-Restarts:** Max 5 Neustart-Versuche bevor aufgegeben

## 3. Kommunikation & Connectivity
*   **MQTT (Home Assistant):** Bietet Auto-Discovery für Sensoren und Schalter.
*   **Web-Server:** Streamt den stabilisierten MJPEG-Feed und bietet ein Notfall-Dashboard.

### Web Dashboard Features
Das Dashboard (`api/templates/index.html`) bietet:
*   **Live Kamera-Stream** mit Status-Anzeige (Verbunden/Getrennt)
*   **FPS-Counter** für Vision-Performance
*   **Face Detection Overlay** mit Name und Trust-Score
*   **Biometrie & Stimmung** Anzeige (Energie, Aufregung, Komfort)
*   **Kinematik-Monitor** mit 2D Bein-Visualisierung
*   **SLAM-Karte** mit Roboter-Position und Hindernissen
*   **Soziales Gedächtnis** mit Face-Cards und Trust-Verlauf
*   **Servo-Kalibrierung** mit Live-Mittelwerte
*   **MQTT-Konfiguration** für Home Assistant

### API Endpoints
| Endpoint | Methode | Beschreibung |
|----------|---------|-------------|
| `/api/status` | GET | Robot-Status (Battery, Pose, Mood, detected_face) |
| `/api/config` | GET/PUT | Konfiguration lesen/schreiben |
| `/api/camera_stream` | GET | MJPEG Video-Stream |
| `/api/move` | POST | Bewegungsbefehle |
| `/api/faces` | GET | Face-Datenbank |
| `/api/map` | GET | SLAM-Kartendaten |
| `/api/markers` | GET/POST/DELETE | Aruco-Marker |
