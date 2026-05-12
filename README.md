# Enzonic Discipine System
A system for disciplining pets that make too much noise. The stand-alone script serves as a pet monitor that detects loud sounds, records the noise commotion, and notifies the user. Additional instructions are provided to install the rest of the system.

## Requirements
* OS running Python3 (only tested on Unix-based OSs, but working on Windows)
* Microphone compatible with the python-sounddevice library
* Any standard speaker(s)

## Hardware Installation
* TODO

## Soundboard API Configuration: discipline_soundboard_api.py
* TODO

## Email Notifications
* TODO

## Monitor Configuration: enzonic_sound_discipline.py
The following instructions are meant for a Unix-based OSs, but the approach may similar for any standard OS.

Create the ```creds.py``` file that will contain API details and email credentials. Use ```creds_sample.py``` as a template.
```bash
$ cp creds_sample.py creds.py
$ vim creds.py
```

Setup the python environment.
```bash
$ python3 -m venv bark_env
$ source bark_env/bin/activate
$ pip install -r requirements.txt
```

Run ```enzonic_sound_discipline.py``` and make a loud noise in front of the microphone. The script should prompt API to make a discipline sound, record the commotion, and send you an email notification.

```bash
$ python3 enzonic_sound_discipline.py
>>> LOUD NOISE DETECTED! Recording in progress...
```
