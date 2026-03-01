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
    
    Vision -->|Detection Events / Tilt Requests| Queue[(Result Queue)]
    Queue -->|Process Requests| Intel[Intelligence Controller]
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

### C. Intelligenz (Behavior Trees)
Anstelle einer komplexen State-Machine nutzen wir **Behavior Trees**. Dies erlaubt eine klare Priorisierung:
1.  **Safety**: Hindernisvermeidung (Ultrasonic).
2.  **Security**: Alarm-Modus (Personenerkennung).
3.  **Interaction**: Verfolgen von Personen, Gestensteuerung.
4.  **Social/Idle**: Interaktion mit anderen Hunden, Spieltrieb.

## 3. Kommunikation & Connectivity
*   **MQTT (Home Assistant):** Bietet Auto-Discovery für Sensoren und Schalter.
*   **Web-Server:** Streamt den stabilisierten MJPEG-Feed und bietet ein Notfall-Dashboard.
