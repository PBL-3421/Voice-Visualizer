import numpy as np\
import pyaudio\
import math\
import sys\
\
# --- Configuration ---\
FORMAT = pyaudio.paInt16\
CHANNELS = 1\
RATE = 44100  # Sample rate\
CHUNK = 1024  # Number of samples per frame\
NUM_BARS = 16 # Number of bars in the display\
BAR_CHAR = '\uc0\u9608 ' # Character to use for the bars\
EMPTY_BAR_CHAR = '\uc0\u9617 ' # Character for empty parts of the bar\
\
# --- Audio Stream Setup ---\
p = pyaudio.PyAudio()\
try:\
    stream = p.open(format=FORMAT,\
                    channels=CHANNELS,\
                    rate=RATE,\
                    input=True,\
                    frames_per_buffer=CHUNK)\
except OSError as e:\
    print(f"Error opening audio stream: \{e\}")\
    print("Please check your microphone permissions in System Settings > Privacy & Security > Microphone.")\
    sys.exit(1)\
\
print("KITT Voice Box Activated. Speak into your microphone.")\
print("Press Ctrl+C to exit.")\
\
def get_audio_data(data):\
    """Convert raw audio data to a numpy array."""\
    numpy_data = np.frombuffer(data, dtype=np.int16)\
    normalized_data = numpy_data / 32768.0\
    return normalized_data\
\
def calculate_frequency_bins(data, num_bins):\
    """Calculate the average amplitude for different frequency ranges."""\
    fft_data = np.fft.fft(data)\
    fft_magnitude = np.abs(fft_data)\
    \
    num_freq_bins = len(fft_magnitude) // 2\
    freq_magnitude = fft_magnitude[:num_freq_bins]\
    \
    bin_size = num_freq_bins // num_bins\
    frequency_bins = []\
    \
    for i in range(num_bins):\
        start_index = i * bin_size\
        end_index = start_index + bin_size\
        bin_average = np.mean(freq_magnitude[start_index:end_index])\
        frequency_bins.append(bin_average)\
        \
    return frequency_bins\
\
try:\
    while True:\
        data = stream.read(CHUNK, exception_on_overflow=False)\
        \
        audio_data = get_audio_data(data)\
        frequency_amplitudes = calculate_frequency_bins(audio_data, NUM_BARS)\
        \
        # --- Display Logic ---\
        print('\\r', end='')\
        \
        bar_display = []\
        for amplitude in frequency_amplitudes:\
            # Scale the amplitude to a number of characters (e.g., 0 to 20)\
            # The scaling factor (e.g., 50) can be adjusted for sensitivity\
            bar_height = int(amplitude * 50)\
            bar_height = min(20, max(0, bar_height)) # Clamp between 0 and 20\
            \
            # Create the bar string\
            filled_bars = BAR_CHAR * bar_height\
            empty_bars = EMPTY_BAR_CHAR * (20 - bar_height)\
            bar_display.append(f"\{filled_bars\}\{empty_bars\}")\
            \
        print(" ".join(bar_display), end='', flush=True)\
\
except KeyboardInterrupt:\
    print("\\nKITT Voice Box Deactivated.")\
finally:\
    stream.stop_stream()\
    stream.close()\
    p.terminate()}