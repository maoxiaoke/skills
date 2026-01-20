---
name: draw-images
description: Generate images using Nano Banana, an advanced AI image generation and editing tool. Use this skill to create stunning visuals, icons, flows, diagrams, and more.
---

# Draw Images

This skill provides guidance for creating images using Nano Banana.

## Quick Start

### Step 1: Make sure GEMINI_API_KEY is provided

GEMINI_API_KEY need to be set in the environment variables. Use the following command to check if it is set:

```bash
printenv | grep 'GEMINI_API_KEY'
```

If it is not set, return `GEMINI_API_KEY is not set. Please set it in your environment variables.` immediately.

### Step 2: Generate images with Nano Banana

To generate images with Nano Banana, you can use the following command:

```bash
python script/generate_image.py "Your prompt here" proper_name.png --aspect-ratio 16:9
```

You should: 
- Replace `"Your prompt here"` with your desired prompt with specific, clear and descriptive details.
- Replace `proper_name.png` with the appropriate file name that fully describes the image.
- (Optional) `--aspect-ratio`: Specify the aspect ratio of the image. Default is 16:9.

**What the script does**
- Sends a request to Nano Banana's API with the provided prompt.
- Saves the image data to the specified output file.

**Aspect Ratio**

Choose the aspect ratio that best suits your needs. Common aspect ratios include 1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9 and 21:9.
Make sure no content is cropped or distorted.

## How to generate satisfactory images

### The Golden Rules of Prompting

- Get the Design right first

Your visual language is a foundation, not a polish layer.

- Use Natural Language & Full Sentences

Talk to the model as if you were briefing a human artist. Use proper grammar and descriptive adjectives.

- Be Specific and Descriptive

Vague prompts yield generic results.

- Provide Context (The “Why” or “For whom”)

Because the model “thinks,” giving it context helps it make logical artistic decisions.
