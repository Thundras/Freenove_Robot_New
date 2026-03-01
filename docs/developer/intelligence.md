# Intelligenz & Verhalten (Behavior Trees)

Diese Dokumentation beschreibt die Entscheidungs-Logik und die Wahrnehmung des Roboters.

## 1. Architektur-Übersicht
Die Intelligenz des Roboters ist in zwei Hauptkomponenten unterteilt:
*   **Vision-Prozess:** Ein separater Prozess für rechenintensive Bildverarbeitung (z.B. Marker-Erkennung).
*   **Behavior Tree (BT):** Die zentrale Entscheidungsinstanz, die Sensordaten und Vision-Ergebnisse verarbeitet.

## 2. Der Behavior Tree (BT)
Wir nutzen eine hybride Architektur aus Condition- und Action-Nodes.

### Knoten-Typen:
*   **Selector (OR):** Versucht seine Kinder nacheinander auszuführen. Sobald eines erfolgreich ist, bricht er ab und meldet Erfolg. (Ideal für Priorisierungen).
*   **Sequence (AND):** Führt alle Kinder nacheinander aus. Wenn eines fehlschlägt, bricht er ab.

### Aktueller Entscheidungs-Baum:
1.  **AvoidObstacles (Priorität 1):** Prüft Ultraschall-Daten. Wenn ein Hindernis nah ist, wird eine Ausweich-Bewegung eingeleitet.
2.  **ExploreRoom (Priorität 2):** Fallback-Verhalten, das den Roboter einfach vorwärts laufen lässt.

## 3. Vision-Integration (Multiprocessing)
Der Vision-Prozess kommuniziert über eine `multiprocessing.Queue` mit dem Gehirn. Dies stellt sicher, dass die 100Hz Motor-Steuerung niemals durch eine langsame Bildverarbeitung (z.B. 10Hz) blockiert wird.

### Datenfluss:
`Kamera -> VisionProcess -> Queue -> IntelligenceController -> Behavior Tree`

## 4. Navigation (Ausblick)
In zukünftigen Versionen wird der BT um SLAM-Nodes erweitert, die eine 2D-Karte (`Occupancy Grid`) aufbauen und zur Navigation nutzen.
