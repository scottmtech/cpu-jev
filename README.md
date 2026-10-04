# cpu-jev

`select` picks one declared option id. `yes_no` answers yes or no. Each call builds a short prompt, reads a local Qwen3 completion on CPU, and returns the pick plus the `<think>` body. This first cut does not train a model and does not return a probability. The code license is MIT.

cpu-jev runs on CPU only. It is not TypeSafe Jev, it is not a Jev clone, and it has no calibrated probabilities. Hosted Jev scores choice, score, and noul questions. cpu-jev returns the pick and the model think text.

## Weights

The runner loads one official file, `Qwen3-0.6B-Q8_0.gguf`, published by Qwen at https://huggingface.co/Qwen/Qwen3-0.6B-GGUF under Apache-2.0. Point `CPU_JEV_GGUF` at a copy you already have. cpu-jev does not download weights and does not look for a Q4_K_M build.

## Call select and yes_no

Pass a `SelectRequest` or a `YesNoRequest`. Leave `complete` unset to run llama.cpp. Tests pass `complete` so they can feed a completion string without a GGUF.

```python
from cpu_jev import Option, SelectRequest, YesNoRequest, select, yes_no

route = SelectRequest(
    state="Customer: I was charged twice and nobody has replied for 3 days.",
    instructions="Where should this go?",
    options=(
        Option("billing", "money"),
        Option("bug", "broken"),
        Option("account", "login"),
    ),
)
picked = select(route)
print(picked.pick)
print(picked.reasoning)

gate = YesNoRequest(
    state="Customer: I was charged twice and nobody has replied for 3 days.",
    instructions="Escalate to a human now?",
)
answer = yes_no(gate)
print(answer.pick)
print(answer.reasoning)
```

`pick` on a select decision is one of the option ids. `pick` on a yes or no decision is `yes` or `no`. `reasoning` is the stripped think-tag body from the completion. A missing think tag raises `ParseError`. A pick outside the declared set raises `ParseError` too.

String state is copied into the prompt as text. Dict and list state are rendered with `json.dumps`.

## Run Qwen3-0.6B Q8_0 on CPU

The runner needs the GGUF file and a CPU llama.cpp backend.

- `CPU_JEV_GGUF` is the path to `Qwen3-0.6B-Q8_0.gguf`. A directory is accepted when that file sits inside it. If you leave it unset, the runner looks for `models/Qwen3-0.6B-Q8_0.gguf`.
- `CPU_JEV_LLAMA` is the path to `llama-cli`. If you leave it unset, the runner looks for `llama-cli` on `PATH`.

`llama-cli` is started with `--jinja`, `-ngl 0`, `--reasoning-format none`, `--reasoning-budget 64`, context 2048, and 192 tokens. Sampling follows Qwen3 thinking mode. Temperature is 0.6, top_p is 0.95, top_k is 20, min_p is 0, and presence_penalty is 1.5. The prompt starts with `/think` so Qwen3 thinking mode is on. If `llama-cli` is not available and `llama-cpp-python` is installed, `llama_cpp.Llama` runs with `n_gpu_layers` 0 and the same sampling. If neither backend can load that GGUF, the call raises `RunnerError`.

## How the tests compare

`fixtures/decide.json` and `fixtures/yes_no.json` are Jev-shaped requests. Each one has the published `state` and `questions` map and no Jev scores. `cpu_jev.fixtures.load` checks that shape. A choice question with a criteria map becomes a `SelectRequest`. A noul question becomes a `YesNoRequest`.

The default tests call `select` and `yes_no` with an injected completion. They assert the literal pick and the literal think body. They do not invent a Jev probability.

`tests/test_jev_live.py` skips unless `JEV_API_KEY` or `TYPESAFE_API_KEY` is set. With a key, it POSTs a fixture and checks that the JSON has an answers map. `tests/test_cpu_live.py` skips unless the GGUF and llama.cpp are both present. With both, it runs one real `select` and checks that the pick is a declared option id and that the think text is non-empty. It does not fake model output.

Run the default suite from the repo root.

```bash
python3 -m unittest discover -s tests -v
```

The command needs no GGUF, no API key, and no extra packages.
