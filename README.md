# Freenove Robot Dog Project - New Development

Dies ist das zentrale Dokumentationsverzeichnis für das neue Projekt basierend auf dem Freenove Robot Dog Kit. Hier werden alle Erkenntnisse, Planungen und Brainstorming-Ergebnisse festgehalten.

## Projektübersicht
Der Roboter ist ein vierbeiniger Roboterhund (Quadruped), der von einem Raspberry Pi gesteuert wird. Die Bewegungen basieren auf inverser Kinematik, und die Fernsteuerung erfolgt über ein TCP-Protokoll.

## Inhaltsverzeichnis
* [Hardware Spezifikationen](docs/hardware_specs.md) - Details zu Sensoren und Aktoren.
* [Software Architektur](docs/software_architecture.md) - Steuerungslogik, Vision-Pipeline & Social Memory.
* [Brainstorming & Ideen](docs/brainstorming_ideas.md) - Sammlung von Features und Erweiterungen.
* [Entwicklungs-Roadmap](docs/development_roadmap.md) - Strategische Planung & Fortschritt.

## Key Features (Abgeschlossen)
*   **Modulare SAL:** Hardware-Abstraktion für stabilen Betrieb und Simulation.
*   **Perzeption & Vision:** Hochfrequente Objekterkennung (YuNet/SFace) in eigenem Prozess.
*   **Soziales Gedächtnis:** Multi-View Gesichtserkennung mit persistentem Speicher und Foto-Capture.
*   **Trust-System:** Dynamisches Vertrauens-Level basierend auf Kontaktzeit.
*   **Web Dashboard:** Moderne Steuerung mit Live-Feed und Social-Memory Management.

## Wichtige Regeln
* Keine Änderungen am Original-Code im Quellordner `Freenove_Robot_Dog_Kit_for_Raspberry_Pi` vornehmen.
* Alle neuen Entwicklungen, Dokumentationen und Code-Stubs finden ausschließlich im Ordner `freenove_robot_new` statt.
