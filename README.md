# image-gen

A Claude Code skill for generating and editing images using AI models. Supports Google's Gemini image models (via OpenRouter) and OpenAI's gpt-image models.

## Features

- **Multi-model support**: Gemini Nano Banana, Nano Banana Pro, GPT-Image-1, GPT-Image-1.5, GPT-Image-Mini
- **Smart model selection**: Automatically picks the best model based on your prompt
- **Iterative refinement**: Edit generated images with follow-up prompts
- **Session state**: Tracks current image and output directory per-project
- **Auto-retry**: Handles transient network/SSL errors with exponential backoff
- **Venv isolation**: Self-contained dependencies, won't pollute your system Python

## Installation

1. Clone to your Claude Code skills directory:
   ```bash
   git clone https://github.com/grizzdank/image-gen.git ~/.claude/skills/image-gen
   ```

2. Create and activate the virtual environment:
   ```bash
   cd ~/.claude/skills/image-gen
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Set up API keys (copy `.env.example` to `.env` and fill in):
   ```bash
   cp .env.example .env
   # Edit .env with your keys
   ```

   Or export them directly:
   ```bash
   export OPENROUTER_API_KEY="your-openrouter-key"
   export OPENAI_API_KEY="your-openai-key"
   ```

## Usage

The script auto-bootstraps into its venv, so invoke it however you like:

```bash
# Generate an image
~/.claude/skills/image-gen/generate.py generate "a sunset over mountains"

# Edit the last generated image
~/.claude/skills/image-gen/generate.py edit "add a sailboat"

# Edit a specific image
~/.claude/skills/image-gen/generate.py edit "make it warmer" -i /path/to/image.png

# Force a specific model
~/.claude/skills/image-gen/generate.py generate "logo design" -m gpt-image-1.5

# Transparent background (auto-selects gpt-image-1.5)
~/.claude/skills/image-gen/generate.py generate "icon on transparent background" --transparent

# High resolution with aspect ratio
~/.claude/skills/image-gen/generate.py generate "landscape photo" --aspect-ratio 16:9 --image-size 4K

# Set output directory
~/.claude/skills/image-gen/generate.py set-dir ./public/images

# Check session status
~/.claude/skills/image-gen/generate.py status

# Clear session
~/.claude/skills/image-gen/generate.py clear
```

## Available Models

| Alias | Model | Best For |
|-------|-------|----------|
| `nano-banana` | Gemini 2.5 Flash Image | Fast generation, high volume |
| `nano-banana-pro` | Gemini 3 Pro Image | 4K resolution, complex scenes (default) |
| `gpt-image` | OpenAI gpt-image-1 | General purpose |
| `gpt-image-1.5` | OpenAI gpt-image-1.5 | Transparency, text rendering |
| `gpt-image-mini` | OpenAI gpt-image-1-mini | Fast, lower cost |

## Smart Model Selection

When you don't specify a model, the script auto-selects based on your prompt:

| Detected Intent | Selected Model | Reason |
|----------------|----------------|--------|
| Transparency keywords | gpt-image-1.5 | Only OpenAI supports transparent PNG |
| Text/typography | gpt-image-1.5 | Better text rendering |
| "4K", "high res", "poster" | nano-banana-pro | Supports up to 4K |
| "quick", "draft", "sketch" | nano-banana | Faster iteration |
| Default | nano-banana-pro | Best overall quality |

## Configuration

### API Keys

- `OPENROUTER_API_KEY` - Required for Gemini models (get one at [openrouter.ai](https://openrouter.ai))
- `OPENAI_API_KEY` - Required for GPT-Image models (get one at [platform.openai.com](https://platform.openai.com))

### Model-Specific Parameters

**Gemini (via OpenRouter):**
- `--aspect-ratio`: 1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9
- `--image-size`: 1K, 2K, 4K

**OpenAI:**
- `--size`: 1024x1024, 1536x1024 (landscape), 1024x1536 (portrait), auto

## Session State

The skill maintains per-project session state in `.image-gen-session.json`:
- Current working image (for edits)
- Output directory preference
- Generation history

Add `.image-gen-session.json` to your `.gitignore`.

## Error Handling

The script automatically retries up to 3 times with exponential backoff (1s, 2s, 4s) for transient network/SSL errors. Retry progress is shown in the output.

## Using with Claude Code

This skill is designed for [Claude Code](https://claude.com/claude-code). Place the `SKILL.md` file in your skills directory and Claude will automatically use it when you ask to generate or edit images.

## License

MIT
