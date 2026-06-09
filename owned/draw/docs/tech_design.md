# 需求概述

把 `script/draw.py` 改造成**通用画图 CLI 工具**：基于 OpenAI ChatGPT 图像模型，完整覆盖三种方法 —— **generate / edit / variation**，每种方法支持其官方全部入参，并在公司内部自动走 liteproxy（litellm）转发网关。

> 历史背景：本工具最初仅支持 Gemini，随后扩展到 Gemini + OpenAI，**当前版本已移除 Gemini 支持，仅保留 OpenAI**。

**目标**
- OpenAI 三个 method 以**子命令**形式暴露：`generate` / `edit` / `variation`。
- 公司内部环境自动走 liteproxy（Bearer 认证 + `pub-*` / 内部模型名）；公网环境自动走官方 OpenAI API。
- 认证与网关地址全部走环境变量，**不硬编码 key**。
- 向后兼容现有 `prompt / output / --aspect-ratio` 调用方式（不带子命令默认 `generate`）。

## 术语

- **liteproxy / litellm**：公司内部的 LLM 网关（`https://litellm-sg.mayfair-inc.com`），用统一的 `Authorization: Bearer sk-xxx` 转发到各家模型。
- **backend**：请求实际落到的端点，分 `public`（官方公网 OpenAI API）与 `liteproxy`（公司内部网关）。
- **method / 子命令**：OpenAI 图像三种方法 —— `generate`（文生图）、`edit`（图+提示词改图）、`variation`（图生变体，无 prompt）。
- **codec**：针对某个 method 的「请求体构造 + 响应解图」逻辑。

> liteproxy 与公网 API 的差异本质只有两处：**网关 base URL** 和 **认证用的 key**（均为 `Authorization: Bearer`）。协议体本身不变。

## 用例图

```
                ┌──────────────────────────────────────────────┐
   user ───▶    │                 draw.py (CLI)                │
                │   <subcommand> generate | edit | variation   │
                └───────────────────┬──────────────────────────┘
                                    │ resolve_model() → backend (auto-detect)
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                            ▼
    generate (JSON)            edit (multipart)          variation (multipart)
    openai_generate            openai_edit               openai_variation
    /v1/images/generations     /v1/images/edits          /v1/images/variations
        │                           │                            │
        └───────────► extract images (b64_json / url / SSE) ◄────┘
                                    │
                          save_images() —— n>1 自动加 -2/-3 后缀
```

# 数据模型

> 本工具是无状态 CLI，无数据库、无持久化模型。下面定义内部配置与协议的数据结构。

## 模型别名映射表（核心配置）

| `--model` 别名 | public 模型名 | liteproxy 模型名 |
|---|---|---|
| `gpt` / `chatgpt` / `openai`（generate/edit 默认） | `gpt-image-2-2026-04-21` | `gpt-image-2` |
| `dall-e-2`（variation 默认，完整名直传） | `dall-e-2` | `dall-e-2` |

> `--model` 也接受完整真实名（如 `gpt-image-1.5`、`dall-e-3`），此时直接作为模型名透传，不走别名映射。
> 各子命令默认模型：`generate`=`gpt`、`edit`=`gpt`、`variation`=`dall-e-2`（官方目前仅 dall-e-2 支持 variation）。

## 环境变量约定

| 环境变量 | 用途 | 必填 |
|---|---|---|
| `LITELLM_API_KEY` | liteproxy Bearer token | 配了即触发 liteproxy backend |
| `LITELLM_BASE_URL` | liteproxy 网关地址，默认 `https://litellm-sg.mayfair-inc.com` | 否 |
| `OPENAI_API_KEY` | 公网 OpenAI key（`Authorization: Bearer`） | 走公网时必填 |
| `OPENAI_BASE_URL` | 公网 OpenAI 地址，默认 `https://api.openai.com` | 否 |

**后端自动探测逻辑**：若 `LITELLM_API_KEY` 已设置 → 走 liteproxy（模型名用 liteproxy 列，认证 `Authorization: Bearer $LITELLM_API_KEY`）；否则走 public（用 `$OPENAI_API_KEY`）。**纯自动探测，无 `--backend` 覆盖参数**。

## 数据库表设计
无。本工具不涉及数据库。

## ER 图
无变更。

## 接口设计（对外调用的第三方接口）

> 全部统一认证：`Authorization: Bearer <key>`（public 用 `$OPENAI_API_KEY`，liteproxy 用 `$LITELLM_API_KEY`）；`{base}` = public `$OPENAI_BASE_URL` / liteproxy `$LITELLM_BASE_URL`。

### generate — `POST {base}/v1/images/generations`（JSON）

- **入参**（全部 pass-through，None 自动省略）：`model`、`prompt`(必填)、`n`、`size`、`quality`、`style`、`response_format`、`output_format`、`output_compression`、`background`、`moderation`、`partial_images`、`user`、`stream`。
  - `--aspect-ratio` → `size` 映射（仅当未显式给 `--size`）：`16:9`/`3:2`→`1536x1024`，`9:16`/`2:3`→`1024x1536`，`1:1`→`1024x1024`，其余省略 `size`。
- **出参**：`data[].b64_json`（base64）或 `data[].url`（DALL-E，需下载）。

### edit — `POST {base}/v1/images/edits`（multipart/form-data）

- **文件字段**：`image`（单张）或 `image[]`（多张，`--image` 可重复）；可选 `mask`。
- **标量入参**（form 字段，pass-through）：`model`、`prompt`(必填)、`n`、`size`、`quality`、`background`、`output_format`、`output_compression`、`input_fidelity`、`moderation`、`partial_images`、`user`、`stream`。
- **出参**：同 generate（`b64_json` / `url` / SSE）。

### variation — `POST {base}/v1/images/variations`（multipart/form-data）

- **文件字段**：`image`（必填，无 prompt）。
- **标量入参**：`model`、`n`、`size`、`response_format`、`user`。
- **出参**：同上。官方目前仅 `dall-e-2` 支持。

### 响应解析与流式

- 非流式：从 `data[]` 逐项取 `b64_json` 解码；若为 `url`（DALL-E）则用 urllib 下载字节。
- 流式（`--stream`）：响应为 SSE，逐事件解析，取 `type` 以 `completed` 结尾且含 `b64_json` 的事件作为最终图（不做中间帧渲染）。

# 实现要点（CLI 行为）

- **子命令**（argparse subparsers）：`generate` / `edit` / `variation`，一一对应 OpenAI 三个 method。
- **向后兼容**：`sys.argv` 首参不是子命令且非 `-` 开头时，自动前置 `generate`。
- `resolve_model(model_arg)` → `{model, backend, base_url, headers}`，纯自动探测后端。
- `run(args)` 按 `args.mode` 分派到 `openai_generate` / `openai_edit` / `openai_variation`，统一返回 `list[bytes]`。
- `_openai_send()` 统一处理 JSON 与 multipart 两种 body，以及流式/非流式解析。
- `encode_multipart()` 纯标准库手写 multipart/form-data；文件 MIME 按扩展名推断。
- `save_images(images, output)`：第一张写 `output`，后续写 `<root>-2<ext>`、`<root>-3<ext>`…
- 错误处理统一走 `_http_post`（HTTPError/URLError/Timeout）与 `die()`；缺 key 时给出「该后端需要哪个环境变量」提示。
- **纯标准库**实现，无第三方依赖。

# 测试方案（scrum 要求覆盖率 > 85%）

- **单元测试**（mock `urllib.request.urlopen` / `_http_post`，不打真实网络）：
  - `resolve_model`：别名映射 / 完整名透传 / 默认值 / 缺 key 报错 / liteproxy 与 public 的 base_url 探测。
  - generate：全量入参 payload、`aspect-ratio→size` 映射与 `--size` 覆盖、`url` 下载、`--stream` SSE 解析、多图返回。
  - edit：单图 `image` / 多图 `image[]`、mask、multipart 字段与 Content-Type、缺文件报错。
  - variation：multipart 字段、多图返回。
  - 辅助：`encode_multipart`（跳过 None / 含文件）、`extract_openai_images`/`parse_sse_images` 错误路径、`download_url`、`save_images` 多图后缀、`guess_image_mime`、`run`/`main` 分派与默认子命令。
- **集成冒烟**（可选，需真实 key，默认 skip）：liteproxy 与公网各跑一次真实出图。

**实测结果**：35 个单元测试通过，行覆盖率 **98%**（远超 85% 门槛）。

# 已确认的设计决策

1. ✅ OpenAI liteproxy 模型名用 `gpt-image-2`（以跑通示例为准）。
2. ✅ 纯自动探测后端，不加 `--backend` 覆盖参数。
3. ✅ `--aspect-ratio → size` 映射保留；同时支持独立 `--size`（显式给定时优先）。
4. ✅ OpenAI 三方法以子命令暴露（= 直接暴露三个 method）；不带子命令默认 `generate`。
5. ✅ `--stream` 按 SSE 解析最终图保存，不渲染中间帧。
6. ✅ **移除 Gemini 支持**，工具仅保留 OpenAI（移除 `gemini` 别名、`gemini_codec`、`GEMINI_API_KEY` / `GEMINI_BASE_URL`、provider 分支与 require_openai 校验）。
