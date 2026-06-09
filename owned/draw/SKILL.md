---
name: draw
description: Generate, edit, and create variations of images from the command line. Use this skill to create stunning visuals, icons, flows, diagrams, and more.
---

# Draw

A small CLI for creating images: `python script/draw.py <command> ...`.

Three commands: **generate**, **edit**, **variation**. When no command is given, `generate` is assumed.

## Setup

Set one API key (auto-detected):

- `LITELLM_API_KEY` — used when set.
- `OPENAI_API_KEY` — used otherwise.

Optional: `LITELLM_BASE_URL`, `OPENAI_BASE_URL` (override default endpoints).

If neither key is set, stop and report: `No API key set. Set LITELLM_API_KEY or OPENAI_API_KEY.`

Every command saves to the given output path. With `--n > 1`, extra images get a `-2`, `-3`, … suffix (e.g. `out.png`, `out-2.png`).

---

## generate — text → image

```bash
python script/draw.py generate "<prompt>" out.png --aspect-ratio 16:9
# equivalent (command omitted):
python script/draw.py "<prompt>" out.png --aspect-ratio 16:9
```

**Inputs**

| Argument | Required | Description |
|---|---|---|
| `prompt` | yes | Text prompt (positional). |
| `output` | yes | Output file path (positional). |
| `--model` | no | Model name. Default `gpt`. |
| `--aspect-ratio` | no | `16:9`, `9:16`, `1:1`, … → mapped to `--size` if `--size` unset. |
| `--size` | no | e.g. `1024x1024`, `1536x1024`, `1024x1536`. |
| `--n` | no | Number of images. |
| `--quality` | no | `low` / `medium` / `high` / `auto`. |
| `--style` | no | `vivid` / `natural`. |
| `--background` | no | `transparent` / `opaque` / `auto`. |
| `--output-format` | no | `png` / `jpeg` / `webp`. |
| `--output-compression` | no | `0`–`100`. |
| `--moderation` | no | `auto` / `low`. |
| `--response-format` | no | `b64_json` / `url`. |
| `--partial-images` | no | `0`–`3`. |
| `--stream` | no | Stream and save the final image. |
| `--user` | no | End-user identifier. |

**Output**: the generated image saved to `output`.

---

## edit — image(s) + prompt → image

```bash
python script/draw.py edit out.png --image in.png --prompt "Add a party hat" --mask mask.png
```

**Inputs**

| Argument | Required | Description |
|---|---|---|
| `output` | yes | Output file path (positional). |
| `--image` | yes | Input image; repeat the flag for multiple images. |
| `--prompt` | yes | Edit instruction. |
| `--mask` | no | Mask image marking the area to edit. |
| `--model` | no | Model name. Default `gpt`. |
| `--n` | no | Number of images. |
| `--size` | no | e.g. `1024x1024`, `1536x1024`, `1024x1536`. |
| `--quality` | no | `low` / `medium` / `high` / `auto`. |
| `--background` | no | `transparent` / `opaque` / `auto`. |
| `--output-format` | no | `png` / `jpeg` / `webp`. |
| `--output-compression` | no | `0`–`100`. |
| `--input-fidelity` | no | `high` / `low`. |
| `--moderation` | no | `auto` / `low`. |
| `--partial-images` | no | `0`–`3`. |
| `--stream` | no | Stream and save the final image. |
| `--user` | no | End-user identifier. |

**Output**: the edited image saved to `output`.

---

## variation — image → variations

```bash
python script/draw.py variation out.png --image in.png --n 3 --size 512x512
```

**Inputs**

| Argument | Required | Description |
|---|---|---|
| `output` | yes | Output file path (positional). |
| `--image` | yes | Source image. |
| `--model` | no | Model name. Default `dall-e-2`. |
| `--n` | no | Number of variations. |
| `--size` | no | `256x256` / `512x512` / `1024x1024`. |
| `--response-format` | no | `b64_json` / `url`. |
| `--user` | no | End-user identifier. |

**Output**: the variation image(s) saved to `output`.
