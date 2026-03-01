# Freenove Robot Dog Project - New Development

Dies ist das zentrale Dokumentationsverzeichnis für das neue Projekt basierend auf dem Freenove Robot Dog Kit. Hier werden alle Erkenntnisse, Planungen und Brainstorming-Ergebnisse festgehalten.

## Projektübersicht
Der Roboter ist ein vierbeiniger Roboterhund (Quadruped), der von einem Raspberry Pi gesteuert wird. Die Bewegungen basieren auf inverser Kinematik, und die Fernsteuerung erfolgt über ein TCP-Protokoll.

## Inhaltsverzeichnis
* [Hardware Spezifikationen](docs/hardware_specs.md) - Details zu Sensoren und Aktoren.
* [Software Architektur](docs/software_architecture.md) - Steuerungslogik und Kommunikation.
* [Brainstorming & Ideen](docs/brainstorming_ideas.md) - Sammlung von Features und Erweiterungen.
* [Entwicklungs-Roadmap](docs/development_roadmap.md) - Strategische Planung der Neuentwicklung.
    * [Detailplanung SAL](docs/software_architecture.md) - Punkt 1 der Neuentwicklung.
    * [Detailplanung Bewegungs-Engine](docs/developer/plan_02_movement.md) - Punkt 2 der Neuentwicklung.
    * [Detailplanung Intelligenz](docs/developer/plan_03_intelligence.md) - Punkt 3 der Neuentwicklung.
    * [Detailplanung Connectivity / HA](docs/developer/plan_04_connectivity.md) - Punkt 4 der Neuentwicklung.
    * [Detailplanung Infrastruktur](docs/developer/plan_05_infrastructure.md) - Punkt 5 der Neuentwicklung.

## Wichtige Regeln
* Keine Änderungen am Original-Code im Quellordner `Freenove_Robot_Dog_Kit_for_Raspberry_Pi` vornehmen.
* Alle neuen Entwicklungen, Dokumentationen und Code-Stubs finden ausschließlich im Ordner `freenove_robot_new` statt.
