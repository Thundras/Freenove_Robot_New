# 💻 Lokales Testen am PC

Da das Projekt eine vollständige Hardware-Abstraktionsschicht (SAL) besitzt, kannst du den Großteil der Software direkt auf deinem PC entwickeln und testen, ohne einen echten Roboter zu besitzen.

## 1. Voraussetzungen
Stelle sicher, dass du eine Python-Umgebung (3.10+) eingerichtet hast.
```bash
# Optional: Virtuelle Umgebung erstellen
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Abhängigkeiten installieren (die meisten PC-kompatiblen)
pip install -r requirements.txt
```

---

## 2. Simulations-Modus (Mock Mode)
In der Datei `config/config.yaml` muss folgender Wert gesetzt sein:
```yaml
system:
  simulation_mode: true
```
Wenn du nun `python main.py` startest:
*   Werden keine I2C-Fehler geworfen.
*   Alle Servo-Befehle werden nur in die Konsole geloggt (`INFO: MockServoController initialized`).
*   Sensordaten (Akku, IMU, Ultraschall) liefern statische "Mock"-Werte.
*   Die KI (Vision) versucht deine PC-Webcam zu nutzen, falls vorhanden.

---

## 3. Automatisierte Tests ausführen
Wir nutzen `pytest` für die Qualitätssicherung. Du kannst alle Tests mit einem Befehl starten:

```bash
# Alle Tests ausführen
python -m pytest tests/

# Nur einen bestimmten Test (z.B. die neuen Features)
python -m pytest tests/test_milestone_features.py -v
```

### Was wird getestet?
*   **IK-Mathe:** Rechnet der Roboter die Beinwinkel für (x,y,z) korrekt aus?
*   **Gait Logic:** Funktionieren die Oszillatoren für Trot/Walk?
*   **Behavior Trees:** Reagiert das Gehirn korrekt auf Sensordaten (z.B. "Ball gefunden" -> LEDs grün?)
*   **Infrastruktur:** Lädt der Plugin-Loader korrekt?

---

## 4. Debugging Tipps
*   **Log-Level:** Setze `log_level: "DEBUG"` in der `config.yaml`, um jeden einzelnen Schritt des Behavior Trees und der Servos zu sehen.
*   **Visualisierung:** Die Koordinaten der Beine werden in den Logs ausgegeben. Du kannst prüfen, ob sich die Z-Werte beim Laufen rhythmisch ändern.
*   **Web-Dashboard:** Wenn du `main.py` startest, kannst du das Dashboard unter `http://localhost:5000` aufrufen und Befehle simulieren.
