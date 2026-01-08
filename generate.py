#!/Users/davegraham/.claude/skills/image-gen/.venv/bin/python3
"""
Image Generation Script for Claude Code
Supports: OpenRouter (Gemini Nano Banana) + Direct OpenAI (gpt-image-1.5)
"""

import argparse
import base64
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# === Venv Bootstrap ===
# Ensures script runs in its own venv regardless of how it's invoked
SKILL_DIR = Path(__file__).parent.resolve()
VENV_PYTHON = SKILL_DIR / ".venv" / "bin" / "python3"

def _ensure_venv():
    """Re-exec with venv Python if we're not already in it."""
    if VENV_PYTHON.exists() and Path(sys.executable).resolve() != VENV_PYTHON.resolve():
        os.execv(str(VENV_PYTHON), [str(VENV_PYTHON)] + sys.argv)

_ensure_venv()

# === Configuration ===
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # seconds

def get_session_file() -> Path:
    """Get project-local session file path."""
    return Path.cwd() / ".image-gen-session.json"

MODELS = {
    # OpenRouter models (Gemini)
    "nano-banana": "google/gemini-2.5-flash-image-preview",
    "nano-banana-pro": "google/gemini-3-pro-image-preview",
    # Direct OpenAI models
    "gpt-image": "gpt-image-1",
    "gpt-image-1.5": "gpt-image-1.5",
    "gpt-image-mini": "gpt-image-1-mini",
}

DEFAULT_MODEL = "nano-banana-pro"


def select_model(prompt: str, transparent: bool = False, high_res: bool = False,
                 fast: bool = False, text_heavy: bool = False) -> str:
    """
    Smart model selection based on task requirements.

    Selection logic:
    - Transparency needed → gpt-image-1.5 (only OpenAI supports transparent PNG)
    - Text/typography heavy → gpt-image-1.5 (better text rendering)
    - 4K / high resolution → nano-banana-pro (supports up to 4K)
    - Fast/draft iteration → nano-banana or gpt-image-mini
    - Complex scenes, multiple elements → nano-banana-pro
    - Default → nano-banana-pro (best overall quality)
    """
    prompt_lower = prompt.lower()

    # Check for transparency keywords
    transparency_keywords = ["transparent", "transparency", "png with alpha",
                            "no background", "remove background", "cutout",
                            "isolated on", "white background", "clear background"]
    if transparent or any(kw in prompt_lower for kw in transparency_keywords):
        return "gpt-image-1.5"

    # Check for text-heavy content
    text_keywords = ["text", "typography", "lettering", "words", "title",
                    "heading", "sign", "poster with text", "logo with text",
                    "banner", "quote", "writing"]
    if text_heavy or any(kw in prompt_lower for kw in text_keywords):
        return "gpt-image-1.5"

    # Check for fast/draft mode
    fast_keywords = ["quick", "draft", "rough", "sketch", "fast", "test"]
    if fast or any(kw in prompt_lower for kw in fast_keywords):
        return "nano-banana"  # Faster, still good quality

    # Check for high resolution needs
    highres_keywords = ["4k", "high res", "high resolution", "detailed",
                       "print quality", "large format", "poster", "wallpaper"]
    if high_res or any(kw in prompt_lower for kw in highres_keywords):
        return "nano-banana-pro"

    # Default to nano-banana-pro for best overall quality
    return "nano-banana-pro"


def load_session():
    """Load current session state."""
    session_file = get_session_file()
    if session_file.exists():
        return json.loads(session_file.read_text())
    return {"current_image": None, "history": [], "output_dir": None}


def save_session(session):
    """Save session state."""
    get_session_file().write_text(json.dumps(session, indent=2))


def clear_session():
    """Clear session state."""
    session_file = get_session_file()
    if session_file.exists():
        session_file.unlink()
    print(f"Session cleared: {session_file}")


def image_to_base64(image_path: str) -> tuple[str, str]:
    """Convert image file to base64 with mime type."""
    path = Path(image_path)
    suffix = path.suffix.lower()
    mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
    mime_type = mime_map.get(suffix, "image/png")

    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return data, mime_type


def save_image(base64_data: str, output_dir: Path, prefix: str = "gen") -> Path:
    """Save base64 image to file with correct extension."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Detect format from data URL or default to png
    ext = "png"
    if base64_data.startswith("data:"):
        # Parse: data:image/jpeg;base64,<data>
        header, base64_data = base64_data.split(",", 1)
        mime_type = header.split(";")[0].replace("data:", "")
        ext_map = {
            "image/png": "png",
            "image/jpeg": "jpg",
            "image/jpg": "jpg",
            "image/webp": "webp",
            "image/gif": "gif",
        }
        ext = ext_map.get(mime_type, "png")

    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    existing = list(output_dir.glob(f"{prefix}_{timestamp}_*.{ext}"))
    index = len(existing) + 1
    filename = f"{prefix}_{timestamp}_{index:03d}.{ext}"

    output_path = output_dir / filename

    with open(output_path, "wb") as f:
        f.write(base64.b64decode(base64_data))

    return output_path


def generate_openrouter(prompt: str, model: str, input_image: str = None,
                         aspect_ratio: str = None, image_size: str = None) -> str:
    """Generate image using OpenRouter (Gemini models)."""
    try:
        import requests
    except ImportError:
        raise ImportError("requests not installed. Run: pip install requests")

    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY not set")

    # Build message content
    content = []
    if input_image:
        img_data, mime_type = image_to_base64(input_image)
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:{mime_type};base64,{img_data}"}
        })
    content.append({"type": "text", "text": prompt})

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "modalities": ["image", "text"],
    }

    # Add image config if specified
    if aspect_ratio or image_size:
        payload["image_config"] = {}
        if aspect_ratio:
            payload["image_config"]["aspect_ratio"] = aspect_ratio
        if image_size:
            payload["image_config"]["image_size"] = image_size

    # Retry loop for transient network/SSL errors
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=120,
            )
            response.raise_for_status()
            break
        except requests.exceptions.RequestException as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_BACKOFF_BASE ** attempt
                print(f"  Retry {attempt + 1}/{MAX_RETRIES} after {wait_time}s: {e}")
                time.sleep(wait_time)
            else:
                raise last_error

    result = response.json()

    # Extract image from response
    message = result["choices"][0]["message"]

    if "images" in message and message["images"]:
        img = message["images"][0]
        # Handle both string and dict formats
        if isinstance(img, dict):
            # Format: {"type": "image_url", "image_url": {"url": "data:..."}}
            if "image_url" in img and isinstance(img["image_url"], dict):
                return img["image_url"]["url"]
            return img.get("url") or img.get("b64_json") or img.get("data")
        return img  # Base64 data URL string

    # Fallback: check content for inline image
    if isinstance(message.get("content"), list):
        for part in message["content"]:
            if part.get("type") == "image_url":
                return part["image_url"]["url"]

    raise ValueError(f"No image in response. Message keys: {message.keys()}")


def generate_openai(prompt: str, model: str, input_image: str = None,
                    size: str = "auto", quality: str = "auto",
                    output_format: str = "png", background: str = "auto") -> str:
    """Generate image using direct OpenAI API."""
    try:
        import requests
    except ImportError:
        raise ImportError("requests not installed. Run: pip install requests")

    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set")

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    # Retry loop for transient network/SSL errors
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            if input_image:
                # Image edit endpoint
                with open(input_image, "rb") as f:
                    files = {"image": f}
                    data = {
                        "model": model,
                        "prompt": prompt,
                        "size": size,
                    }
                    response = requests.post(
                        "https://api.openai.com/v1/images/edits",
                        headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                        files=files,
                        data=data,
                        timeout=120,
                    )
            else:
                # Image generation endpoint
                payload = {
                    "model": model,
                    "prompt": prompt,
                    "size": size,
                    "quality": quality,
                    "output_format": output_format,
                    "background": background,
                    "n": 1,
                }
                response = requests.post(
                    "https://api.openai.com/v1/images/generations",
                    headers=headers,
                    json=payload,
                    timeout=120,
                )
            response.raise_for_status()
            break
        except requests.exceptions.RequestException as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_BACKOFF_BASE ** attempt
                print(f"  Retry {attempt + 1}/{MAX_RETRIES} after {wait_time}s: {e}")
                time.sleep(wait_time)
            else:
                raise last_error

    result = response.json()

    return result["data"][0]["b64_json"]


def generate(prompt: str, model_alias: str = None, input_image: str = None,
             output_dir: str = None, aspect_ratio: str = None,
             image_size: str = None, size: str = "auto",
             transparent: bool = False, fast: bool = False) -> str:
    """Main generation function."""
    session = load_session()

    # Resolve model - use smart selection if not explicitly specified
    if model_alias is None or model_alias == "auto":
        model_alias = select_model(prompt, transparent=transparent, fast=fast,
                                   high_res=(image_size == "4K"))
        print(f"Auto-selected model: {model_alias}")

    if model_alias not in MODELS:
        available = ", ".join(MODELS.keys())
        raise ValueError(f"Unknown model '{model_alias}'. Available: {available}")

    model = MODELS[model_alias]
    is_openai = model_alias.startswith("gpt-")

    # Resolve output directory
    if output_dir:
        out_path = Path(output_dir).expanduser().resolve()
        session["output_dir"] = str(out_path)
    elif session.get("output_dir"):
        out_path = Path(session["output_dir"])
    else:
        out_path = Path.cwd() / "generated-images"
        session["output_dir"] = str(out_path)

    # Use current image for edit if no input specified
    if input_image is None and session.get("current_image"):
        input_image = session["current_image"]

    # Generate
    print(f"Generating with {model_alias} ({model})...")
    if input_image:
        print(f"  Editing: {input_image}")

    if is_openai:
        base64_data = generate_openai(prompt, model, input_image, size=size)
    else:
        base64_data = generate_openrouter(prompt, model, input_image,
                                           aspect_ratio, image_size)

    # Save image
    saved_path = save_image(base64_data, out_path)
    print(f"Saved: {saved_path}")

    # Update session
    session["current_image"] = str(saved_path)
    session["history"].append({
        "prompt": prompt,
        "model": model_alias,
        "input": input_image,
        "output": str(saved_path),
        "timestamp": datetime.now().isoformat(),
    })
    save_session(session)

    return str(saved_path)


def show_status():
    """Show current session status."""
    session_file = get_session_file()
    session = load_session()
    print("=== Image Gen Session ===")
    print(f"Session file: {session_file}")
    print(f"Current image: {session.get('current_image', 'None')}")
    print(f"Output dir: {session.get('output_dir', 'Not set (will ask)')}")
    print(f"History: {len(session.get('history', []))} generations")
    if session.get("history"):
        last = session["history"][-1]
        print(f"Last: {last['model']} - {last['prompt'][:50]}...")


def main():
    parser = argparse.ArgumentParser(description="Generate images with AI models")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Generate command
    gen_parser = subparsers.add_parser("generate", aliases=["gen", "g"],
                                        help="Generate a new image")
    gen_parser.add_argument("prompt", help="Image prompt")
    gen_parser.add_argument("-m", "--model", choices=["auto"] + list(MODELS.keys()),
                           default="auto", help="Model to use (auto = smart selection)")
    gen_parser.add_argument("-o", "--output", help="Output directory")
    gen_parser.add_argument("--aspect-ratio", help="Aspect ratio (Gemini: 1:1, 16:9, etc.)")
    gen_parser.add_argument("--image-size", choices=["1K", "2K", "4K"],
                           help="Image size (Gemini only)")
    gen_parser.add_argument("--size", default="auto",
                           help="Size for OpenAI (1024x1024, 1536x1024, etc.)")
    gen_parser.add_argument("--transparent", action="store_true",
                           help="Request transparent background (uses gpt-image-1.5)")
    gen_parser.add_argument("--fast", action="store_true",
                           help="Fast mode for drafts (uses nano-banana)")

    # Edit command
    edit_parser = subparsers.add_parser("edit", aliases=["e"],
                                         help="Edit current or specified image")
    edit_parser.add_argument("prompt", help="Edit instructions")
    edit_parser.add_argument("-i", "--input", help="Image to edit (defaults to current)")
    edit_parser.add_argument("-m", "--model", choices=["auto"] + list(MODELS.keys()),
                            default="auto", help="Model to use (auto = smart selection)")
    edit_parser.add_argument("-o", "--output", help="Output directory")
    edit_parser.add_argument("--transparent", action="store_true",
                           help="Request transparent background")
    edit_parser.add_argument("--fast", action="store_true",
                           help="Fast mode for drafts")

    # Status command
    subparsers.add_parser("status", aliases=["s"], help="Show session status")

    # Clear command
    subparsers.add_parser("clear", aliases=["c"], help="Clear session")

    # Set output dir
    dir_parser = subparsers.add_parser("set-dir", help="Set output directory")
    dir_parser.add_argument("directory", help="Output directory path")

    args = parser.parse_args()

    try:
        if args.command in ("generate", "gen", "g"):
            result = generate(
                prompt=args.prompt,
                model_alias=args.model if args.model != "auto" else None,
                output_dir=args.output,
                aspect_ratio=args.aspect_ratio,
                image_size=args.image_size,
                size=args.size,
                transparent=args.transparent,
                fast=args.fast,
            )
            print(f"\nGenerated: {result}")

        elif args.command in ("edit", "e"):
            result = generate(
                prompt=args.prompt,
                model_alias=args.model if args.model != "auto" else None,
                input_image=args.input,
                output_dir=args.output,
                transparent=args.transparent,
                fast=args.fast,
            )
            print(f"\nEdited: {result}")

        elif args.command in ("status", "s"):
            show_status()

        elif args.command in ("clear", "c"):
            clear_session()

        elif args.command == "set-dir":
            session = load_session()
            session["output_dir"] = str(Path(args.directory).expanduser().resolve())
            save_session(session)
            print(f"Output directory set to: {session['output_dir']}")

        else:
            parser.print_help()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
