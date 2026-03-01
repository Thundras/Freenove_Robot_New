# Punkt 3: Intelligenz & Behavior Trees - Detailplanung

Vom ferngesteuerten Roboter zum autonomen Agenten. Hier planen wir, wie der Hund eigene Entscheidungen trifft.

## 1. Verhaltens-Architektur: Behavior Trees (BT)
Wir nutzen Behavior Trees anstelle komplexer "If-Else"-Ketten.
*   **Vorteil:** Modulare Verhaltensweisen, die einfach kombiniert werden können.
*   **Kern-Knoten:** 
    *   *Selectors:* Versuche A, wenn das nicht geht, versuche B.
    *   *Sequences:* Mach erst A, dann B, dann C.
*   **Beispiel-Baum:** `WENN Batterie niedrig -> SUCHE Ladestation -> SONST WENN Hindernis -> WEICHE AUS -> SONST ERKUNDE Raum`.

## 2. Sensor-Fusion & Wahrnehmung
Die Intelligenz nutzt die aufbereiteten Daten aus dem SAL:
*   **Abstrakte Zustände:** Der BT arbeitet nicht mit "Entfernung 10cm", sondern mit Zuständen wie `IsObstacleAhead`.
*   **Vision-Input:** Einbindung von OpenCV zur Erkennung von (z.B.) QR-Codes (für die Ladestation) oder Gesichtern.

## 3. Kartierung & Navigation (SLAM Light)
*   **Occupancy Grid Map:** 2D-Karte aus Schritten und Ultraschall.
*   **Objekterkennung:** Integration von Person- und Haustier-Erkennung (z.B. via TFLite/MobileNet).
*   **Gestenerkennung:** Erkennung von Handzeichen (z.B. "Herkommen", "Weggehen") zur Steuerung des Follow-Verhaltens.
*   **Idle Animation:** Implementierung einer subtilen "Atmung" oder Wiegebewegung im Stillstand.
*   **Visual Landmarks:** Re-Lokalisierung via QR/Bild-Marker.
*   **Persistent Memory:** Speichern der Karte für dauerhafte Orientierung.

## 4. Docking & Ladestation (Exkurs)
Da die Hardware keine Ladekontakte hat, wäre ein "echtes" Docking ein Hardware-Addon. Softwareseitig planen wir die Logik dennoch ein:
*   **Anflug:** Erkennung eines speziellen Markers (z.B. Aruco-Tag) an der Station aus >2m Entfernung.
*   **Feinausrichtung:** Vision-basierte PID-Regelung, um den Hund zentimetergenau vor die Kontakte zu steuern.
*   **Validierung:** Prüfung des Ladestroms (via ADS7830), um ein erfolgreiches Docking zu bestätigen.

## 5. System-Design Entscheidungen (Fixiert)
*   **Vision-Prozess:** Das Vision-System (OpenCV, Landmark-Erkennung) läuft in einem **unabhängigen Prozess** (via `multiprocessing`), um die Motorik-Frequenz (100Hz) niemals zu beeinträchtigen.
*   **Verhaltens-Steuerung:** Entscheidung für eine **Custom Lightweight Behavior Tree Engine**.
    *   *Begründung:* Maximale Kontrolle, keine externen Abhängigkeiten, passgenau für die 5-10 Kern-Verhaltensweisen des Roboters.
*   **Mapping-Strategie:** Fokus auf **Visual Landmarks** (QR-Codes/Aruco-Tags) für eine robuste und CPU-schonende Re-Lokalisierung in der Wohnung.

---
*Status: Detailplanung für Intelligenz (Punkt 3) vollständig abgeschlossen. Bereit für die Umsetzung.*
