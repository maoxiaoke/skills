#!/usr/bin/env python3
"""Unit tests for draw.py (no real network calls)."""

import base64
import io
import json
import os
import tempfile
import unittest
import urllib.error
from unittest import mock

import draw as gi


PNG_BYTES = b"\x89PNG\r\n\x1a\nfakepng"
PNG_B64 = base64.b64encode(PNG_BYTES).decode()
PNG2_BYTES = b"\x89PNG\r\n\x1a\nsecond"
PNG2_B64 = base64.b64encode(PNG2_BYTES).decode()


def clear_env():
    for k in ("LITELLM_API_KEY", "LITELLM_BASE_URL", "OPENAI_API_KEY", "OPENAI_BASE_URL"):
        os.environ.pop(k, None)


def parse_args(argv):
    return gi.build_parser().parse_args(argv)


class ResolveModelTest(unittest.TestCase):
    def setUp(self):
        clear_env()
        self.addCleanup(clear_env)

    def test_public_alias(self):
        os.environ["OPENAI_API_KEY"] = "o-key"
        cfg = gi.resolve_model("gpt")
        self.assertEqual(cfg["model"], "gpt-image-2-2026-04-21")
        self.assertEqual(cfg["backend"], "public")
        self.assertEqual(cfg["base_url"], gi.DEFAULT_OPENAI_BASE_URL)
        self.assertEqual(cfg["headers"]["Authorization"], "Bearer o-key")

    def test_liteproxy_alias_uses_gpt_image_2(self):
        os.environ["LITELLM_API_KEY"] = "sk-lite"
        cfg = gi.resolve_model("gpt")
        self.assertEqual(cfg["backend"], "liteproxy")
        self.assertEqual(cfg["model"], "gpt-image-2")
        self.assertEqual(cfg["base_url"], gi.DEFAULT_LITELLM_BASE_URL)
        self.assertEqual(cfg["headers"]["Authorization"], "Bearer sk-lite")

    def test_liteproxy_custom_base_url(self):
        os.environ["LITELLM_API_KEY"] = "sk-lite"
        os.environ["LITELLM_BASE_URL"] = "https://gw.internal/"
        self.assertEqual(gi.resolve_model("gpt")["base_url"], "https://gw.internal")

    def test_full_model_name_passthrough(self):
        os.environ["OPENAI_API_KEY"] = "o-key"
        cfg = gi.resolve_model("dall-e-2")
        self.assertEqual(cfg["model"], "dall-e-2")

    def test_public_custom_base_url(self):
        os.environ["OPENAI_API_KEY"] = "o-key"
        os.environ["OPENAI_BASE_URL"] = "https://proxy.example/"
        self.assertEqual(gi.resolve_model("gpt")["base_url"], "https://proxy.example")

    def test_missing_key_exits(self):
        with self.assertRaises(SystemExit):
            gi.resolve_model("gpt")


class OpenAIGenerateTest(unittest.TestCase):
    def setUp(self):
        clear_env()
        os.environ["OPENAI_API_KEY"] = "o-key"
        self.addCleanup(clear_env)

    def test_full_params_payload(self):
        cfg = gi.resolve_model("gpt")
        args = parse_args(["generate", "a dog", "out.png", "--model", "gpt",
                           "--n", "2", "--size", "1024x1024", "--quality", "high",
                           "--background", "transparent", "--output-format", "webp",
                           "--output-compression", "80", "--moderation", "low",
                           "--user", "u1"])
        sent = {}
        def fake_post(url, headers, data):
            sent["url"], sent["payload"] = url, json.loads(data.decode())
            return json.dumps({"data": [{"b64_json": PNG_B64}, {"b64_json": PNG2_B64}]}).encode()
        with mock.patch.object(gi, "_http_post", side_effect=fake_post):
            imgs = gi.openai_generate(cfg, args)
        self.assertEqual(imgs, [PNG_BYTES, PNG2_BYTES])
        self.assertTrue(sent["url"].endswith("/v1/images/generations"))
        p = sent["payload"]
        self.assertEqual(p["model"], "gpt-image-2-2026-04-21")
        self.assertEqual(p["n"], 2)
        self.assertEqual(p["size"], "1024x1024")
        self.assertEqual(p["quality"], "high")
        self.assertEqual(p["background"], "transparent")
        self.assertEqual(p["output_format"], "webp")
        self.assertEqual(p["output_compression"], 80)
        self.assertEqual(p["moderation"], "low")
        self.assertEqual(p["user"], "u1")

    def test_aspect_ratio_maps_to_size(self):
        cfg = gi.resolve_model("gpt")
        args = parse_args(["generate", "a dog", "out.png", "--aspect-ratio", "9:16"])
        with mock.patch.object(gi, "_http_post",
                               return_value=json.dumps({"data": [{"b64_json": PNG_B64}]}).encode()) as m:
            gi.openai_generate(cfg, args)
        self.assertEqual(json.loads(m.call_args[0][2].decode())["size"], "1024x1536")

    def test_explicit_size_overrides_aspect_ratio(self):
        cfg = gi.resolve_model("gpt")
        args = parse_args(["generate", "d", "o.png", "--aspect-ratio", "9:16", "--size", "1536x1024"])
        with mock.patch.object(gi, "_http_post",
                               return_value=json.dumps({"data": [{"b64_json": PNG_B64}]}).encode()) as m:
            gi.openai_generate(cfg, args)
        self.assertEqual(json.loads(m.call_args[0][2].decode())["size"], "1536x1024")

    def test_url_response_is_downloaded(self):
        cfg = gi.resolve_model("gpt")
        args = parse_args(["generate", "d", "o.png"])
        resp = json.dumps({"data": [{"url": "https://x/img.png"}]}).encode()
        with mock.patch.object(gi, "_http_post", return_value=resp), \
             mock.patch.object(gi, "download_url", return_value=PNG_BYTES) as dl:
            imgs = gi.openai_generate(cfg, args)
        dl.assert_called_once_with("https://x/img.png")
        self.assertEqual(imgs, [PNG_BYTES])

    def test_stream_parses_sse(self):
        cfg = gi.resolve_model("gpt")
        args = parse_args(["generate", "d", "o.png", "--stream"])
        sse = (f'data: {{"type":"image_generation.partial_image","b64_json":"{PNG_B64}"}}\n\n'
               f'data: {{"type":"image_generation.completed","b64_json":"{PNG_B64}"}}\n\n'
               'data: [DONE]\n\n').encode()
        with mock.patch.object(gi, "_http_post", return_value=sse) as m:
            imgs = gi.openai_generate(cfg, args)
        self.assertEqual(imgs, [PNG_BYTES])
        self.assertTrue(json.loads(m.call_args[0][2].decode())["stream"])


class OpenAIEditTest(unittest.TestCase):
    def setUp(self):
        clear_env()
        os.environ["OPENAI_API_KEY"] = "o-key"
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(clear_env)
        self.img_a = os.path.join(self.tmp.name, "a.png")
        self.img_b = os.path.join(self.tmp.name, "b.png")
        self.mask = os.path.join(self.tmp.name, "mask.png")
        for p in (self.img_a, self.img_b, self.mask):
            with open(p, "wb") as f:
                f.write(PNG_BYTES)

    def test_single_image_multipart(self):
        cfg = gi.resolve_model("gpt")
        args = parse_args(["edit", "out.png", "--image", self.img_a, "--prompt", "add a hat",
                           "--mask", self.mask, "--n", "1", "--size", "1024x1024",
                           "--input-fidelity", "high"])
        captured = {}
        def fake_post(url, headers, data):
            captured["url"], captured["ct"], captured["body"] = url, headers["Content-Type"], data
            return json.dumps({"data": [{"b64_json": PNG_B64}]}).encode()
        with mock.patch.object(gi, "_http_post", side_effect=fake_post):
            imgs = gi.openai_edit(cfg, args)
        self.assertEqual(imgs, [PNG_BYTES])
        self.assertTrue(captured["url"].endswith("/v1/images/edits"))
        self.assertTrue(captured["ct"].startswith("multipart/form-data; boundary="))
        body = captured["body"]
        self.assertIn(b'name="image"', body)
        self.assertIn(b'name="mask"', body)
        self.assertIn(b'name="prompt"', body)
        self.assertIn(b"add a hat", body)
        self.assertIn(b'name="input_fidelity"', body)

    def test_multiple_images_use_array_field(self):
        cfg = gi.resolve_model("gpt")
        args = parse_args(["edit", "out.png", "--image", self.img_a,
                           "--image", self.img_b, "--prompt", "merge"])
        with mock.patch.object(gi, "_http_post",
                               return_value=json.dumps({"data": [{"b64_json": PNG_B64}]}).encode()) as m:
            gi.openai_edit(cfg, args)
        self.assertIn(b'name="image[]"', m.call_args[0][2])

    def test_missing_input_file_exits(self):
        cfg = gi.resolve_model("gpt")
        args = parse_args(["edit", "out.png", "--image", "/no/such.png", "--prompt", "x"])
        with self.assertRaises(SystemExit):
            gi.openai_edit(cfg, args)


class OpenAIVariationTest(unittest.TestCase):
    def setUp(self):
        clear_env()
        os.environ["OPENAI_API_KEY"] = "o-key"
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(clear_env)
        self.img = os.path.join(self.tmp.name, "a.png")
        with open(self.img, "wb") as f:
            f.write(PNG_BYTES)

    def test_variation_multipart(self):
        cfg = gi.resolve_model("dall-e-2")
        args = parse_args(["variation", "out.png", "--image", self.img,
                           "--model", "dall-e-2", "--n", "2", "--size", "512x512",
                           "--response-format", "b64_json"])
        captured = {}
        def fake_post(url, headers, data):
            captured["url"], captured["body"] = url, data
            return json.dumps({"data": [{"b64_json": PNG_B64}, {"b64_json": PNG2_B64}]}).encode()
        with mock.patch.object(gi, "_http_post", side_effect=fake_post):
            imgs = gi.openai_variation(cfg, args)
        self.assertEqual(imgs, [PNG_BYTES, PNG2_BYTES])
        self.assertTrue(captured["url"].endswith("/v1/images/variations"))
        self.assertIn(b'name="image"', captured["body"])
        self.assertIn(b'name="response_format"', captured["body"])


class MultipartTest(unittest.TestCase):
    def test_encode_skips_none_and_includes_file(self):
        body, ct = gi.encode_multipart({"a": "1", "b": None}, [("image", "x.png", PNG_BYTES)])
        self.assertIn("boundary=", ct)
        self.assertIn(b'name="a"', body)
        self.assertNotIn(b'name="b"', body)
        self.assertIn(b'filename="x.png"', body)
        self.assertIn(PNG_BYTES, body)


class ExtractTest(unittest.TestCase):
    def test_no_data_exits(self):
        with self.assertRaises(SystemExit):
            gi.extract_openai_images({"data": []})

    def test_empty_items_exit(self):
        with self.assertRaises(SystemExit):
            gi.extract_openai_images({"data": [{}]})

    def test_sse_no_completed_exits(self):
        with self.assertRaises(SystemExit):
            gi.parse_sse_images(b'data: {"type":"x.partial_image","b64_json":"abc"}\n\n')


class HttpTest(unittest.TestCase):
    def _ctx(self, payload_bytes):
        fake = io.BytesIO(payload_bytes)
        fake.__enter__ = lambda s: s
        fake.__exit__ = lambda s, *a: False
        return fake

    def test_post_raw_success(self):
        with mock.patch("urllib.request.urlopen", return_value=self._ctx(b'{"ok":true}')):
            self.assertEqual(gi._http_post("http://x", {}, b""), b'{"ok":true}')

    def test_http_error_exits(self):
        err = urllib.error.HTTPError("http://x", 400, "Bad", {}, io.BytesIO(b'{"e":1}'))
        with mock.patch("urllib.request.urlopen", side_effect=err):
            with self.assertRaises(SystemExit):
                gi._http_post("http://x", {}, b"")

    def test_url_error_exits(self):
        with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("down")):
            with self.assertRaises(SystemExit):
                gi._http_post("http://x", {}, b"")

    def test_timeout_exits(self):
        with mock.patch("urllib.request.urlopen", side_effect=TimeoutError):
            with self.assertRaises(SystemExit):
                gi._http_post("http://x", {}, b"")

    def test_download_url_success(self):
        with mock.patch("urllib.request.urlopen", return_value=self._ctx(PNG_BYTES)):
            self.assertEqual(gi.download_url("http://x/i.png"), PNG_BYTES)

    def test_download_url_error_exits(self):
        with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("x")):
            with self.assertRaises(SystemExit):
                gi.download_url("http://x/i.png")


class DecodeAndSaveTest(unittest.TestCase):
    def test_bad_base64_exits(self):
        with self.assertRaises(SystemExit):
            gi.decode_base64("!!!not-base64!!!")

    def test_save_multiple_images_suffixes(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "sub", "img.png")
            paths = gi.save_images([PNG_BYTES, PNG2_BYTES], out)
        self.assertEqual(paths[0], out)
        self.assertTrue(paths[1].endswith("img-2.png"))

    def test_save_io_error_exits(self):
        with mock.patch("builtins.open", side_effect=IOError("nope")):
            with self.assertRaises(SystemExit):
                gi.save_images([PNG_BYTES], "img.png")


class GuessMimeTest(unittest.TestCase):
    def test_known_and_unknown(self):
        self.assertEqual(gi.guess_image_mime("a.jpg"), "image/jpeg")
        self.assertEqual(gi.guess_image_mime("a.bin"), "application/octet-stream")


class RunDispatchTest(unittest.TestCase):
    def setUp(self):
        clear_env()
        os.environ["OPENAI_API_KEY"] = "o-key"
        self.addCleanup(clear_env)

    def test_generate_dispatch(self):
        args = parse_args(["generate", "p", "o.png"])
        with mock.patch.object(gi, "openai_generate", return_value=[PNG_BYTES]) as om:
            self.assertEqual(gi.run(args), [PNG_BYTES])
        om.assert_called_once()

    def test_generate_empty_prompt_exits(self):
        args = parse_args(["generate", "   ", "o.png"])
        with self.assertRaises(SystemExit):
            gi.run(args)

    def test_edit_dispatch(self):
        args = parse_args(["edit", "o.png", "--image", "a.png", "--prompt", "x"])
        with mock.patch.object(gi, "openai_edit", return_value=[PNG_BYTES]) as em:
            gi.run(args)
        em.assert_called_once()

    def test_variation_dispatch(self):
        args = parse_args(["variation", "o.png", "--image", "a.png", "--model", "dall-e-2"])
        with mock.patch.object(gi, "openai_variation", return_value=[PNG_BYTES]) as vm:
            gi.run(args)
        vm.assert_called_once()


class MainTest(unittest.TestCase):
    def setUp(self):
        clear_env()
        os.environ["OPENAI_API_KEY"] = "o-key"
        self.addCleanup(clear_env)

    def test_main_default_subcommand_is_generate(self):
        with mock.patch("sys.argv", ["prog", "a cat", "out.png"]), \
             mock.patch.object(gi, "run", return_value=[PNG_BYTES]) as r, \
             mock.patch.object(gi, "save_images", return_value=["out.png"]):
            gi.main()
        self.assertEqual(r.call_args[0][0].mode, "generate")
        self.assertEqual(r.call_args[0][0].prompt, "a cat")

    def test_main_no_args_prints_help_and_exits(self):
        with mock.patch("sys.argv", ["prog"]):
            with self.assertRaises(SystemExit):
                gi.main()


if __name__ == "__main__":
    unittest.main()
