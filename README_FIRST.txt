IAM TYPING DS2 UPDATE
=====================

1. Extract this ZIP into:
   C:\Users\cmark\PycharmProjects\IAM_Typing

2. In the PyCharm terminal, run:
   python install_ds2_support.py

3. Run main.py and import your .DS2 test file.

The installer:
- Downloads the MIT-licensed DS2 decoder from hirparak/dss-codec.
- Creates main_before_ds2.py.
- Patches main.py.
- Converts DS2 to temporary WAV for playback and Whisper.

First-build limits:
- Unencrypted DS2 files only.
- Long files may convert slowly.
