import importlib.util
import json
import os
import shutil
import subprocess
from pathlib import Path

from cpu_jev.types import SelectDecision, SelectRequest, YesNoDecision, YesNoRequest

GGUF_FILENAME = "Qwen3-0.6B-Q8_0.gguf"
GGUF_URL = "https://huggingface.co/Qwen/Qwen3-0.6B-GGUF"
N_GPU_LAYERS = 0
N_CTX = 2048
N_PREDICT = 192
TEMPERATURE = 0.6
TOP_P = 0.95
TOP_K = 20
MIN_P = 0.0
PRESENCE_PENALTY = 1.5


class RunnerError(RuntimeError):
    pass


def select(request: SelectRequest) -> SelectDecision:
    from cpu_jev.api import select_decision
    from cpu_jev.prompt import render_select

    return select_decision(request, complete(render_select(request)))


def yes_no(request: YesNoRequest) -> YesNoDecision:
    from cpu_jev.api import yes_no_decision
    from cpu_jev.prompt import render_yes_no

    return yes_no_decision(request, complete(render_yes_no(request)))


def available() -> bool:
    try:
        resolve_gguf()
    except RunnerError:
        return False
    return llama_cli() is not None or llama_cpp_installed()


def complete(prompt: str) -> str:
    if not isinstance(prompt, str) or prompt.strip() == "":
        raise RunnerError("prompt must be a non-empty string")
    gguf = resolve_gguf()
    cli = llama_cli()
    if cli is not None:
        return _complete_cli(cli, gguf, prompt)
    if llama_cpp_installed():
        return _complete_library(gguf, prompt)
    raise RunnerError(_missing_backend())


def resolve_gguf() -> str:
    for path in _gguf_candidates():
        if path.is_file() and path.name == GGUF_FILENAME:
            return str(path.resolve())
        if path.exists() and path.name != GGUF_FILENAME:
            raise RunnerError(
                "CPU_JEV_GGUF must be the file Qwen3-0.6B-Q8_0.gguf. "
                "cpu-jev does not look for other quantizations."
            )
    raise RunnerError(_missing_backend())


def _gguf_candidates() -> list[Path]:
    raw = os.environ.get("CPU_JEV_GGUF", "").strip()
    if raw:
        path = Path(os.path.expanduser(raw))
        if path.is_dir():
            path = path / GGUF_FILENAME
        return [path]
    root = Path(__file__).resolve().parent.parent
    return [Path.cwd() / "models" / GGUF_FILENAME, root / "models" / GGUF_FILENAME]


def llama_cli() -> str | None:
    override = os.environ.get("CPU_JEV_LLAMA", "").strip()
    if override:
        path = os.path.expanduser(override)
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
        return None
    return shutil.which("llama-cli")


def llama_cpp_installed() -> bool:
    try:
        return importlib.util.find_spec("llama_cpp") is not None
    except (ImportError, ValueError):
        return False


def _missing_backend() -> str:
    return (
        "cpu-jev needs llama-cli or llama-cpp-python, and the GGUF file "
        f"{GGUF_FILENAME} from {GGUF_URL}. "
        "Set CPU_JEV_GGUF to that file and CPU_JEV_LLAMA to llama-cli if it is not on PATH. "
        "cpu-jev does not download weights and does not use a GPU."
    )


def _complete_cli(cli: str, gguf: str, prompt: str) -> str:
    command = [
        cli,
        "-m",
        gguf,
        "--offline",
        "--jinja",
        "--fit",
        "off",
        "-ngl",
        str(N_GPU_LAYERS),
        "--device",
        "none",
        "-c",
        str(N_CTX),
        "-n",
        str(N_PREDICT),
        "--temp",
        str(TEMPERATURE),
        "--top-p",
        str(TOP_P),
        "--top-k",
        str(TOP_K),
        "--min-p",
        str(MIN_P),
        "--presence-penalty",
        str(PRESENCE_PENALTY),
        "--reasoning",
        "on",
        "--reasoning-format",
        "none",
        "--reasoning-budget",
        "64",
        "--chat-template-kwargs",
        json.dumps({"enable_thinking": True}),
        "--simple-io",
        "--no-display-prompt",
        "--no-show-timings",
        "--color",
        "off",
        "--no-escape",
        "--no-warmup",
        "--single-turn",
        "--log-disable",
        "--prompt",
        prompt,
    ]
    env = os.environ.copy()
    env["LLAMA_ARG_N_GPU_LAYERS"] = "0"
    env["CUDA_VISIBLE_DEVICES"] = ""
    try:
        proc = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raise RunnerError("llama-cli timed out") from exc
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise RunnerError(detail[-2000:] or f"llama-cli exited {proc.returncode}")
    if proc.stdout.strip() == "":
        detail = (proc.stderr or "").strip()
        raise RunnerError(detail[-2000:] or "llama-cli returned an empty completion")
    return _cli_completion(proc.stdout)


def _complete_library(gguf: str, prompt: str) -> str:
    from llama_cpp import Llama

    model = Llama(
        model_path=gguf,
        n_gpu_layers=N_GPU_LAYERS,
        n_ctx=N_CTX,
        verbose=False,
    )
    sample = {
        "max_tokens": N_PREDICT,
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "top_k": TOP_K,
        "min_p": MIN_P,
        "presence_penalty": PRESENCE_PENALTY,
    }
    if not hasattr(model, "create_chat_completion"):
        raw = model(
            prompt,
            max_tokens=N_PREDICT,
            temperature=TEMPERATURE,
            top_p=TOP_P,
            top_k=TOP_K,
            presence_penalty=PRESENCE_PENALTY,
        )
        return raw["choices"][0]["text"]
    kwargs = {
        "messages": [{"role": "user", "content": prompt}],
        "chat_template_kwargs": {"enable_thinking": True},
        **sample,
    }
    try:
        response = model.create_chat_completion(**kwargs)
    except TypeError:
        kwargs.pop("min_p", None)
        kwargs.pop("chat_template_kwargs", None)
        response = model.create_chat_completion(**kwargs)
    message = response["choices"][0]["message"]
    text = _message_text(message)
    if text.strip() == "":
        raise RunnerError("llama-cpp-python returned an empty completion")
    return text


def _cli_completion(stdout: str) -> str:
    start = stdout.find("<think>")
    if start < 0:
        return stdout
    text = stdout[start:]
    marker = "\nExiting..."
    end = text.rfind(marker)
    if end >= 0:
        text = text[:end]
    return text


def _message_text(message: dict) -> str:
    content = message.get("content") or ""
    reasoning = message.get("reasoning_content") or ""
    if "<think>" in content and "</think>" in content:
        return content
    if reasoning.strip():
        body = reasoning.strip()
        return f"<think>\n{body}\n</think>\n{content}"
    return content
