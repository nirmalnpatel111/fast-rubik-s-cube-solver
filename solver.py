import odrive
from odrive.enums import AxisState, ControlMode, InputMode
import time

# Face name -> ODrive serial number
SERIALS = {
    "D": "395634623331",  # Down (Bottom) - Yellow
    "U": "395134633331",  # Up (Top) - White
    "L": "396034693331",  # Left - Blue
    "B": "3971346B3331",  # Back - Red
    "F": "395134623331",  # Front - Orange
    "R": "395934593331",  # Right - Green
}

# Rubik's notation: R, L, U, D, F, B = clockwise 90°
#                   R', L', U', D', F', B' = counter-clockwise 90°
SCRAMBLE_SEQUENCE  = ["R", "U", "F'", "L", "D'", "B", "R'", "F", "L'", "D", "U'", "B'", "R", "L", "F", "D'", "U", "B", "L'", "R'"]
# Reverse: invert each move and reverse order
UNSCRAMBLE_SEQUENCE = ["R", "L", "B'", "U'", "D", "F'", "L'", "R'", "B", "U", "D'", "L", "F'", "R", "B'", "D", "L'", "F", "U'", "R'"]

def connect_odrives():
    """Connect to all 6 ODrives"""
    odrives = {}
    print("Connecting to ODrives...")
    for face, serial in SERIALS.items():
        try:
            odrv = odrive.find_sync(serial_number=serial, timeout=10)
            odrives[face] = odrv
            print(f"  Connected: {face} ({serial})")
        except Exception as e:
            print(f"  FAILED: {face} ({serial}) - {e}")
            return None
    print("All ODrives connected!\n")
    return odrives

def setup_motors(odrives):
    """Put all motors into position control + closed loop, one at a time"""
    print("Setting up motors (one at a time)...")
    for face, odrv in odrives.items():
        # Set position control mode + trajectory input for smooth, fast moves
        odrv.axis0.controller.config.control_mode = ControlMode.POSITION_CONTROL
        odrv.axis0.controller.config.input_mode = InputMode.TRAP_TRAJ

        # Trajectory planner: smooth accel/coast/decel
        odrv.axis0.trap_traj.config.vel_limit = 80.0        # max speed [turns/s]
        odrv.axis0.trap_traj.config.accel_limit = 150.0     # acceleration [turns/s²]
        odrv.axis0.trap_traj.config.decel_limit = 150.0     # deceleration [turns/s²]

        # CRITICAL: set input_pos to current position BEFORE entering closed loop
        # so the motor does NOT snap to 0
        odrv.axis0.controller.input_pos = odrv.axis0.pos_estimate

        # Enter closed loop control (direct state set, no async)
        odrv.axis0.requested_state = AxisState.CLOSED_LOOP_CONTROL
        time.sleep(1)  # wait for state transition

        # Verify it entered closed loop
        state = odrv.axis0.current_state
        if state != AxisState.CLOSED_LOOP_CONTROL:
            print(f"  WARNING: {face} did not enter closed loop (state={state})")
        else:
            print(f"  {face}: ready (pos = {odrv.axis0.pos_estimate:.3f})")
    print("All motors ready!\n")

def rotate(odrv, quarter_turns):
    """Rotate motor by quarter_turns * 90 degrees. +1 = CW, -1 = CCW"""
    current = odrv.axis0.controller.input_pos
    target = current + (quarter_turns * 0.25)  # 0.25 rev = 90°
    odrv.axis0.controller.input_pos = target
    time.sleep(0.08)  # wait for move to finish before next one

def execute_sequence(odrives, sequence):
    """Execute a list of Rubik's notation moves, one at a time"""
    for move in sequence:
        if move.endswith("'"):
            face = move[0]
            direction = -1  # counter-clockwise
        else:
            face = move[0]
            direction = 1   # clockwise

        if face not in odrives:
            print(f"  Face {face} not connected!")
            continue

        print(f"  {move}", end=" ... ", flush=True)
        rotate(odrives[face], direction)
        print("done")

def main():
    odrives = connect_odrives()
    if not odrives:
        print("Failed to connect to all ODrives")
        return

    setup_motors(odrives)

    while True:
        choice = input("Enter command (S=scramble, U=unscramble, Q=quit): ").upper()

        if choice == 'S':
            print("Scrambling...")
            start = time.time()
            execute_sequence(odrives, SCRAMBLE_SEQUENCE)
            elapsed = time.time() - start
            print(f"Scramble complete! ({elapsed:.2f}s)\n")

        elif choice == 'U':
            print("Unscrambling...")
            start = time.time()
            execute_sequence(odrives, UNSCRAMBLE_SEQUENCE)
            elapsed = time.time() - start
            print(f"Unscramble complete! ({elapsed:.2f}s)\n")

        elif choice == 'Q':
            print("Exiting...")
            break

        else:
            print("Invalid choice!\n")

if __name__ == "__main__":
    main()
