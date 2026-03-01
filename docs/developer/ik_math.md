# Inverse Kinematik (IK) Dokumentation

Dieses Dokument beschreibt die mathematische Herleitung der Inversen Kinematik für den Freenove Robot Dog.

## Beingeometrie
Jedes Bein besteht aus drei Segmenten:
1.  **Coxa (l1):** Der seitliche Versatz vom Körper zum Schultergelenk.
2.  **Femur (l2):** Der Oberschenkel.
3.  **Tibia (l3):** Der Unterschenkel.

## Koordinatensystem
*   **X:** Vorwärts / Rückwärts
*   **Y:** Hoch / Runter (Höhe)
*   **Z:** Seitlich (Rechts / Links)

## Herleitung der Winkel

### 1. Coxa-Winkel (α)
Der Coxa-Winkel rotiert das Bein in der Y-Z Ebene.
$$ \alpha = 90^\circ - \text{atan2}(z, y) $$
Ein Winkel von $90^\circ$ entspricht der neutralen Ausrichtung.

### 2. Effektive Beinlänge ($l_{23}$)
Nachdem die Coxa-Rotation berücksichtigt wurde, betrachten wir das Problem in der Ebene des Beins. Wir berechnen die Distanz vom Coxa-Gelenk zum Fusspunkt:
$$ l_{23} = \sqrt{(z - x_{coxa})^2 + (y - y_{coxa})^2 + x^2} $$
Wobei $x_{coxa}$ und $y_{coxa}$ die Position des Gelenks nach der Rotation $\alpha$ sind.

### 3. Femur-Winkel (β)
Der Femur-Winkel wird über den Kosinussatz und die Neigung zur X-Achse berechnet:
$$ \beta = \text{asin}\left(\frac{x}{l_{23}}\right) - \text{acos}\left(\frac{l_2^2 + l_{23}^2 - l_3^2}{2 \cdot l_2 \cdot l_{23}}\right) $$

### 4. Tibia-Winkel (γ)
Der Tibia-Winkel ergibt sich ebenfalls aus dem Kosinussatz:
$$ \gamma = \pi - \text{acos}\left(\frac{l_2^2 + l_3^2 - l_{23}^2}{2 \cdot l_2 \cdot l_3}\right) $$

## Implementierung
Die Implementierung findet sich in `movement/ik.py`. Zur Stabilität werden die Eingabewerte für `acos` und `asin` auf das Intervall $[-1, 1]$ begrenzt.
