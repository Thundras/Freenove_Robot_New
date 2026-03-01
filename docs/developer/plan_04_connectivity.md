# Punkt 4: Home Assistant & Connectivity - Detailplanung

Dieser Teil stellt die Brücke zur Außenwelt dar. Wir wollen den Roboter weg von der starren App hin zu einer offenen Smart-Home-Komponente führen.

## 1. MQTT-Schnittstelle (Die Hauptader)
MQTT ist das stabilste und am weitesten verbreitete Protokoll für Smart-Home-Integrationen.
*   **Auto-Discovery:** Der Roboter sendet beim Start spezielle Konfigurations-Topics, damit er in Home Assistant sofort als Gerät mit allen Entitäten erscheint.
*   **Telemetrie (Sensoren):** 
    *   Batteriespannung & Prozent.
    *   Aktuelle Pose & Modus.
    *   Entfernungswert (Ultraschall).
    *   System-Status (CPU Last, Temperatur).
*   **Befehle (Aktoren):**
    *   Licht-Steuerung (LEDs).
    *   Buzzer.
    *   Modus-Wahl (Auto, Manuel, Sitzen, Parken).
    *   Direkte Fernsteuerung (Bewegungs-Vektoren).

## 2. Modernes Web-Dashboard (Direct Control)
Für die direkte Steuerung ohne Smart-Home-Server:
*   **Technologie:** Ein kleiner Webserver (z.B. FastAPI oder Flask) mit Websockets für Realtime-Daten.
*   **Features:** Live-Kamera-Stream, virtuelle Joysticks, Kalibrierungs-Interface für die Servos.

## 3. Video-Streaming
*   **WebRTC oder MJPEG:** Für minimale Latenz beim Fahren.
*   **Privacy:** Stream nur aktiv, wenn ein Client verbunden ist oder der BT "Wachhund-Modus" aktiv ist.

## 4. System-Design Entscheidungen (Fixiert)
*   **Sicherheit:** Kein Passwortschutz für Web-Dashboard/MQTT (Betrieb ausschließlich im gesicherten Intranet).
*   **Protokoll:** MQTT via Mosquitto/Home Assistant Broker.
*   **Discovery:** Home Assistant Auto-Discovery für alle Sensoren und Schalter.

---
*Status: Detailplanung für Connectivity (Punkt 4) vollständig abgeschlossen.*
