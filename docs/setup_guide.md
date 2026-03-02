# Setup Guide (Robot 2.0)

Dieses Dokument beschreibt die notwendigen Schritte, um die Robot 2.0 Software auf dem **Entwicklungsrechner (Windows)** und dem **Zielsystem (Raspberry Pi)** zu installieren.

> [!IMPORTANT]
> Dieses Projekt wird auf Windows entwickelt, läuft aber produktiv auf einem Raspberry Pi. Achte auf die plattformspezifischen Unterschiede bei den Abhängigkeiten.

## 1. Systemvoraussetzungen
*   **Betriebssystem:** Windows 10/11 (Entwicklung) oder Raspberry Pi OS (Produktion).
*   **Python:** Version 3.9 (empfohlen).

## 2. Dependencies installieren

Die Abhängigkeiten sind in der `requirements.txt` festgeschrieben. Insbesondere auf Windows ist die Einhaltung dieser Versionen kritisch, um Konflikte zwischen MediaPipe, TensorFlow und Protobuf zu vermeiden.

```powershell
pip install -r requirements.txt --user
```

**Wichtige Versionen (Windows Fix):**
*   `numpy==1.26.4` (Verhindert "Numpy 2.0" Inkompatibilität mit MediaPipe)
*   `mediapipe==0.10.32` (Modernes Tasks API Bundle)
*   `protobuf==6.33.5` (Zwingend erforderlich für moderne TF/MediaPipe Kombinationen)

## 3. Modelle & Ressourcen

Da wir auf die moderne **MediaPipe Tasks API** umgestiegen sind, wird eine spezifische Modell-Datei benötigt:

1.  Die Datei `hand_landmarker.task` muss im Verzeichnis `brain/models/` liegen.
2.  **Download Link:** [hand_landmarker.task](https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task)

## 4. Startvorgang

Das System wird über die zentrale `main.py` gestartet:

```powershell
python main.py
```

### Logging & Debugging
Die Logs sind so konfiguriert, dass sie beim Start detaillierte Informationen über die Hardware-Initialisierung und die KI-Module ausgeben:
- Das Logging wird in `main.py` am Anfang initialisiert (`force=True`), um library-spezifische Overrides zu verhindern.
- Interne Warnungen von Bibliotheken (z.B. TensorFlow/absl) werden auf ein Minimum reduziert, um die Konsole sauber zu halten.

## 5. Deployment auf dem Raspberry Pi (Zielsystem)

Für den produktiven Einsatz am Roboter:

1.  **Betriebssystem:** Verwende ein **64-bit Raspberry Pi OS** (Bookworm empfohlen).
2.  **Kamera:** Stelle sicher, dass das Legacy Camera Interface deaktiviert ist (für `libcamera`/MediaPipe Support).
3.  **Installation:**
    ```bash
    pip install -r requirements.txt
    ```
    *Hinweis:* Auf dem Pi werden automatisch die ARM64-Wheels geladen. Die in der `requirements.txt` fixierten Versionen sind mit dem Pi 4/5 kompatibel.

4.  **Hardware-Treiber:** Stelle sicher, dass I2C aktiviert ist (`raspi-config`). Die `adafruit-circuitpython` Bibliotheken benötigen Root-Rechte oder entsprechende Gruppen-Mitgliedschaften (`gpio`, `i2c`).

---

## 6. Trust-System zurücksetzen (optional)
Wenn du sofort Gesten testen willst, ohne erst Kontaktzeit aufzubauen:
- Gehe in `config/config.yaml`
- Setze `system.gesture_trust_threshold: 0.0`
- Starte den Roboter neu.
