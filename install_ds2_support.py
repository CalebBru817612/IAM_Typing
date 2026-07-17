#!/usr/bin/env python3
# One-time DS2 support installer for IAM Typing.

from __future__ import annotations

import os
import shutil
import urllib.error
import urllib.request
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
MAIN_FILE = APP_DIR / "main.py"
BACKUP_FILE = APP_DIR / "main_before_ds2.py"
CODEC_DIR = APP_DIR / "ds2_codec"

CODEC_FILES = {
    "ds2decode.py": "https://raw.githubusercontent.com/hirparak/dss-codec/refs/heads/master/ds2decode.py",
    "ds2_lsp_codebook.npz": "https://raw.githubusercontent.com/hirparak/dss-codec/refs/heads/master/ds2_lsp_codebook.npz",
    "ds2_qp_codebook.npz": "https://raw.githubusercontent.com/hirparak/dss-codec/refs/heads/master/ds2_qp_codebook.npz",
    "THIRD_PARTY_LICENSE.txt": "https://raw.githubusercontent.com/hirparak/dss-codec/refs/heads/master/LICENSE",
}

PATCH_MARKER = "# IAM_TYPING_DS2_SUPPORT_V1"
DS2_SUPPORT_CODE = '# IAM_TYPING_DS2_SUPPORT_V1\nclass DS2ConversionError(RuntimeError):\n    pass\n\n\nclass DS2Converter:\n    def __init__(self):\n        self.app_dir = os.path.dirname(os.path.abspath(__file__))\n        self.codec_dir = os.path.join(self.app_dir, "ds2_codec")\n        self.decoder_path = os.path.join(self.codec_dir, "ds2decode.py")\n        self.required_files = [\n            self.decoder_path,\n            os.path.join(self.codec_dir, "ds2_lsp_codebook.npz"),\n            os.path.join(self.codec_dir, "ds2_qp_codebook.npz"),\n        ]\n\n    def verify(self):\n        missing = [\n            os.path.basename(path)\n            for path in self.required_files\n            if not os.path.isfile(path)\n        ]\n        if missing:\n            raise DS2ConversionError(\n                "DS2 support files are missing:\\n\\n"\n                + "\\n".join(missing)\n                + "\\n\\nRun install_ds2_support.py again."\n            )\n\n        try:\n            import numpy\n        except Exception as error:\n            raise DS2ConversionError(\n                "NumPy is required for DS2 conversion.\\n\\n"\n                "Run: python -m pip install numpy"\n            ) from error\n\n    def convert(self, source_path):\n        import importlib.util\n        import tempfile\n        import uuid\n\n        self.verify()\n\n        with open(source_path, "rb") as source:\n            header = source.read(4)\n\n        if header == b"\\x03enc":\n            raise DS2ConversionError(\n                "This DS2 file is encrypted.\\n\\n"\n                "This first DS2 build supports unencrypted files only."\n            )\n\n        if header not in (b"\\x03ds2", b"\\x01ds2", b"\\x07ds2"):\n            raise DS2ConversionError(\n                "This file is not a supported DS2 format."\n            )\n\n        module_name = "iam_ds2decode_" + uuid.uuid4().hex\n        spec = importlib.util.spec_from_file_location(\n            module_name,\n            self.decoder_path\n        )\n        if spec is None or spec.loader is None:\n            raise DS2ConversionError("Could not load the DS2 decoder.")\n\n        decoder_module = importlib.util.module_from_spec(spec)\n        old_folder = os.getcwd()\n        output_path = os.path.join(\n            tempfile.gettempdir(),\n            "IAM_Typing_DS2_" + uuid.uuid4().hex + ".wav"\n        )\n\n        try:\n            os.chdir(self.codec_dir)\n            spec.loader.exec_module(decoder_module)\n            _frames, _count, mode = decoder_module.read_ds2_file(source_path)\n            decoder = decoder_module.DS2Decoder(mode)\n            decoder.decode_file(source_path, output_path)\n        except Exception as error:\n            try:\n                if os.path.exists(output_path):\n                    os.remove(output_path)\n            except OSError:\n                pass\n            raise DS2ConversionError(\n                "IAM Typing could not convert this DS2 file.\\n\\n"\n                + str(error)\n            ) from error\n        finally:\n            os.chdir(old_folder)\n\n        if not os.path.isfile(output_path) or os.path.getsize(output_path) <= 44:\n            raise DS2ConversionError(\n                "The DS2 decoder did not create a valid WAV file."\n            )\n\n        return output_path\n'
NEW_FILE_HANDLING_METHODS = '    def cleanup_temp_audio(self):\n        if not self.temp_audio_file:\n            return\n\n        if self.player:\n            try:\n                self.player.stop()\n            except Exception:\n                pass\n\n        try:\n            if os.path.exists(self.temp_audio_file):\n                os.remove(self.temp_audio_file)\n        except OSError:\n            pass\n\n        self.temp_audio_file = ""\n\n    def on_close(self):\n        if self.player:\n            try:\n                self.player.stop()\n            except Exception:\n                pass\n\n        self.cleanup_temp_audio()\n        self.root.destroy()\n\n    def prepare_selected_file(self, selected_file):\n        self.source_file = selected_file\n        self.update_file_info(selected_file)\n\n        file_name = os.path.basename(selected_file)\n        self.recent_files[file_name] = selected_file\n\n        if len(self.recent_files) > 15:\n            oldest = list(self.recent_files.keys())[0]\n            del self.recent_files[oldest]\n\n        if os.path.splitext(selected_file)[1].lower() != ".ds2":\n            self.cleanup_temp_audio()\n            self.selected_file = selected_file\n            self.load_media_for_playback(selected_file)\n            self.set_progress(\n                0,\n                "File ready. Use playback or Start Auto Draft."\n            )\n            self.set_status("File ready")\n            return\n\n        self.cleanup_temp_audio()\n        self.selected_file = ""\n        self.is_converting_ds2 = True\n        self.set_start_buttons("disabled", "Converting DS2...")\n        self.set_progress(5, "Converting Philips DS2 to WAV...")\n        self.set_status("Converting DS2")\n\n        threading.Thread(\n            target=self.convert_ds2_for_use,\n            args=(selected_file,),\n            daemon=True\n        ).start()\n\n    def convert_ds2_for_use(self, source_file):\n        try:\n            wav_file = self.ds2_converter.convert(source_file)\n            self.safe_ui(\n                lambda: self.finish_ds2_conversion(source_file, wav_file)\n            )\n        except Exception as error:\n            self.safe_ui(\n                lambda error=error: self.fail_ds2_conversion(error)\n            )\n\n    def finish_ds2_conversion(self, source_file, wav_file):\n        if source_file != self.source_file:\n            try:\n                if os.path.exists(wav_file):\n                    os.remove(wav_file)\n            except OSError:\n                pass\n            return\n\n        self.temp_audio_file = wav_file\n        self.selected_file = wav_file\n        self.is_converting_ds2 = False\n        self.load_media_for_playback(wav_file)\n        self.set_start_buttons("normal", "▶ Start Typing Draft")\n        self.set_progress(\n            100,\n            "DS2 converted. Ready for playback or Auto Draft."\n        )\n        self.set_status("DS2 ready")\n\n    def fail_ds2_conversion(self, error):\n        self.is_converting_ds2 = False\n        self.selected_file = ""\n        self.set_start_buttons("normal", "▶ Start Typing Draft")\n        self.set_progress(0, "DS2 conversion failed")\n        self.set_status("DS2 error")\n        messagebox.showerror("DS2 Conversion Error", str(error))\n\n    def select_file(self):\n        selected_file = filedialog.askopenfilename(\n            title="Select Dictation Audio or Video File",\n            filetypes=SUPPORTED_FILETYPES\n        )\n\n        if not selected_file:\n            return\n\n        self.prepare_selected_file(selected_file)\n\n'
OLD_STATE = '        self.selected_file = ""\n        self.recent_files = {}\n        self.is_transcribing = False\n        self.whisper_model = None\n'
NEW_STATE = '        self.selected_file = ""\n        self.source_file = ""\n        self.temp_audio_file = ""\n        self.recent_files = {}\n        self.is_transcribing = False\n        self.is_converting_ds2 = False\n        self.whisper_model = None\n        self.ds2_converter = DS2Converter()\n        self.root.protocol("WM_DELETE_WINDOW", self.on_close)\n'
OLD_START = '    def start_auto_draft(self):\n        if self.is_transcribing:\n'
NEW_START = '    def start_auto_draft(self):\n        if self.is_converting_ds2:\n            messagebox.showinfo(\n                "Converting DS2",\n                "Please allow the DS2 conversion to finish first."\n            )\n            return\n\n        if self.is_transcribing:\n'
OLD_EXPORT = '    def default_export_name(self, extension):\n        if self.selected_file:\n            base_name = os.path.splitext(os.path.basename(self.selected_file))[0]\n        else:\n            base_name = "typed_document"\n'
NEW_EXPORT = '    def default_export_name(self, extension):\n        export_source = self.source_file or self.selected_file\n\n        if export_source:\n            base_name = os.path.splitext(os.path.basename(export_source))[0]\n        else:\n            base_name = "typed_document"\n'
OLD_FRESH = '    def start_fresh(self):\n        if self.player:\n            self.player.stop()\n\n        self.selected_file = ""\n'
NEW_FRESH = '    def start_fresh(self):\n        if self.player:\n            self.player.stop()\n\n        self.source_file = ""\n        self.cleanup_temp_audio()\n        self.selected_file = ""\n'
OLD_HISTORY = '            if path and os.path.exists(path):\n                self.selected_file = path\n                self.load_media_for_playback(path)\n                self.update_file_info(path)\n                self.set_status("File ready")\n                history_window.destroy()\n'
NEW_HISTORY = '            if path and os.path.exists(path):\n                self.prepare_selected_file(path)\n                history_window.destroy()\n'


def download_file(url, destination):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "IAM-Typing-DS2-Installer/1.0"}
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read()
    except (urllib.error.URLError, TimeoutError) as error:
        raise RuntimeError(
            "Could not download " + destination.name + "\n\n" + str(error)
        ) from error

    if not data:
        raise RuntimeError("Downloaded file is empty: " + destination.name)

    destination.write_bytes(data)


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            "Could not safely patch "
            + label
            + ". Expected one match, found "
            + str(count)
            + "."
        )
    return text.replace(old, new, 1)


def patch_main(text):
    if PATCH_MARKER in text:
        raise RuntimeError("DS2 support is already installed.")

    anchor = "FFMPEG_EXECUTABLE = configure_ffmpeg()\n"
    text = replace_once(
        text,
        anchor,
        anchor + "\n" + DS2_SUPPORT_CODE.strip("\n") + "\n",
        "DS2 converter"
    )

    text = text.replace(
        'APP_VERSION = "v1.0.2-compact"',
        'APP_VERSION = "v1.0.3-ds2"'
    )
    text = text.replace(
        'APP_VERSION = "v1.0.1-compact"',
        'APP_VERSION = "v1.0.3-ds2"'
    )

    text = replace_once(text, OLD_STATE, NEW_STATE, "application state")

    start = text.find("    def select_file(self):\n")
    end = text.find("    def update_file_info(self, file_path):\n", start)
    if start == -1 or end == -1:
        raise RuntimeError("Could not locate select_file.")

    text = text[:start] + NEW_FILE_HANDLING_METHODS + text[end:]
    text = replace_once(text, OLD_START, NEW_START, "Auto Draft guard")
    text = replace_once(text, OLD_EXPORT, NEW_EXPORT, "export filename")
    text = replace_once(text, OLD_FRESH, NEW_FRESH, "Start Fresh cleanup")
    text = replace_once(text, OLD_HISTORY, NEW_HISTORY, "history loader")
    return text


def main():
    print("IAM Typing DS2 installer")
    print("=" * 32)

    if not MAIN_FILE.is_file():
        print("\nERROR: main.py was not found.")
        print("Put this installer in the IAM_Typing project folder.")
        return 1

    CODEC_DIR.mkdir(exist_ok=True)

    print("\nDownloading DS2 decoder files...")
    for filename, url in CODEC_FILES.items():
        print("  - " + filename)
        download_file(url, CODEC_DIR / filename)

    original = MAIN_FILE.read_text(encoding="utf-8")
    patched = patch_main(original)

    if not BACKUP_FILE.exists():
        shutil.copy2(MAIN_FILE, BACKUP_FILE)
        print("\nBackup created: main_before_ds2.py")

    temp_file = MAIN_FILE.with_suffix(".py.tmp")
    temp_file.write_text(patched, encoding="utf-8")
    os.replace(temp_file, MAIN_FILE)

    print("\nSUCCESS")
    print("DS2 support was added to main.py.")
    print("Run main.py and import an unencrypted .ds2 file.")
    print("Long files may convert slowly in this first build.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print("\nINSTALLATION FAILED")
        print(error)
        print("\nmain.py is only replaced after every patch point passes.")
        raise SystemExit(1)
