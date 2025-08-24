import logging
import numpy as np
import pyaudio
import threading
import time
import torch
import wave
from silero_vad import load_silero_vad, get_speech_timestamps
from utils import phone_picked_up, KillableFunction



# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s')


# Global model storage
silero_model = None
model_ready_event = threading.Event()

# Load model in a thread at startup
def load_model_once():
    global silero_model
    silero_model = load_silero_vad()
    silero_model.eval()  # type: ignore
    model_ready_event.set()

# Start model loading on import
threading.Thread(target=load_model_once, daemon=True).start()







# Killable wrapper function
def killable_record_audio_silero(*args, **kwargs):
    def should_kill():
        return not phone_picked_up()

    killable = KillableFunction(
        func=record_audio_with_silero_vad,
        args=args,
        kwargs=kwargs,
        kill_check=should_kill,
        use_thread=True  # Make sure this uses a thread, not a process.
    )
    return killable.run()



def record_audio_with_silero_vad(save_filepath: str,
                                 silence_duration_to_stop: float = 3.0,
                                 min_recording_duration: float = 5.0,
                                 max_recording_duration: float = 30.0) -> str | None:
    """
    Records audio from the mic using Silero VAD. Starts when speech is
    detected, stops after `silence_duration_to_stop` seconds of silence,
    but only if total recording time exceeds `min_recording_duration`.
    Cuts off recording if it exceeds `max_recording_duration`.

    Saves to `save_filepath`.

    Parameters
    ----------
    save_filepath : str
        Where the file is saved.
    silence_duration_to_stop : float
        How much silence until the recording is cut off.
    min_recording_duration : float
        The minimum duration of an accepted recording.
    max_recording_duration : float
        Cuts off the recording at this time.

    Returns
    -------
    str
        save_filepath if audio was recorded
    None
        if no speech detected or recording too short
    """
    model_ready_event.wait()
    model = silero_model


    buffer_duration = 1.0
    sample_rate = 16000
    chunk_size = 1024

    print('s1')


    print('s2')
    # Audio recording object.
    pa = pyaudio.PyAudio()
    stream = pa.open(format=pyaudio.paInt16,
                     channels=1,
                     rate=sample_rate,
                     input=True,
                     frames_per_buffer=chunk_size)

    # Raw int16 numpy arrays waiting for VAD check
    audio_buffer = []

    print('s3')
    # Frames after speech started
    recorded_frames = []

    recording_started = False
    last_speech_time = None
    recording_start_time = None

    try:
        buffer_duration = 0.3 # TODO: remove this!

        while True:
            # Read from the audio stream, appending to the buffer too.
            data = stream.read(chunk_size, exception_on_overflow=False)
            audio_np = np.frombuffer(data, dtype=np.int16)
            audio_buffer.append(audio_np)

            # Run VAD once we have enough audio buffered.
            total_samples = sum(len(chunk) for chunk in audio_buffer)

            if total_samples < int(buffer_duration * sample_rate):
                continue
            print('s4')
            audio_for_vad = np.concatenate(audio_buffer)
            audio_tensor = torch.from_numpy(audio_for_vad).float() / 32768.0

            speech_timestamps = get_speech_timestamps(audio_tensor,
                                                      model,
                                                      sampling_rate=sample_rate,
                                                      return_seconds=True)

            # Assuming a buffer of 1 sec, if greater than 0.3 is speech, it's real
            speech_duration = sum(ts['end'] - ts['start'] for ts in speech_timestamps)

            print('s5')
            if speech_duration > 0.5:
                last_speech_time = time.time()
                if not recording_started:
                    recording_started = True
                    recording_start_time = time.time()

                recorded_frames.extend(audio_buffer)
                audio_buffer = []

            else:
                if recording_started:
                    silence_elapsed = time.time() - last_speech_time
                    recording_elapsed = time.time() - recording_start_time

                    # Check max recording duration (added)
                    if recording_elapsed >= max_recording_duration:
                        logging.info(f"Max recording duration {max_recording_duration}s reached, stopping.")
                        break

                    # Only stop if silence passed AND minimum recording time is reached
                    if silence_elapsed >= silence_duration_to_stop and recording_elapsed >= min_recording_duration:
                        logging.info(f"Silence for {silence_elapsed:.2f}s after speech and minimum recording time reached, stopping.")
                        break
                    else:
                        recorded_frames.extend(audio_buffer)
                        audio_buffer = []

                    print('s6')
                else:
                    # Not recording yet, limit buffer to prevent memory bloat
                    max_buffer_samples = int(buffer_duration * sample_rate * 5)
                    if sum(len(c) for c in audio_buffer) > max_buffer_samples:
                        audio_buffer.pop(0)

    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()

    if not recorded_frames:
        logging.info("No speech was detected. Returning None.")
        return None

    recorded_audio = np.concatenate(recorded_frames)

    print('s7')
    with wave.open(save_filepath, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(pa.get_sample_size(pyaudio.paInt16))
        wf.setframerate(sample_rate)
        wf.writeframes(recorded_audio.tobytes())

    logging.debug(f"Audio saved to {save_filepath}")
    return save_filepath



# Optional test runner
if __name__ == "__main__":

    for _ in range(3):
        killable_record_audio_silero(
            save_filepath="vad_silero.wav",
            silence_duration_to_stop=3.0,
            min_recording_duration=5.0,
            max_recording_duration=20.0)
