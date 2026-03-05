from movement.ik import IKEngine

ik = IKEngine(l1=25, l2=55, l3=60)
# Neutral position at target height 105mm
angles = ik.calculate_angles(0, 105, 0)
print(f"Neutral Angles (x=0, y=105, z=0):")
print(f"  Joint 1: {angles.joint_1:.2f}")
print(f"  Joint 2: {angles.joint_2:.2f}")
print(f"  Joint 3: {angles.joint_3:.2f}")

# Check limits
print("\nChecking range (y=70 to y=140):")
for y in [70, 105, 140]:
    ang = ik.calculate_angles(0, y, 0)
    print(f"  y={y}: J2={ang.joint_2:.1f}, J3={ang.joint_3:.1f}")
