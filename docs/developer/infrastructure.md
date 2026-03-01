# Infrastruktur & System-Integration

Diese Dokumentation beschreibt, wie das System gestartet, erweitert und verwaltet wird.

## 1. Plugin-System
Um den Roboter zu erweitern, ohne den Kern-Code zu ändern, nutzen wir ein dynamisches Plugin-System.

*   **Plugin-Verzeichnis:** `/plugins`
*   **Ablauf:** Alle `.py` Dateien in diesem Ordner werden beim Start automatisch geladen.
*   **Voraussetzung:** Jedes Plugin muss eine Funktion `initialize(context)` bereitstellen. Der `context` ist das `RobotDog`-Objekt, worüber das Plugin Zugriff auf alle Subsysteme (IK, Gait, MQTT) hat.

## 2. Autostart (systemd)
Auf dem Raspberry Pi nutzen wir `systemd`, um sicherzustellen, dass die Software nach dem Booten automatisch startet.

### Installation:
1.  Kopiere `freenove_dog.service` nach `/etc/systemd/system/`.
2.  Aktiviere den Dienst: `sudo systemctl enable freenove_dog.service`
3.  Starte den Dienst: `sudo systemctl start freenove_dog.service`

## 3. Logging
Das System nutzt das Python `logging` Modul. Im Standard-Modus werden alle wichtigen Ereignisse (Treiber-Start, MQTT-Verbindung, BT-Entscheidungen) auf der Konsole ausgegeben und können via `journalctl -u freenove_dog.service` eingesehen werden.

## 4. Konfiguration
Die zentrale Schnittstelle für alle Hardware- und Systemparameter ist die `config/config.yaml`. Hier werden Servo-Offsets, I2C-Adressen und Netzwerk-Einstellungen verwaltet.
