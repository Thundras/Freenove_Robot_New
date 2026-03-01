# Inbetriebnahmeanleitung: Erstmals Kalibrieren

Nachdem die neue Software auf dem Raspberry Pi installiert wurde, müssen die Servomittelpunkte (Offsets) einmalig eingestellt werden, da jedes Servo-Horn mechanisch leicht versetzt aufgesteckt sein kann.

## 1. Vorbereitung
*   Stelle den Hund auf einen **Bock** oder lege ihn auf den Rücken, sodass die Beine in der Luft hängen. Das verhindert ruckartige Bewegungen am Boden.
*   Stelle sicher, dass in der `config.yaml` alle `middle`-Werte auf `90` stehen.

## 2. Das Kalibrierungs-Tool (CLI)
Wir werden ein spezielles Skript `utils/calibrate_servos.py` bereitstellen. Dieses Tool erlaubt es dir, jeden Servo einzeln anzusteuern:

### Ablauf:
1.  **Start:** `python utils/calibrate_servos.py --leg fl --joint femur`
2.  **Feinjustierung:** Du kannst mit den Pfeiltasten (oder Eingabe von Werten) den Servo in 1-Grad-Schritten bewegen.
3.  **Optische Prüfung:** Bewege den Servo so lange, bis das Beinsegment exakt die gewünschte Ausrichtung hat (z.B. Femur exakt 90 Grad zum Körper).
4.  **Speichern:** Das Tool zeigt dir den finalen Wert an (z.B. `94`). Diesen trägst du in die `config.yaml` unter `middle` ein.

## 3. Alternative: Dashboard-Kalibrierung
Sobald **Meilenstein 3 (Connectivity)** abgeschlossen ist, kannst du dies bequem über das Web-Interface erledigen:
*   Dort gibt es Schieberegler für jeden Servo.
*   Du schiebst den Regler so lange, bis das Bein perfekt steht.
*   Ein Klick auf "Save as Middle" schreibt den Wert dauerhaft in die Config-Datei.

## 4. Wichtige Tipps
*   **Reihenfolge:** Kalibriere immer erst die Coxa (Schulter), dann den Femur (Oberschenkel) und zuletzt die Tibia (Unterschenkel).
*   **Symmetrie:** Die Werte der linken und rechten Seite sollten sich (wenn der Hund perfekt gebaut ist) ähneln, können aber aufgrund der Fertigungstoleranzen leicht abweichen.

## 5. Orientierungshilfe: Typische Offset-Werte
Falls du unsicher bist, hier sind Erfahrungswerte für ein frisch zusammengebautes Freenove-Kit:

| Gelenk | Typischer Offset | Erwartete Position | 
| :--- | :--- | :--- |
| **Coxa** | 85 - 95 | Bein steht im 90° Winkel zum Gehäuse |
| **Femur** | 90 - 105 | Oberschenkel zeigt senkrecht nach unten |
| **Tibia** | 80 - 100 | Unterschenkel bildet 90° Winkel zum Oberschenkel |

*Hinweis: Werte außerhalb von 70-110 deuten oft darauf hin, dass das Servo-Horn mechanisch um einen Zahn versetzt aufgesteckt wurde. Es empfiehlt sich dann, das Horn abzuschrauben und mittiger neu aufzustecken.*
