# Gait Sequencing Dokumentation

Dieses Dokument beschreibt die Implementierung der Gangarten-Steuerung (Gait Sequencing) für den Freenove Robot Dog.

## Prinzip: Timeline-Oszillatoren
Anstatt eine feste State Machine zu nutzen, basiert die Bewegung auf unabhängigen Oszillatoren für jedes Bein. Jeder Oszillator läuft in einer Phase von $0.0$ bis $1.0$.

### Phasen-Einteilung
*   **0.0 bis 0.5 (Swing Phase):** Das Bein hebt ab, bewegt sich nach vorne und setzt wieder auf.
*   **0.5 bis 1.0 (Stance Phase):** Das Bein bleibt am Boden und drückt den Körper nach vorne (Bewegung nach hinten relativ zum Körper).

## Gangarten (Gaits)
Die verschiedenen Gangarten werden durch unterschiedliche Phasen-Offsets zwischen den Beinen definiert.

### 1. Trot (Trab)
Diagonal gegenüberliegende Beine bewegen sich synchron.
*   Vorne-Links (FL) & Hinten-Rechts (RR): Phase 0.0
*   Vorne-Rechts (FR) & Hinten-Links (RL): Phase 0.5

### 2. Walk (Schritt)
Die Beine bewegen sich nacheinander in einer festen Sequenz.
*   Phasen-Offsets: 0.0, 0.25, 0.5, 0.75

## Ramping (Beschleunigung)
Um mechanischen Stress zu vermeiden und flüssige Übergänge zu gewährleisten, wird die Geschwindigkeit (`current_speed`) nicht sofort gesetzt, sondern über eine Rampe an die Zielgeschwindigkeit angepasst.

## Implementierung
Die Logik befindet sich in `movement/gait.py`. Die Funktion `get_coordinates` berechnet die (x, y, z) Position relativ zum Schultergelenk basierend auf der aktuellen Phase.
