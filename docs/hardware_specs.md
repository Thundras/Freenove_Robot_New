# Hardware Spezifikationen

Präzise Auflistung der im Freenove Robot Dog verbauten Hardware-Komponenten.

## Aktoren (Ausführung)
| Komponente | Anzahl | Typ / Modell | Funktion |
| :--- | :--- | :--- | :--- |
| Beinservos | 12 | ES08MA Ⅱ | 3 Gelenke pro Bein (Hüfte, Oberbein, Unterbein) |
| Kopfservo | 1 | S90 | Drehung des Kopfmoduls (Horizont) |
| RGB-LEDs | 7 | WS2812 (NeoPixel) | Visuelle Effekte, Statusanzeigen |
| Buzzer | 1 | Aktiver Summer | Akustische Signale |

## Sensoren (Wahrnehmung)
| Komponente | Modell | Schnittstelle | Nutzen |
| :--- | :--- | :--- | :--- |
| Kamera | OV5647 | CSI | Video-Streaming, Bilderkennung (OpenCV) |
| IMU (6-Achsen) | MPU6050 | I2C | Gleichgewicht, Neigungserkennung |
| Ultraschall | HC-SR04 | GPIO | Distanzmessung (2cm - 400cm) |
| Spannungssensor | ADS7830 | I2C | Überwachung der Akkuspannung (Shutdown bei < 6.4V) |

## Elektronik
* **Raspberry Pi:** Zentrale Recheneinheit (empfohlen: Pi 5 / 4B / 3B+).
* **Robot Shield:** Hauptplatine für Energieverteilung und Anschlüsse.
* **PCA9685:** 16-Kanal PWM-Treiber (I2C) für die Servosteuerung.
* **Stromversorgung:** 2x 18650 Li-ion Batterien (3.7V).
