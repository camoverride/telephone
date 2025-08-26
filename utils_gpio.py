import platform
import select
import sys



# System-dependent import. Get The GPIO pins on Raspbian.
# Check for Raspbian specifically, and not just any Linux system.
if platform.system() == "Linux":
    try:
        with open("/etc/os-release") as f:
            os_info = f.read().lower()
            if "raspbian" in os_info:
                from gpiozero import Button  # type: ignore
                # GPIO 17 with 50ms debounce time.
                button = Button(17, bounce_time=0.05)
            else:
                print("Not running on Raspbian, skipping GPIO setup.")
    except FileNotFoundError:
        print("Could not read /etc/os-release to check \
                         for Raspbian. Skipping GPIO setup.")
    from gpiozero import Button # type: ignore


def phone_picked_up() -> bool:
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

                raise PhonePutDownError
                return False

        return True

    elif platform.system() == "Linux":
        if button.is_pressed:
            return True

        else:
            raise PhonePutDownError
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
