---
name: image-gen
description: Generate and edit images using AI models. Use when the user asks to create images, generate visuals, make graphics, create artwork, generate a picture, draw something, or edit/refine an existing image. Supports Gemini Nano Banana Pro (Google) and gpt-image-1.5 (OpenAI).
allowed-tools: Bash, Read
---

# Image Generation Skill

Generate and iteratively refine images using state-of-the-art AI models.

## Available Models

| Alias | Model | Best For |
|-------|-------|----------|
| `nano-banana` | Gemini 2.5 Flash Image | Fast generation, high volume |
| `nano-banana-pro` | Gemini 3 Pro Image | 4K resolution, complex scenes, default |
| `gpt-image` | OpenAI gpt-image-1 | General purpose |
| `gpt-image-1.5` | OpenAI gpt-image-1.5 | Latest OpenAI, transparency support |
| `gpt-image-mini` | OpenAI gpt-image-1-mini | Fast, lower cost |

## Smart Model Selection

By default, the script auto-selects the best model based on the prompt:

| Detected Intent | Selected Model | Reason |
|----------------|----------------|--------|
| Transparency keywords | gpt-image-1.5 | Only OpenAI supports transparent PNG |
| Text/typography | gpt-image-1.5 | Better text rendering |
| "4K", "high res", "poster" | nano-banana-pro | Supports up to 4K |
| "quick", "draft", "sketch" | nano-banana | Faster iteration |
| Default | nano-banana-pro | Best overall quality |

Override with `-m <model>` or use `--transparent` / `--fast` flags.

## Quick Reference

```bash
# Generate new image (auto model selection)
python ~/.claude/skills/image-gen/generate.py generate "a sunset over mountains"

# Force specific model
python ~/.claude/skills/image-gen/generate.py generate "a cat wearing a hat" -m gpt-image-1.5

# Transparent background (auto-selects gpt-image-1.5)
python ~/.claude/skills/image-gen/generate.py generate "a logo on transparent background" --transparent

# Fast draft mode (auto-selects nano-banana)
python ~/.claude/skills/image-gen/generate.py generate "quick sketch of a house" --fast

# High resolution with aspect ratio (Gemini)
python ~/.claude/skills/image-gen/generate.py generate "landscape photo" --aspect-ratio 16:9 --image-size 4K

# Edit the current image (iterative refinement)
python ~/.claude/skills/image-gen/generate.py edit "make the sky more orange"

# Edit a specific image
python ~/.claude/skills/image-gen/generate.py edit "add a boat" -i /path/to/image.png

# Set output directory
python ~/.claude/skills/image-gen/generate.py set-dir /path/to/output

# Check session status
python ~/.claude/skills/image-gen/generate.py status

# Clear session (start fresh)
python ~/.claude/skills/image-gen/generate.py clear
```

## Workflow

### First Generation
1. **Always ask the user where to save images** before the first generation in a session
2. Suggest a smart default based on project structure:
   - `./public/images` — if `./public` exists (Next.js, Vite, static sites)
   - `./assets/images` — if `./assets` exists (general web projects)
   - `./static/images` — if `./static` exists (Hugo, some frameworks)
   - `./images` — if none of the above exist
3. Set output directory: `generate.py set-dir /path/to/dir`
4. Generate: `generate.py generate "prompt"`

**Example prompt to user:**
> "Where should I save generated images? I suggest `./public/images` since this looks like a Next.js project. Or specify a different path."

### Iterative Refinement
After generating, subsequent `edit` commands automatically use the last generated image:

```bash
generate.py generate "a cozy cabin in the woods"
# Creates cabin_001.png

generate.py edit "add snow on the roof"
# Uses cabin_001.png, creates cabin_002.png

generate.py edit "add warm light in the windows"
# Uses cabin_002.png, creates cabin_003.png
```

### Model Selection Guidelines

**Choose `nano-banana-pro` (default) when:**
- User wants high resolution (up to 4K)
- Complex scenes with multiple elements
- Specific aspect ratios needed
- Image editing with multiple reference images

**Choose `gpt-image-1.5` when:**
- User needs transparency (PNG with transparent background)
- Detailed text rendering in images
- User specifically requests OpenAI

**Choose `nano-banana` or `gpt-image-mini` when:**
- Quick iterations/drafts
- Cost efficiency matters
- Simple compositions

## Parameters

### Gemini Models (via OpenRouter)
- `--aspect-ratio`: 1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9
- `--image-size`: 1K, 2K, 4K

### OpenAI Models
- `--size`: 1024x1024, 1536x1024 (landscape), 1024x1536 (portrait), auto

## Environment Setup

Requires these environment variables:
- `OPENROUTER_API_KEY` - For Gemini models
- `OPENAI_API_KEY` - For gpt-image models

## Error Handling

If generation fails:
1. Check API keys are set: `echo $OPENROUTER_API_KEY` / `echo $OPENAI_API_KEY`
2. Check network connectivity
3. Try a different model
4. Check rate limits (wait and retry)

## Session State

The skill maintains **per-project** session state in `.image-gen-session.json` (in the current working directory):
- Current working image (for edits)
- Output directory preference
- Generation history

Each project has its own session, so you can work on multiple projects without cross-contamination.

Use `generate.py status` to view and `generate.py clear` to reset.

Consider adding `.image-gen-session.json` to your `.gitignore`.
