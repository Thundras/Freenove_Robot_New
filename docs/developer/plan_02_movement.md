# Punkt 2: Bewegungs-Engine (IK & Gaits) - Detailplanung

Dieser Teil der Software berechnet, wie der Hund seine 12 Gelenke bewegen muss, um eine bestimmte Pose oder Bewegung auszuführen.

## 1. Mathematische Basis: Inverse Kinematik (IK)
Wir implementieren die IK neu, um sanftere Übergänge zu ermöglichen.
*   **Koordinatensystem:** Festlegung eines stabilen Körper-Nullpunkts (Center of Mass).
*   **Gelenk-Limits:** Hard-coded Software-Limits im IK-Modell, um mechanische Blockaden zu verhindern.
*   **Interpolation:** Nutzung von Bezier-Kurven oder Sinus-Interpolation für die Fuß-Trajektorien (verhindert ruckartige Bewegungen beim Laufen).

## 2. Gangarten (Gait Sequencer)
Ein modularer Sequencer soll verschiedene Laufmuster ermöglichen:
*   **Walk:** Statisch stabil (immer 3 Füße am Boden).
*   **Trot (Trab):** Dynamisch stabil (diagonale Beinpaare bewegen sich gleichzeitig).
*   **Crawl:** Sehr langsame, präzise Bewegung.
*   **Spezial-Posen:** "Sitz", "Platz", "Geben Pfote".

## 3. Stabilisierung & Sensor-Feedback
Die Engine soll aktiv auf die IMU-Daten aus dem SAL reagieren:
*   **Active Balancing:** Der Körper neigt sich aktiv gegen eine Schräglage des Untergrunds.
*   **Impact Detection:** Erkennung, wenn ein Bein den Boden früher oder später als erwartet berührt (via Servo-Last oder Beschleunigung).

## Getroffene Entscheidungen (Endgültige Strategie)
1.  **Mathe-Library:** Native `math`-Library (Kein numpy) für maximale Portabilität.
2.  **Kalibrierung:** Zentrale `config.yaml` für Offsets und Hardware-Limits.
3.  **Gait-Sequencing:** Flexibles **Timeline-Modell**. Jedes Bein wird als unabhängiger Oszillator gesteuert, was stufenlose Geschwindigkeits- und Gangartenwechsel ermöglicht.
4.  **Bewegungs-Qualität:** 
    *   **Ramping:** Sanfte Beschleunigung und Verzögerung bei jedem Start/Stopp.
    *   **Kollisionsschutz:** Software-seitiger Check im IK-Modell gegen mechanische Anschläge.
    *   **Hertz-Zahl:** Interner Control-Loop mit **100 Hz** für extrem flüssige Bewegungsabläufe.

---
*Status: Detailplanung für Bewegungs-Engine (Punkt 2) abgeschlossen. Bereit für Punkt 3.*

---
*Status: Strategie für Bewegungs-Engine (IK ohne numpy) festgelegt. Fokus nun auf Posen-Management.*
