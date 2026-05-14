#!/mnt/c/Users/jcaj3/Projects/personal/bark_detect/bark_env/bin/python3

import sys
import numpy as np
from datetime import datetime

# Notification system
from aiosmtplib import send
from email.message import EmailMessage

# Bark detection
import asyncio
import sounddevice as sd

# Audio recording
from pathlib import Path
import wave
from collections import deque

# Credentials
from creds import ENZONIC_API_URL, ENZONIC_API_CREDS, ENZONIC_DISC_SOUND, EMAIL_ADDR, EMAIL_KEY

# Microphone configuration
THRESHOLD_DB = -30 # sound level limit, in decibels
DETECTED_AUDIO_DURATION = 5 # recording time after sound is detected, in seconds
SAMPLE_RATE = 44100 # standard audio sample rate
BLOCK_SIZE = 8820 # monitor/record noise roughly every 200ms
CHANNELS = 1 # mono audio signal

# Output sound file conversion
now = datetime.now()
curr_time_str = now.strftime("%Y-%m-%d_%H-%M-%S")
OUTPUT_FILENAME = f'audio_recs/sound_detection_{curr_time_str}'
SAMPLE_WIDTH = 2 # resolution of no noise quality
RECORDING_TIME = 15 # total recording time of sound detected, in seconds
INT16_SCALE = 32767 # scaling factor of analog audio data to 16-bit
max_blocks = (SAMPLE_RATE // BLOCK_SIZE) * RECORDING_TIME # calculate total blocks of audio data
audio_buffer = deque(maxlen=max_blocks) # initialize the audio buffer for recording

# Global states
recn = 0 # current sound detection index
is_busy = False # flag for preventing detection loop (ignore detections when 'True')

async def notify_bark_detection():
	""" Send an email notification of bark detection. """

	# Prepare message
	msg = EmailMessage()
	msg['Subject'] = 'Enzonic: commotion detected'
	msg['From'] = EMAIL_ADDR
	msg['To'] = EMAIL_ADDR
	msg.set_content(f"Loud noise detected in your apartment.")

	# Forward message to receiver
	await send(
		msg,
		hostname="smtp.gmail.com",
		port=587,
		username=EMAIL_ADDR,
		password=EMAIL_KEY,
		start_tls=True
	)

async def notify_api_failure():
	""" Send an email notification about failed API call. """

	# Prepare message
	msg = EmailMessage()
	msg['Subject'] = 'Enzonic: error'
	msg['From'] = EMAIL_ADDR
	msg['To'] = EMAIL_ADDR
	msg.set_content(f"Application failed to send discipline request to API.")

	# Forward message to receiver
	await send(
		msg,
		hostname="smtp.gmail.com",
		port=587,
		username=EMAIL_ADDR,
		password=EMAIL_KEY,
		start_tls=True
	)

def db_from_noise(audio):
	""" Calculate sound level. """

	# Calculate RMS (Volume)
	rms = np.sqrt(np.mean(audio**2))

	# Calculate the decibels from RMS
	if rms == 0:
		return -np.inf
	return 20 * np.log10(rms + 1e-9) # avoid log of zero with a tiny epsilon

async def discipline():
	''' Notify user about detection and record clip of sound detection. '''

	# Get current noise detected in process
	global recn

	# Set process to 'busy' to prevent multiple instances of 'discipline'
	global is_busy
	is_busy = True

	# Notify console
	print(f">>> LOUD NOISE DETECTED! Recording in progress...")
	
	# Play the discipline sound
	discipline_sound = await asyncio.create_subprocess_exec(
		'curl', '-X', 'POST', ENZONIC_API_URL, '-u', ENZONIC_API_CREDS, '-H', ENZONIC_DISC_SOUND[0], '-d', ENZONIC_DISC_SOUND[1],
		stdout=asyncio.subprocess.DEVNULL,
		stderr=asyncio.subprocess.DEVNULL,
		stdin=asyncio.subprocess.DEVNULL
	)
	try:
		# run discipline sound
		stdout, stderr = await asyncio.wait_for(discipline_sound.communicate(), timeout=3.0)
	except asyncio.TimeoutError:
		# API failed to return a response
		print("Process timed out after 3 seconds.")

		# Notify user of failure
		await notify_api_failure()

		# end process
		sys.exit()

	# Hold detection to let sound play and recording audio
	await asyncio.sleep(DETECTED_AUDIO_DURATION)

	# Join the chunks into a single byte string
	recorded_bytes = b''.join(list(audio_buffer))

	# Determine audio file name
	FINAL_OUTPUT_FILENAME = OUTPUT_FILENAME + '_detection_' + str(recn) + '.wav'
	recn += 1

	# Create wav file with specified configs
	with wave.open(FINAL_OUTPUT_FILENAME, 'wb') as wf:
		wf.setnchannels(CHANNELS)
		wf.setsampwidth(SAMPLE_WIDTH)
		wf.setframerate(SAMPLE_RATE)
		wf.writeframes(recorded_bytes)
	print(f"File saved as '{FINAL_OUTPUT_FILENAME}'")

	# Notify user via email
	await notify_bark_detection()
	
	# Process no longer busy
	is_busy = False

def audio_monitor(audio, frames, time, status):
	""" Monitor noise level and continuously capture audio. """

	# Determine whether process is 'busy'
	global is_busy
	
	# Continuously capture the last 15 seconds of audio
	audio_int16 = (audio.copy() * INT16_SCALE).astype(np.int16)
	audio_buffer.append(audio_int16.tobytes())

	# If the process is busy, ignore the noise detection
	if(is_busy):
		return
	
	# Get the current noise level
	db = db_from_noise(audio)
	print(f"Noise Level: {db:.2f} dB", end="\r")

	# Check whether noise leve is too high
	if(db > THRESHOLD_DB):
		# Run steps to discipline
		print(f"Noise Level: {db:.2f} dB")
		asyncio.run_coroutine_threadsafe(discipline(), loop)

async def main():

	# Create output audio directory, if it doesn't exist
	path = Path("./audio_recs")
	path.mkdir(parents=True, exist_ok=True)

	# Initiate looping thread context
	global loop
	loop = asyncio.get_running_loop()

	print(f"Monitoring noise... (Press Ctrl+C to stop)")

	# Run audio monitor
	with sd.InputStream(callback=audio_monitor,
						channels=CHANNELS, 
						samplerate=SAMPLE_RATE, 
						blocksize=BLOCK_SIZE):
		while True:
			await asyncio.sleep(1) # Keep the loop alive

if __name__ == "__main__":
	try:
		asyncio.run(main())
	except Exception:
		print("\nUnexpected error occurred.")
		sys.exit()
	except KeyboardInterrupt:
		print("\nMonitoring stopped.")
	