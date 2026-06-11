#!/usr/bin/env python3
import sys
import math
from typing import List, Tuple

PI: float = 3.14159265358979323846

# Generate n equally spaced points on the unit circle
def generate_input_vectors(n: int) -> List[Tuple[float, float]]:
    pts: List[Tuple[float, float]] = []
    if n <= 0:
        return pts
    for k in range(n):
        theta = 2.0 * PI * float(k) / float(n)
        x = math.cos(theta)
        y = math.sin(theta)
        pts.append((x, y))
    return pts

def read_n(argv: List[str]) -> int:
    if len(argv) > 1:
        try:
            return int(argv[1])
        except Exception:
            pass
    try:
        return int(sys.stdin.readline().strip())
    except Exception:
        return 0

def normalize_angle(angle: float) -> float:
    if angle > 0.0 and angle > 2.0 * math.pi:
        return math.fmod(angle, 2.0 * math.pi) - 2.0 * math.pi
    elif angle > 0.0:
        return angle - 2.0 * math.pi
    elif angle <= 0.0 and abs(angle) > 2.0 * math.pi:
        return math.fmod(angle, 2.0 * math.pi)
    else:
        return angle

def get_quadrant(angle: float) -> int:
    # Keep the same behavior as std::fmod(angle, -2π) from C++ (result has sign of numerator)
    angle_new = math.fmod(angle, -2.0 * math.pi)

    if angle_new >= -math.pi / 2:
        return 1
    elif angle_new >= -math.pi:
        return 2
    elif angle_new >= -3.0 * math.pi / 2.0:
        return 3
    elif angle_new >= -2.0 * math.pi:
        return 4
    else:
        return 0

def alphas_tan(alpha_1: float, dist_1: float, dist_2: float, dist_4: float) -> float:
    return math.atan(math.tan(alpha_1)*(dist_4 + dist_1) / (dist_1))

def GetCommandsFromSpeedVector(x_command: float, y_command: float) -> List[float]:
    wheel_commands: List[float] = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    velocities: List[float] = [0.0, 0.0, 0.0, 0.0]  # unused, kept for parity

    x_component = 0.0
    y_component = 0.0
    alpha_1 = 0.0
    quadrant = 0
    alpha_2 = 0.0
    beta_d = 0.0
    left_wheel_command = 0.0
    right_wheel_command = 0.0
    caster_fork_command = 0.0
    caster_wheel_command = 0.0
    x_dot_c_desired = 0.0
    y_dot_c_desired = 0.0
    alpha_target = 0.0
    alpha_c = 0.0

    # Parameters
    max_x_velocity_ = 10.0
    min_x_velocity_ = -10.0
    max_y_velocity_ = 10.0
    min_y_velocity_ = -10.0
    center_distance_ = 1.0
    wheel_separation_ = 1.15
    center_to_caster_distance_ = 0.75
    left_wheel_radius_ = 0.750 / 2.0
    caster_fork_pos_ = 0.0

    unlim_left_wheel_cmd_ = 0.0
    unlim_right_wheel_cmd_ = 0.0
    unlim_caster_fork_cmd_ = 0.0
    unlim_caster_wheel_cmd_ = 0.0
    min_left_wheel_motor_speed_ = -1000.00
    max_right_wheel_motor_speed_ = 1000.0
    min_right_wheel_motor_speed_ = -1000.0
    max_caster_fork_motor_pos_ = 1000.0
    min_caster_fork_motor_pos_ = -1000.0

    max_caster_wheel_motor_speed_ = 1000.0
    min_caster_wheel_motor_speed_ = -1000.0

    max_left_wheel_motor_speed_ = 1000.0

    # Clamp input speeds
    if x_command > max_x_velocity_ and x_command > 0:
        x_command = max_x_velocity_
    elif x_command < min_x_velocity_ and x_command < 0:
        x_command = min_x_velocity_

    if y_command > max_y_velocity_ and y_command > 0:
        y_command = max_y_velocity_
    elif y_command < min_y_velocity_ and y_command < 0:
        y_command = min_y_velocity_

    alpha_1 = math.atan2(y_command, x_command) - (math.pi / 2.0)
    alpha_1 = normalize_angle(alpha_1)
    quadrant = get_quadrant(alpha_1)

    # quadrant-based logic (kept as-is)
    if quadrant == 1:
        alpha_2 = alphas_tan(alpha_1, center_distance_, wheel_separation_, center_to_caster_distance_)
        alpha_target = alpha_2
    elif quadrant == 2:
        alpha_2 = alphas_tan(alpha_1, center_distance_, wheel_separation_, center_to_caster_distance_) - math.pi
        alpha_target = alpha_2 - math.pi
    elif quadrant == 3:
        alpha_2 = alphas_tan(alpha_1, center_distance_, wheel_separation_, center_to_caster_distance_) - math.pi
        alpha_target = alpha_2 + math.pi
    elif quadrant == 4:
        alpha_2 = alphas_tan(alpha_1, center_distance_, wheel_separation_, center_to_caster_distance_) - (2.0 * math.pi)
        alpha_target = alpha_2
    else:
        alpha_target = alpha_2

    alpha_2 = normalize_angle(alpha_2)
    alpha_target = normalize_angle(alpha_target)

    beta_d = alpha_2
    caster_fork_command = alpha_target

    left_wheel_command = (
        (wheel_separation_ / (2.0 * left_wheel_radius_ * center_distance_)) * x_command
        + (1.0 / left_wheel_radius_) * y_command
    )
    right_wheel_command = (
        -(wheel_separation_ / (2.0 * left_wheel_radius_ * center_distance_)) * x_command
        + (1.0 / left_wheel_radius_) * y_command
    )

    x_dot_c_desired = (
        (left_wheel_radius_ * (center_distance_ + center_to_caster_distance_) / wheel_separation_) * left_wheel_command
        - (left_wheel_radius_ * (center_distance_ + center_to_caster_distance_) / wheel_separation_) * right_wheel_command
    )
    y_dot_c_desired = (left_wheel_radius_ / 2.0) * left_wheel_command + (left_wheel_radius_ / 2.0) * right_wheel_command

    # Note: same as C++ comment—caster wheel radius not included
    alpha_c = math.cos(beta_d - caster_fork_pos_) * math.sqrt(x_dot_c_desired**2 + y_dot_c_desired**2)
    caster_wheel_command = alpha_c

    # Save unclamped (not used further, kept for parity)
    unlim_left_wheel_cmd_ = left_wheel_command
    unlim_right_wheel_cmd_ = right_wheel_command
    unlim_caster_fork_cmd_ = caster_fork_command
    unlim_caster_wheel_cmd_ = caster_wheel_command

    # LEFT WHEEL:
    if left_wheel_command > 0 and left_wheel_command > max_left_wheel_motor_speed_:
        wheel_commands[0] = max_left_wheel_motor_speed_
    elif left_wheel_command < 0 and left_wheel_command < min_left_wheel_motor_speed_:
        wheel_commands[0] = min_left_wheel_motor_speed_
    else:
        wheel_commands[0] = left_wheel_command

    # RIGHT WHEEL:
    if right_wheel_command > 0 and right_wheel_command > max_right_wheel_motor_speed_:
        wheel_commands[1] = max_right_wheel_motor_speed_
    elif right_wheel_command < 0 and right_wheel_command < min_right_wheel_motor_speed_:
        wheel_commands[1] = min_right_wheel_motor_speed_
    else:
        wheel_commands[1] = right_wheel_command

    # CASTER FORK:
    quadrant = get_quadrant(caster_fork_command)
    if quadrant == 4:
        caster_fork_command += 2.0 * math.pi

    if caster_fork_command > 0 and caster_fork_command > max_caster_fork_motor_pos_:
        wheel_commands[2] = max_caster_fork_motor_pos_
    elif caster_fork_command < 0 and caster_fork_command < min_caster_fork_motor_pos_:
        wheel_commands[2] = min_caster_fork_motor_pos_
    else:
        wheel_commands[2] = caster_fork_command

    # CASTER WHEEL:
    if caster_wheel_command > 0 and caster_wheel_command > max_caster_wheel_motor_speed_:
        wheel_commands[3] = max_caster_wheel_motor_speed_
    elif caster_wheel_command < 0 and caster_wheel_command < min_caster_wheel_motor_speed_:
        wheel_commands[3] = min_caster_wheel_motor_speed_
    else:
        wheel_commands[3] = caster_wheel_command

    wheel_commands[4] = float(get_quadrant(caster_fork_command))
    wheel_commands[5] = math.fmod(caster_fork_command, -2.0 * math.pi)

    return wheel_commands

def main(argv: List[str]) -> int:
    n = read_n(argv)
    if n <= 0:
        sys.stderr.write(f"Usage: {argv[0]} <n>\n")
        return 1

    pts = generate_input_vectors(n)
    for x, y in pts:
        v = GetCommandsFromSpeedVector(x, y)
        print(f"({x}, {y}) -> ({v[0]}, {v[1]}, {v[2]}, {v[3]}, {v[4]}, {v[5]})")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
