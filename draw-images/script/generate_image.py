#!/usr/bin/env python3
"""Generate images using Gemini API."""

import argparse
import base64
import json
import os
import sys
import urllib.request
import urllib.error


def get_api_key():
    """Get API key from environment variable."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set", file=sys.stderr)
        sys.exit(1)
    return api_key


def generate_image(prompt: str) -> dict:
    """Call Gemini API to generate an image."""
    api_key = get_api_key()
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-image-preview:generateContent"

    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json",
    }

    payload = {
        "contents": [{
            "role": "user",
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"]
        }
    }

    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        print(f"Error: API request failed with status {e.code}", file=sys.stderr)
        if error_body:
            try:
                error_json = json.loads(error_body)
                print(f"Details: {json.dumps(error_json, indent=2)}", file=sys.stderr)
            except json.JSONDecodeError:
                print(f"Details: {error_body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error: Network error - {e.reason}", file=sys.stderr)
        sys.exit(1)
    except TimeoutError:
        print("Error: Request timed out", file=sys.stderr)
        sys.exit(1)


def extract_image_data(response: dict) -> tuple[bytes, str]:
    """Extract image data from API response."""
    candidates = response.get("candidates", [])
    if not candidates:
        print("Error: No candidates in response", file=sys.stderr)
        sys.exit(1)

    content = candidates[0].get("content", {})
    parts = content.get("parts", [])

    for part in parts:
        if "inlineData" in part:
            inline_data = part["inlineData"]
            mime_type = inline_data.get("mimeType", "image/png")
            base64_data = inline_data.get("data", "")

            if not base64_data:
                print("Error: Empty image data in response", file=sys.stderr)
                sys.exit(1)

            try:
                image_bytes = base64.b64decode(base64_data)
                return image_bytes, mime_type
            except Exception as e:
                print(f"Error: Failed to decode base64 data - {e}", file=sys.stderr)
                sys.exit(1)

    print("Error: No image data found in response", file=sys.stderr)
    sys.exit(1)


def save_image(image_bytes: bytes, output_path: str) -> str:
    """Save image bytes to file."""
    try:
        parent_dir = os.path.dirname(output_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(image_bytes)
        return output_path
    except IOError as e:
        print(f"Error: Failed to save image - {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Generate images using Gemini API")
    parser.add_argument("prompt", help="Text prompt for image generation")
    parser.add_argument("output", help="Output file path")
    args = parser.parse_args()

    if not args.prompt.strip():
        print("Error: Prompt cannot be empty", file=sys.stderr)
        sys.exit(1)

    print(f"Generating image for: {args.prompt[:50]}{'...' if len(args.prompt) > 50 else ''}")

    response = generate_image(args.prompt)
    image_bytes, _ = extract_image_data(response)

    save_image(image_bytes, args.output)
    print(f"Image saved to: {args.output}")


if __name__ == "__main__":
    main()
