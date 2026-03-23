import pytest
import time
from sal.mock_drivers import MockIMU


class TestMockIMU:
    def test_initial_state(self):
        imu = MockIMU()
        data = imu.get_data()
        assert data.roll == 0.0
        assert data.pitch == 0.0
        assert data.yaw == 0.0
        assert data.accel_z == 1.0

    def test_set_movement(self):
        imu = MockIMU()
        imu.set_movement(roll=5.0, pitch=3.0, yaw=2.0)
        imu.update()
        data = imu.get_data()
        assert data.roll > 0.0
        assert data.pitch > 0.0
        assert data.yaw > 0.0

    def test_movement_convergence(self):
        imu = MockIMU()
        imu.set_movement(roll=10.0, pitch=10.0, yaw=10.0)
        imu.set_smoothing(0.5)
        for _ in range(20):
            imu.update()
        data = imu.get_data()
        assert abs(data.roll - 10.0) < 0.5
        assert abs(data.pitch - 10.0) < 0.5
        assert abs(data.yaw - 10.0) < 0.5

    def test_reset(self):
        imu = MockIMU()
        imu.set_movement(roll=15.0, pitch=15.0, yaw=15.0)
        imu.update()
        imu.reset()
        data = imu.get_data()
        assert data.roll == 0.0
        assert data.pitch == 0.0
        assert data.yaw == 0.0

    def test_jitter(self):
        imu = MockIMU()
        imu.set_jitter(1.0)
        imu.set_movement(roll=5.0, pitch=5.0, yaw=5.0)
        imu.set_smoothing(1.0)
        values = []
        for _ in range(10):
            imu.update()
            values.append(imu.get_data().roll)
        assert len(set(round(v, 1) for v in values)) > 1

    def test_oscillation(self):
        imu = MockIMU()
        imu.set_oscillation(freq=0.5, amplitude=5.0)
        imu.set_smoothing(1.0)
        roll_at_start = imu.get_data().roll
        time.sleep(0.6)
        imu.update()
        roll_after_delay = imu.get_data().roll
        assert abs(roll_at_start - roll_after_delay) > 1.0

    def test_accel_calculation(self):
        imu = MockIMU()
        imu.set_movement(roll=90.0, pitch=0.0, yaw=0.0)
        imu.set_smoothing(1.0)
        imu.update()
        data = imu.get_data()
        assert abs(data.accel_x) > 5.0
        assert abs(data.accel_z) < 2.0

    def test_smoothing_factor(self):
        imu_slow = MockIMU()
        imu_slow.set_smoothing(0.1)
        imu_slow.set_movement(roll=10.0, pitch=10.0, yaw=10.0)

        imu_fast = MockIMU()
        imu_fast.set_smoothing(0.9)
        imu_fast.set_movement(roll=10.0, pitch=10.0, yaw=10.0)

        for _ in range(5):
            imu_slow.update()
            imu_fast.update()

        slow_data = imu_slow.get_data()
        fast_data = imu_fast.get_data()
        assert slow_data.roll < fast_data.roll

    def test_interface_update(self):
        imu = MockIMU()
        imu.update()
        assert imu.get_data().timestamp > 0

    def test_interface_get_data(self):
        imu = MockIMU()
        data = imu.get_data()
        assert data is not None
        assert hasattr(data, "roll")
        assert hasattr(data, "pitch")
        assert hasattr(data, "yaw")
