# Cost and call budget

No billable provider inference was performed in preparation. Authored mock
token counters are not cost observations. Account plan, balance, paid-usage
settings and SystemOne tariff have not been read or changed.

## Frozen call matrix

| Stage | Haiku/Copilot | Gemini/Copilot | Sol/Codex | Native JEV | Path B/SystemOne | Maximum harness attempts |
|---|---:|---:|---:|---:|---:|---:|
| Smoke | 1 | 1 | 1 | 1 | 1 | 5 |
| Pilot | 33 | 33 | 33 | 27 | 27 | 153 |
| Full | 1,485 | 1,485 | 1,485 | 1,215 | 1,215 | 6,885 |
| All stages, if separately authorised | 1,519 | 1,519 | 1,519 | 1,243 | 1,243 | 7,043 |

One reservation permits at most one **harness adapter invocation**. Path B
uses several trusted local commands, but only its evaluate-live step can make
a SystemOne request. Native and Path B each consume their own request; policy
replay is not another inference. Failed preparation conservatively consumes a
reserved attempt, even if no request was sent.

This is **not** a provider-execution, HTTP-request, token, credit or USD cap.
Opaque CLI retries may race the watchdog; a CLI invocation can involve more
than one HTTP request. Provider-internal retries and some interrupted request
outcomes are unobservable. The strict single-attempt qualification stays blocked.
Operator-side provider/account spending controls remain necessary.

## Reference planning scenario, not a quote

`REFERENCE_RATES.json` records public rate assumptions retrieved on
2026-10-12, with distinct billing units. It is optional. Without `--rates`,
the estimate deliberately reports monetary/credit charges as unknown.

The default estimate assumes **4,000 input and 1,000 output tokens per
invocation**, including an assumed allowance for context. This is not measured
tokenization, actual CLI system-prompt size, provider output, or a prediction
of claims. Histories, question count, hidden reasoning, output length, caching,
long-context tiers, authentication traffic and retries can materially change it.

| Stage | Copilot AI Credits, Haiku + Gemini | USD metered equivalent at $0.01/credit | Separate ChatGPT credits, Sol | SystemOne |
|---|---:|---:|---:|---|
| Smoke | 0.765 | $0.00765 | 0.45 | Unknown, up to 2 planned calls |
| Pilot | 25.245 | $0.25245 | 14.85 | Unknown, up to 54 planned calls |
| Full | 1,136.025 | $11.36025 | 668.25 | Unknown, up to 2,430 planned calls |
| All separately authorised stages | 1,162.035 | $11.62035 | 683.55 | Unknown, up to 2,486 planned calls |

These Copilot figures use default-tier **uncached input/output** rates:
Haiku 5.5 $0.10/$0.50 per million and Gemini 3.8 Flash $0.75/$3.75 per million.
Haiku's separately priced cache writes are not included. No auto-selection
discount is assumed: automatic model selection/substitution is prohibited.
At 16,000 input / 4,000 output tokens, the same simple full-stage scenario is
four times as large: 4,544.1 Copilot AI Credits ($45.441 equivalent) and
2,673 separate ChatGPT credits, **still excluding SystemOne and the other
listed uncertainties**.

An included credit allowance may cover some/all metered usage; the USD
equivalent is not necessarily an additional cash charge. No claim is made that
the operator's remaining monthly allowance covers the study.

## Dry-run estimates

```sh
cd ~/git/mmmtap_phase2
export PYTHONDONTWRITEBYTECODE=1
python -m operator_execution_v1 estimate --stage full --max-calls 6885 \
  --rates operator_execution_v1/REFERENCE_RATES.json
python -m operator_execution_v1 estimate --stage full --max-calls 6885 \
  --input-tokens-per-call 16000 --output-tokens-per-call 4000 \
  --rates operator_execution_v1/REFERENCE_RATES.json
```

Output is JSON on stdout; there is no inference. The report preserves the
complete matrix scenario alongside the selected invocation ceiling. A smaller
ceiling does not imply a representative subset or a linear provider bill.

For account-specific estimates, provide a separate JSON file keyed by adapter.
Each entry has `unit` (`USD`, `Copilot_AI_Credits` or `ChatGPT_credits`),
`input_per_million`, `output_per_million` and an explicit `basis`.
Missing adapter rates stay unknown. No one-credit-per-call or universal
per-request price is assumed.

## Billing arrangements are not interchangeable

- **Copilot Haiku/Gemini:** GitHub AI Credits depend on model and tokens,
  including applicable cache charges. Current public usage-based documentation
  converts 1 credit to $0.01. Included allowances reset monthly; this task did
  not inspect the operator's allowance. Legacy premium-request plans may have
  different terms; old $0.04/request arithmetic is not used here.
- **Sol:** the pinned route is the operator's ChatGPT OAuth subscription,
  not an OpenAI API key and not Copilot. Public GPT-6.1 Sol Standard credit
  rates are 50 input / 2.5 cached input / 250 output credits per million.
  Credit rates do not determine included subscription task counts. Actual
  purchase prices, remaining limits and workspace terms remain unknown.
- **SystemOne:** both mechanisms use JEVKEY and the fixed SystemOne endpoint.
  No authoritative account tariff is available in the frozen configuration.
  Do not call 2,430 planned requests free or convert them into Copilot credits.
  Obtain the operator's provider tariff before committing to full execution.

## Public references

Retrieved by ordinary documentation fetches, not inference or account probes:

1. GitHub, [Models and pricing](https://docs.github.com/en/copilot/reference/copilot-billing/models-and-pricing).
2. GitHub, [Usage-based billing for individuals](https://docs.github.com/en/copilot/concepts/billing-and-usage/individuals/billing).
3. OpenAI, [Codex pricing](https://learn.chatgpt.com/docs/pricing), redirected from the official Codex pricing URL.
4. GitHub, [Supported models](https://docs.github.com/en/copilot/reference/ai-models/supported-models).

Published availability/pricing is not proof that these exact authenticated
routes or models are enabled for this account. Reconfirm billing before the
human authorises each stage; do not modify a frozen model to get a lower bill.
