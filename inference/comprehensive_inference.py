import os
import soundfile as sf
import torch
import numpy as np
from neutts import NeuTTS
import argparse
import sys
import subprocess
from nltk.tokenize import sent_tokenize

# It's good practice to download the punkt tokenizer once
try:
    import nltk
    nltk.data.find('tokenizers/punkt')
except (ImportError, LookupError):
    print("NLTK 'punkt' tokenizer not found. Downloading...")
    nltk.download('punkt', quiet=True)

def is_gguf_model(model_name):
    """Checks if the model name suggests it's a GGUF model."""
    return "gguf" in model_name.lower()

def play_audio_with_paplay(audio_stream):
    """Pipes audio stream to paplay."""
    try:
        player_process = subprocess.Popen(
            ["paplay", "--raw", f"--rate=24000", "--format=s16le", "--channels=1"],
            stdin=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )
        for chunk in audio_stream:
            player_process.stdin.write(chunk)
        player_process.stdin.close()
        player_process.wait()
    except FileNotFoundError:
        print("`paplay` not found. Please install it to play audio.", file=sys.stderr)
    except Exception as e:
        print(f"Error playing audio with paplay: {e}", file=sys.stderr)


def main(args):
    """
    Comprehensive NeuTTS inference script with streaming and device selection.
    """
    if not is_gguf_model(args.backbone) and args.stream:
        print(f"Warning: Streaming is officially supported only for GGUF models. Your model '{args.backbone}' may not work as expected.", file=sys.stderr)

    # --- Initialize Model ---
    print("Initializing NeuTTS...")
    try:
        tts = NeuTTS(
            backbone_repo=args.backbone,
            backbone_device=args.device,
            codec_repo=args.codec,
            codec_device=args.device,
        )
    except Exception as e:
        print(f"Error initializing NeuTTS: {e}", file=sys.stderr)
        sys.exit(1)

    # --- Prepare Reference ---
    if args.ref_text and os.path.exists(args.ref_text):
        with open(args.ref_text, "r") as f:
            ref_text = f.read().strip()
    else:
        ref_text = args.ref_text or "This is a test of the emergency broadcast system."

    print("Encoding reference audio...")
    ref_codes = tts.encode_reference(args.ref_audio)

    # --- Synthesize ---
    print(f"Synthesizing text...")

    if args.stream:
        # Use the native streaming if the model supports it
        def audio_stream_generator():
            for chunk in tts.infer_stream(args.input_text, ref_codes, ref_text):
                # Convert to 16-bit PCM for paplay
                yield (chunk * 32767).astype(np.int16).tobytes()

        play_audio_with_paplay(audio_stream_generator())

    else:
        # Non-streaming chunking approach
        sentences = sent_tokenize(args.input_text)
        
        def audio_chunk_generator():
            for i, sentence in enumerate(sentences):
                print(f"  - Synthesizing chunk {i+1}/{len(sentences)}: '{sentence}'")
                wav_chunk = tts.infer(sentence, ref_codes, ref_text)
                yield (wav_chunk * 32767).astype(np.int16).tobytes()

        if args.play:
            play_audio_with_paplay(audio_chunk_generator())
        else:
            # If not playing, save the whole file
            print("Concatenating chunks for output file...")
            full_wav = np.concatenate([tts.infer(s, ref_codes, ref_text) for s in sentences])
            print(f"Saving audio to {args.output_path}")
            sf.write(args.output_path, full_wav, 24000)

    print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Comprehensive NeuTTS inference script.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # Core arguments
    parser.add_argument("input_text", type=str, help="Input text to be synthesized.")
    parser.add_argument("--ref_audio", type=str, default="./neutts/samples/jo.wav", help="Path to reference audio file.")
    parser.add_argument("--ref_text", type=str, default="./neutts/samples/jo.txt", help="Path to reference text file or the text itself.")
    parser.add_argument("--output_path", type=str, default="comprehensive_output.wav", help="Path to save the output audio (used if --no-play and --no-stream).")

    # Model and device arguments
    parser.add_argument("--backbone", type=str, default="neuphonic/neutts-nano-q8-gguf", help="Hugging Face repo for the TTS backbone model. GGUF models are recommended for streaming.")
    parser.add_argument("--codec", type=str, default="neuphonic/neucodec", help="Hugging Face repo for the audio codec.")
    parser.add_argument("--device", type=str, default="cpu", choices=["cpu", "cuda"], help="Device to use for inference. 'cuda' requires a compatible GPU and PyTorch build.")

    # Playback and streaming arguments
    parser.add_argument("--stream", action="store_true", help="Enable native model streaming (requires GGUF model). Plays audio directly.")
    parser.add_argument("--no-play", dest="play", action="store_false", help="Do not play audio. If not streaming, saves to file. If streaming, output is discarded.")
    
    # Check for CUDA availability
    if not torch.cuda.is_available():
        print("Warning: CUDA is not available on this system. Falling back to CPU.", file=sys.stderr)
        if any('cuda' in arg for arg in sys.argv):
             # if user explicitly asked for cuda, exit
             print("Error: --device cuda requested but CUDA not available.", file=sys.stderr)
             sys.exit(1)
        # remove cuda choice
        parser.get_default_actions()[5].choices = ['cpu']


    args = parser.parse_args()

    # If streaming, we must play, so --no-play is ignored.
    if args.stream and not args.play:
        print("Info: --stream implies --play. Ignoring --no-play.", file=sys.stderr)
        args.play = True
        
    main(args)
