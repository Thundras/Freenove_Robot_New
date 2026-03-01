# Kalibrierungs-Konzept (Servo-Offsets)

In der originalen Software wurde die Kalibrierung über eine `point.txt` gelöst, die Differenz-Werte speicherte. In der Neuentwicklung nutzen wir einen transparenteren Ansatz direkt in der **Software Abstraction Layer (SAL)**.

## 1. Trennung von Mathematik und Hardware
Wir trennen strikt zwischen "idealen" Winkeln und "Hardware"-Signalen:
*   **Bewegungs-Engine:** Berechnet den mathematisch perfekten Winkel (z.B. 0° für "exakt gerade").
*   **SAL (Servo-Treiber):** Liest diesen Winkel und rechnet ihn in den passenden PWM-Wert für den Servo um, unter Berücksichtigung der individuellen Mechanik.

## 2. Die `config.yaml` Lösung
Für jeden Servo speichern wir in der `config.yaml` folgende Werte:
```yaml
leg_fl:
  coxa:  { channel: 0, middle: 92, min: 20, max: 160, inverted: false }
```

### Bedeutung der Parameter:
*   **middle:** Dies ist der "Nullpunkt". Wenn die IK sagt "0 Grad", sendet der Treiber den PWM-Wert für 92 Grad. Damit gleichen wir schief aufgesteckte Servo-Hörner aus.
*   **inverted:** Wenn ein Servo mechanisch spiegelverkehrt eingebaut ist (was beim Hund links/rechts oft der Fall ist), sorgt dieses Flag dafür, dass ein "positiver" Winkelbefehl auch die richtige Richtung bewirkt.
*   **min/max:** Software-seitige Anschläge, um mechanische Blockaden und Schäden zu verhindern.

## 3. Der Mapping-Prozess
Der Prozess im Code sieht so aus:
1.  **Input:** IK berechnet Winkel $\theta_{math}$.
2.  **Invertierung:** Falls `inverted: True`, dann $\theta = -\theta_{math}$.
3.  **Offset:** $\theta_{final} = middle + \theta$.
4.  **Clamping:** Sicherstellen, dass $\theta_{final}$ zwischen `min` und `max` liegt.
5.  **Output:** Senden an den PCA9685.

## Vorteil gegenüber dem Original
*   **Lesbarkeit:** Man sieht in der Config sofort, welcher Servo wie stark korrigiert wurde.
*   **Einfachheit:** Kein Hantieren mit Differenz-Listen (`point.txt`). Ein `middle: 90` bedeutet "perfekt gerade", ein `middle: 95` bedeutet "5 Grad Versatz".
*   **Sicherheit:** Die `min/max` Limits schützen die Hardware auf der untersten Ebene, egal was die Intelligenz befiehlt.
