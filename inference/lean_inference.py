import soundfile as sf
from neutts import NeuTTS
import argparse

# --- Hardcoded Configuration ---
# The user can change these if needed
BACKBONE_REPO = "neuphonic/neutts-nano"
CODEC_REPO = "neuphonic/neucodec"
REF_AUDIO_PATH = "./neutts/samples/jo.wav"
REF_TEXT = "This is a test of the emergency broadcast system." # Text doesn't need to match for nano model
DEVICE = "cpu" # or "cuda" if available

def main(text_to_speak, output_filename):
    """
    Synthesizes speech from text using a hardcoded reference audio.
    """
    print(f"Initializing NeuTTS with backbone: {BACKBONE_REPO}")
    tts = NeuTTS(
        backbone_repo=BACKBONE_REPO,
        backbone_device=DEVICE,
        codec_repo=CODEC_REPO,
        codec_device=DEVICE,
    )

    print(f"Using reference audio: {REF_AUDIO_PATH}")
    ref_codes = tts.encode_reference(REF_AUDIO_PATH)

    print(f"Synthesizing text: '{text_to_speak}'")
    wav = tts.infer(text_to_speak, ref_codes, REF_TEXT)

    print(f"Saving audio to {output_filename}")
    sf.write(output_filename, wav, 24000)
    print("Done.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A lean NeuTTS inference script.")
    parser.add_argument("text", type=str, help="The text to be synthesized.")
    parser.add_argument("-o", "--output", type=str, default="lean_output.wav", help="The name of the output WAV file.")
    args = parser.parse_args()

    main(args.text, args.output)
