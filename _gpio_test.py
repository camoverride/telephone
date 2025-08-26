"""
Test the GPIO button in real time.
NOTE: this will not work on MacOS when testing.
"""
from gpiozero import Button  # type: ignore
from signal import pause



# Use GPIO17 with 50ms debounce
button = Button(17, bounce_time=0.05)

button.when_pressed = lambda: print("Switch is PRESSED")
button.when_released = lambda: print("Switch is NOT pressed")

# Keeps the script running
pause()  
