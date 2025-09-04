import platform
import select
import sys



button = None  # default if GPIO is unavailable

# Only attempt GPIO import on Linux
if platform.system() == "Linux":
    try:
        # Check for Pi by reading the CPU info
        with open("/proc/cpuinfo") as f:
            cpuinfo = f.read().lower()
            if "raspberry pi" in cpuinfo:
                from gpiozero import Button  # type: ignore
                button = Button(17, bounce_time=0.05)
                print("GPIO setup complete.")
            else:
                print("Not a Raspberry Pi, skipping GPIO setup.")
    except FileNotFoundError:
        print("Could not read /proc/cpuinfo, skipping GPIO setup.")
else:
    print("Not Linux, skipping GPIO setup.")


def phone_picked_up(throw_error : bool = True) -> bool:
    """
    Returns True if the phone is picked up, otherwise False.

    Imports `button` from RPi's gpiozero library.

    NOTE: when the phone is picked up, the circuit is completed.
    When the phone is placed down, the circuit disconnects.

    Returns
    -------
    bool
        True
            The phone is picked up.
            NOTE: also always True if testing on MacOS
        False
            The phone is placed down.
    """
    if platform.system() == "Darwin":
        # Wait max 0.1 seconds for input
        i, _, _ = select.select([sys.stdin], [], [], 0.1)

        if i:
            user_input = sys.stdin.readline().strip()
            if user_input.lower() == "q":

                if throw_error:
                    raise PhonePutDownError
                else:
                    return False

        return True

    elif platform.system() == "Linux":
        if button.is_pressed: # type: ignore
            return True

        else:
            if throw_error:
                raise PhonePutDownError
            else:
                return False

    # If it's some other system, return True.
    else:
        return True


class PhonePutDownError(Exception):
    """
    Exception raised when the phone is put down.
    """
    def __init__(self, message="Phone put down"):
        super().__init__(message)
