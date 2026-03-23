from movement.ik import IKEngine

ik = IKEngine(l1=25, l2=55, l3=60)
# Neutral position at target height 105mm
angles = ik.calculate_angles(0, 105, 0)
print(f"Neutral Angles (x=0, y=105, z=0):")
print(f"  Shoulder: {angles.shoulder:.2f}° (Roll: 0° = horizontal)")
print(f"  Thigh: {angles.thigh:.2f}° (Pitch: 0° = straight down)")
print(f"  Shin: {angles.shin:.2f}° (Pitch: 0° = aligned with thigh)")

# Check limits
print("\nChecking range (y=70 to y=140):")
for y in [70, 105, 140]:
    ang = ik.calculate_angles(0, y, 0)
    print(f"  y={y}: Thigh={ang.thigh:.1f}°, Shin={ang.shin:.1f}°")
