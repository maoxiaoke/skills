#!/usr/bin/env python3
"""Generate / edit / vary images using OpenAI (ChatGPT) image models.

Backends are auto-detected from the environment:
  - liteproxy (company internal litellm gateway) when LITELLM_API_KEY is set
  - public OpenAI API otherwise

The three OpenAI image methods are exposed as subcommands:
    draw.py generate "<prompt>" out.png [--model gpt] [...]
    draw.py edit out.png --image in.png --prompt "<prompt>" [--mask m.png] [...]
    draw.py variation out.png --image in.png [--model dall-e-2] [...]

`generate` is the default when no subcommand is given (backward compatible):
    draw.py "<prompt>" out.png --aspect-ratio 16:9
"""

import argparse
import base64
import json
import os
import sys
import urllib.request
import urllib.error


DEFAULT_LITELLM_BASE_URL = "https://litellm-sg.mayfair-inc.com"
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com"

# alias -> (public model name, liteproxy model name)
MODEL_ALIASES = {
    "gpt": ("gpt-image-2-2026-04-21", "gpt-image-2"),
    "chatgpt": ("gpt-image-2-2026-04-21", "gpt-image-2"),
    "openai": ("gpt-image-2-2026-04-21", "gpt-image-2"),
}

# aspect ratio -> OpenAI image size (used when --size is not given)
ASPECT_RATIO_TO_SIZE = {
    "16:9": "1536x1024",
    "3:2": "1536x1024",
    "9:16": "1024x1536",
    "2:3": "1024x1536",
    "1:1": "1024x1024",
}

MULTIPART_BOUNDARY = "----DrawImageBoundary7MA4YWxkTrZu0gW"


def die(message: str) -> None:
    """Print an error to stderr and exit."""
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)


def require_key(env_name: str, backend_desc: str) -> str:
    """Fetch a required API key or exit with a clear message."""
    key = os.environ.get(env_name)
    if not key:
        die(
            f"{env_name} is not set (required for {backend_desc} backend). "
            f"Set {env_name}, or set LITELLM_API_KEY to use the internal liteproxy."
        )
    return key


def resolve_model(model_arg: str) -> dict:
    """Resolve --model into a concrete request config.

    Returns: model, backend, base_url, headers.
    """
    using_liteproxy = bool(os.environ.get("LITELLM_API_KEY"))

    if model_arg in MODEL_ALIASES:
        public_model, liteproxy_model = MODEL_ALIASES[model_arg]
        model_name = liteproxy_model if using_liteproxy else public_model
    else:
        model_name = model_arg  # full/explicit model name, e.g. dall-e-2

    if using_liteproxy:
        backend = "liteproxy"
        base_url = os.environ.get("LITELLM_BASE_URL", DEFAULT_LITELLM_BASE_URL)
        key = os.environ["LITELLM_API_KEY"]
    else:
        backend = "public"
        base_url = os.environ.get("OPENAI_BASE_URL", DEFAULT_OPENAI_BASE_URL)
        key = require_key("OPENAI_API_KEY", "public OpenAI")

    return {
        "model": model_name,
        "backend": backend,
        "base_url": base_url.rstrip("/"),
        "headers": {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    }


# --------------------------------------------------------------------------- #
# HTTP helpers
# --------------------------------------------------------------------------- #

def _http_post(url: str, headers: dict, data: bytes) -> bytes:
    """POST raw bytes, returning the raw response body, exiting on failure."""
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return response.read()
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        print(f"Error: API request failed with status {e.code}", file=sys.stderr)
        if error_body:
            try:
                print(f"Details: {json.dumps(json.loads(error_body), indent=2)}", file=sys.stderr)
            except json.JSONDecodeError:
                print(f"Details: {error_body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        die(f"Network error - {e.reason}")
    except TimeoutError:
        die("Request timed out")


def download_url(url: str) -> bytes:
    """GET a URL and return its raw bytes (used for DALL-E url responses)."""
    try:
        with urllib.request.urlopen(url, timeout=120) as response:
            return response.read()
    except (urllib.error.HTTPError, urllib.error.URLError) as e:
        die(f"Failed to download image from url - {e}")


def guess_image_mime(path: str) -> str:
    """Best-effort MIME type from a file extension."""
    ext = os.path.splitext(path)[1].lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(ext, "application/octet-stream")


def read_file_bytes(path: str) -> bytes:
    """Read a local file or exit with a clear error."""
    try:
        with open(path, "rb") as f:
            return f.read()
    except IOError as e:
        die(f"Cannot read input image '{path}' - {e}")


def encode_multipart(fields: dict, files: list) -> tuple[bytes, str]:
    """Encode form fields + files as multipart/form-data.

    fields: {name: scalar}; files: [(field_name, filename, bytes)].
    Returns (body_bytes, content_type_header).
    """
    crlf = b"\r\n"
    boundary = MULTIPART_BOUNDARY
    parts = []
    for name, value in fields.items():
        if value is None:
            continue
        parts.append(b"--" + boundary.encode())
        parts.append(f'Content-Disposition: form-data; name="{name}"'.encode())
        parts.append(b"")
        parts.append(str(value).encode("utf-8"))
    for field_name, filename, file_bytes in files:
        parts.append(b"--" + boundary.encode())
        parts.append(
            f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"'.encode()
        )
        parts.append(f"Content-Type: {guess_image_mime(filename)}".encode())
        parts.append(b"")
        parts.append(file_bytes)
    parts.append(b"--" + boundary.encode() + b"--")
    parts.append(b"")
    return crlf.join(parts), f"multipart/form-data; boundary={boundary}"


def decode_base64(base64_data: str) -> bytes:
    """Decode base64 image data or exit with a clear error."""
    try:
        return base64.b64decode(base64_data)
    except Exception as e:
        die(f"Failed to decode base64 data - {e}")


def add_if_set(payload: dict, key: str, value) -> None:
    """Add a key to payload only when value is not None."""
    if value is not None:
        payload[key] = value


# --------------------------------------------------------------------------- #
# Response extraction
# --------------------------------------------------------------------------- #

def extract_openai_images(response: dict) -> list:
    """Extract image bytes from a (non-streaming) OpenAI images response."""
    data = response.get("data", [])
    if not data:
        die("No image data found in response")
    images = []
    for item in data:
        if item.get("b64_json"):
            images.append(decode_base64(item["b64_json"]))
        elif item.get("url"):
            images.append(download_url(item["url"]))
    if not images:
        die("Empty image data in response")
    return images


def parse_sse_images(raw: bytes) -> list:
    """Extract final image bytes from an OpenAI streaming (SSE) response."""
    images = []
    for block in raw.decode("utf-8", "replace").split("\n\n"):
        data_payload = "".join(
            line[5:].strip() for line in block.splitlines() if line.startswith("data:")
        )
        if not data_payload or data_payload == "[DONE]":
            continue
        try:
            event = json.loads(data_payload)
        except json.JSONDecodeError:
            continue
        if event.get("type", "").endswith("completed") and event.get("b64_json"):
            images.append(decode_base64(event["b64_json"]))
    if not images:
        die("No completed image found in streaming response")
    return images


# --------------------------------------------------------------------------- #
# Codecs
# --------------------------------------------------------------------------- #

def _openai_send(config: dict, url: str, payload: dict = None,
                 files: list = None, stream: bool = False) -> list:
    """Send an OpenAI image request (JSON or multipart) and return image bytes."""
    if files is not None:
        body, content_type = encode_multipart(payload, files)
        headers = dict(config["headers"])
        headers["Content-Type"] = content_type
        raw = _http_post(url, headers, body)
    else:
        raw = _http_post(url, config["headers"], json.dumps(payload).encode("utf-8"))

    if stream:
        return parse_sse_images(raw)
    return extract_openai_images(json.loads(raw.decode("utf-8")))


def openai_generate(config: dict, args) -> list:
    """POST /v1/images/generations."""
    payload = {"model": config["model"], "prompt": args.prompt}
    size = args.size or ASPECT_RATIO_TO_SIZE.get(getattr(args, "aspect_ratio", None) or "")
    add_if_set(payload, "size", size or None)
    add_if_set(payload, "n", args.n)
    add_if_set(payload, "quality", args.quality)
    add_if_set(payload, "style", args.style)
    add_if_set(payload, "response_format", args.response_format)
    add_if_set(payload, "output_format", args.output_format)
    add_if_set(payload, "output_compression", args.output_compression)
    add_if_set(payload, "background", args.background)
    add_if_set(payload, "moderation", args.moderation)
    add_if_set(payload, "partial_images", args.partial_images)
    add_if_set(payload, "user", args.user)
    if args.stream:
        payload["stream"] = True
    return _openai_send(config, f"{config['base_url']}/v1/images/generations",
                        payload=payload, stream=args.stream)


def openai_edit(config: dict, args) -> list:
    """POST /v1/images/edits (multipart)."""
    fields = {"model": config["model"], "prompt": args.prompt}
    add_if_set(fields, "n", args.n)
    add_if_set(fields, "size", args.size)
    add_if_set(fields, "quality", args.quality)
    add_if_set(fields, "background", args.background)
    add_if_set(fields, "output_format", args.output_format)
    add_if_set(fields, "output_compression", args.output_compression)
    add_if_set(fields, "input_fidelity", args.input_fidelity)
    add_if_set(fields, "moderation", args.moderation)
    add_if_set(fields, "partial_images", args.partial_images)
    add_if_set(fields, "user", args.user)
    if args.stream:
        fields["stream"] = "true"

    image_field = "image" if len(args.image) == 1 else "image[]"
    files = [(image_field, os.path.basename(p), read_file_bytes(p)) for p in args.image]
    if args.mask:
        files.append(("mask", os.path.basename(args.mask), read_file_bytes(args.mask)))

    return _openai_send(config, f"{config['base_url']}/v1/images/edits",
                        payload=fields, files=files, stream=args.stream)


def openai_variation(config: dict, args) -> list:
    """POST /v1/images/variations (multipart)."""
    fields = {"model": config["model"]}
    add_if_set(fields, "n", args.n)
    add_if_set(fields, "size", args.size)
    add_if_set(fields, "response_format", args.response_format)
    add_if_set(fields, "user", args.user)

    files = [("image", os.path.basename(args.image), read_file_bytes(args.image))]
    return _openai_send(config, f"{config['base_url']}/v1/images/variations",
                        payload=fields, files=files)


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #

def save_images(images: list, output_path: str) -> list:
    """Save one or more images; extra images get a `-2`, `-3`, ... suffix."""
    root, ext = os.path.splitext(output_path)
    paths = []
    for i, image_bytes in enumerate(images):
        path = output_path if i == 0 else f"{root}-{i + 1}{ext}"
        try:
            parent_dir = os.path.dirname(path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            with open(path, "wb") as f:
                f.write(image_bytes)
        except IOError as e:
            die(f"Failed to save image - {e}")
        paths.append(path)
    return paths


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate / edit / vary images with OpenAI image models")
    sub = parser.add_subparsers(dest="mode")

    g = sub.add_parser("generate", help="Generate an image from a text prompt")
    g.add_argument("prompt")
    g.add_argument("output")
    g.add_argument("--model", default="gpt", help="gpt (default) or a full model name")
    g.add_argument("--aspect-ratio", help="Mapped to --size when --size is unset")
    g.add_argument("--n", type=int)
    g.add_argument("--size")
    g.add_argument("--quality")
    g.add_argument("--style")
    g.add_argument("--response-format")
    g.add_argument("--output-format")
    g.add_argument("--output-compression", type=int)
    g.add_argument("--background")
    g.add_argument("--moderation")
    g.add_argument("--partial-images", type=int)
    g.add_argument("--user")
    g.add_argument("--stream", action="store_true")

    e = sub.add_parser("edit", help="Edit image(s) with a prompt")
    e.add_argument("output")
    e.add_argument("--image", action="append", required=True, help="Input image (repeatable)")
    e.add_argument("--prompt", required=True)
    e.add_argument("--mask")
    e.add_argument("--model", default="gpt")
    e.add_argument("--n", type=int)
    e.add_argument("--size")
    e.add_argument("--quality")
    e.add_argument("--background")
    e.add_argument("--output-format")
    e.add_argument("--output-compression", type=int)
    e.add_argument("--input-fidelity")
    e.add_argument("--moderation")
    e.add_argument("--partial-images", type=int)
    e.add_argument("--user")
    e.add_argument("--stream", action="store_true")

    v = sub.add_parser("variation", help="Create variations of an image")
    v.add_argument("output")
    v.add_argument("--image", required=True)
    v.add_argument("--model", default="dall-e-2")
    v.add_argument("--n", type=int)
    v.add_argument("--size")
    v.add_argument("--response-format")
    v.add_argument("--user")

    return parser


def run(args) -> list:
    """Dispatch a parsed args namespace to the right codec, returning image bytes."""
    config = resolve_model(args.model)
    if args.mode == "generate":
        if not args.prompt.strip():
            die("Prompt cannot be empty")
        return openai_generate(config, args)
    if args.mode == "edit":
        return openai_edit(config, args)
    return openai_variation(config, args)  # variation


def main():
    argv = sys.argv[1:]
    modes = {"generate", "edit", "variation"}
    # Backward compatible: no subcommand -> default to `generate`.
    if argv and argv[0] not in modes and not argv[0].startswith("-"):
        argv = ["generate"] + argv

    args = build_parser().parse_args(argv)
    if not args.mode:
        build_parser().print_help()
        sys.exit(1)

    label = getattr(args, "prompt", None) or args.image
    label = label if isinstance(label, str) else str(label)
    print(f"[{args.mode}] {label[:50]}{'...' if len(label) > 50 else ''}")

    images = run(args)
    paths = save_images(images, args.output)
    print(f"Saved {len(paths)} image(s): {', '.join(paths)}")


if __name__ == "__main__":
    main()
