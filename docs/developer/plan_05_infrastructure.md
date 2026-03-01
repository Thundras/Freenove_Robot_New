# Punkt 5: System-Infrastruktur & Plugins - Detailplanung

Dieser Bereich sorgt dafür, dass die Software stabil läuft und in Zukunft einfach erweitert werden kann.

## 1. Plugin-Architektur (Erweiterbarkeit)
Das System soll so gebaut sein, dass man neue Funktionen hinzufügen kann, ohne den Kern-Code zu ändern.
*   **Hooks:** Kern-Ereignisse (z.B. `pre_move`, `on_sensor_update`), in die sich Plugins einklinken können.
*   **Beispiele:** Ein Plugin für "Sprachausgabe" oder ein "Zusatz-Sensor-Modul".

## 2. State Management & Persistenz
*   **Zentraler Status (The Source of Truth):** Ein Objekt, das den kompletten aktuellen Zustand des Hundes kennt.
*   **Konfigurations-Handling:** Alle Einstellungen (Servos, WLAN, HA-Login) liegen in einer sauberen `config.yaml`.

## 3. Logging & Diagnose
*   **File Logging:** Speichern von Fehlern auf dem Pi zur späteren Analyse.
*   **Realtime-Logs:** Übertragung wichtiger Logs via Websocket an das Web-Dashboard.

## 4. Software-Update Prozess
*   Möglichkeit, den Roboter via Web-Interface oder Git-Befehl zu aktualisieren.

## 5. System-Design Entscheidungen (Fixiert)
*   **Autostart:** Implementierung als `systemd` Service (Startet automatisch beim Booten).
*   **Konfigurations-Format:** Konsequente Nutzung von **YAML** für alle Einstellungen (Kalibrierung, Hardware-Parameter, WIFI).
*   **Stabilität:** Watchdog-Prozess, der bei Software-Hängern automatisch neu startet.

---
*Status: Detailplanung für Infrastruktur (Punkt 5) vollständig abgeschlossen.*
