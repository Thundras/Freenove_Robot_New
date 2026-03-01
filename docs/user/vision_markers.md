# ArUco Marker Benutzerhandbuch

Damit dein Roboter-Hund seine Umgebung visuell kartieren und die Ladestation finden kann, nutzt er **ArUco Marker**. Hier erfährst du, welche Version du benötigst und wie du sie einsetzt.

## 1. Der Standard: DICT_4X4_50
Wir nutzen den **4x4_50** Standard. Das bedeutet:
*   **4x4:** Das Muster besteht aus 4x4 schwarzen/weißen Quadraten. Dies ist für den Raspberry Pi ideal, da es auch bei geringerer Kamera-Auflösung sehr schnell und zuverlässig erkannt wird.
*   **50:** Es gibt 50 verschiedene IDs (0 bis 49), die der Hund unterscheiden kann.

## 2. Marker erstellen
Du kannst die Marker kostenlos online generieren und ausdrucken.
*   **Empfohlene Seite:** [ArUco Marker Generator](https://chev.me/arucogen/)
*   **Einstellungen:**
    *   **Dictionary:** 4x4 (50 markers)
    *   **Marker ID:** Wähle eine ID (z.B. ID 0 für die Ladestation, ID 1-10 für Räume).
    *   **Marker Size:** 100mm (10cm) ist ein guter Allrounder für Distanzen bis zu 2-3 Metern.

## 3. Bedeutung der IDs (Vorschlag)
Du kannst in der `config.yaml` festlegen, welche ID was bedeutet. Ein gängiger Standard im System ist:
*   **ID 0:** Home-Base / Ladestation (Virtual Docking Ziel)
*   **ID 1-10:** Fixpunkte in der Wohnung (Wände, Türen) zur Re-Lokalisierung.
*   **ID 11-20:** Bewegliche Objekte (z.B. Spielzeug des Hundes).

## 4. Platzierung
*   Bringe die Marker auf Augenhöhe des Roboters an (ca. 10-15 cm über dem Boden).
*   Achte darauf, dass die Marker flach auf Oberflächen kleben und nicht gewölbt sind, da dies die Entfernungsberechnung verzerren kann.

## 5. Tipps für beste Erkennung (Profi-Intervall)
*   **Beleuchtung:** ArUco Marker benötigen einen klaren Kontrast. Vermeide direkte Spiegelungen durch Lampen (Glanzeffekte auf Papier). Mattes Papier ist ideal.
*   **Umgebung:** In sehr dunklen Räumen sinkt die Framerate der Kamera, was die Erkennung erschwert. Eine indirekte Beleuchtung des Markers verbessert die Stabilität massiv.
*   **Distanzen:** 
    *   **Nahbereich (< 50cm):** Marker kann zu groß für das Sichtfeld werden.
    *   **Optimal (100cm - 200cm):** Beste Balance zwischen Präzision und Sichtbarkeit.
    *   **Fernbereich (> 300cm):** Benötigt größere Marker (ca. 15-20cm) oder eine höhere Auflösung in der `config.yaml`.
