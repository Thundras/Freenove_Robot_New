# Bewegungskontrolle: Benutzerhandbuch

Dieses Dokument erklärt, wie die Bewegungen des Roboters gesteuert werden können.

## Grundkonzepte

### Gangarten
Der Roboter unterstützt aktuell zwei Haupt-Gangarten:
1.  **Trot (Standard):** Eine schnelle, dynamische Gangart, bei der sich die Beine abwechselnd diagonal bewegen. Ideal für schnelles Vorankommen.
2.  **Walk:** Eine langsamere, stabilere Gangart, bei der immer nur ein Bein gleichzeitig angehoben wird. Ideal für unebenes Gelände oder präzise Manöver.

### Beschleunigung (Ramping)
Der Roboter beschleunigt und bremst automatisch sanft ab. Du musst dich nicht um plötzliche Ruckler kümmern, wenn du die Zielgeschwindigkeit änderst.

## Fernsteuerung (Übersicht)
Die Steuerung erfolgt über das Dashboard oder MQTT (siehe Connectivity-Doku).
*   **Vorwärts/Rückwärts:** Ändert die `step_length`.
*   **Höhe:** Kann über die `base_height` in der Konfiguration oder live angepasst werden.
