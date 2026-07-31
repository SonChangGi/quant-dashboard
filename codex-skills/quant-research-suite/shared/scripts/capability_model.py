#!/usr/bin/env python3
"""Resolve opt-in structured Quant Research compatibility capabilities.

The model deliberately separates:

* immutable safety invariants, which live in shared/core;
* project capabilities, which activate only relevant contracts;
* assurance levels, which control verification depth;
* provider/framework adapters, which must never become universal defaults.

Public skills do not call this model on their self-contained default path.
"""

from __future__ import annotations

import re
import shlex
from collections.abc import Iterable, Mapping
from typing import Any
from urllib.parse import parse_qsl, urlsplit


PROJECT_CAPABILITIES = frozenset(
    {
        "repo-mutation",
        "web-ui",
        "interactive-chart",
        "analysis",
        "analysis-input-binding",
        "external-data",
        "backend",
        "scheduled-automation",
        "publication",
        "public-web",
        "remote-release",
    }
)

RUNTIME_CAPABILITIES = frozenset(
    {"multi-agent-write", "agent-team-execution"}
)
CAPABILITIES = PROJECT_CAPABILITIES | RUNTIME_CAPABILITIES

MUTUALLY_EXCLUSIVE_CAPABILITY_GROUPS: dict[str, frozenset[str]] = {
    "runtime-execution-mode": RUNTIME_CAPABILITIES,
}

ASSURANCE_LEVELS = ("light", "standard", "strict", "release")
ASSURANCE_RANK = {name: index for index, name in enumerate(ASSURANCE_LEVELS)}
DELIVERY_LEVELS = ("local", "release")

CAPABILITY_IMPLICATIONS: dict[str, frozenset[str]] = {
    "interactive-chart": frozenset({"web-ui"}),
    "analysis-input-binding": frozenset({"analysis"}),
}

PROFILE_CAPABILITIES: dict[str, frozenset[str]] = {
    "quant-research-web": frozenset({"web-ui"}),
    "quant-public-dashboard-strict": frozenset(),
}

PROFILE_ASSURANCE = {
    "quant-research-web": "standard",
    "quant-public-dashboard-strict": "strict",
}

ASSURANCE_GATES: dict[str, frozenset[str]] = {
    "light": frozenset({"contract", "cost"}),
    "standard": frozenset({"contract", "cost", "verification"}),
    "strict": frozenset(
        {"contract", "cost", "verification", "independent_reaudit"}
    ),
    "release": frozenset(
        {
            "contract",
            "cost",
            "verification",
            "independent_reaudit",
            "release",
        }
    ),
}

CAPABILITY_GATES: dict[str, frozenset[str]] = {
    "repo-mutation": frozenset({"tests"}),
    "web-ui": frozenset({"product"}),
    "interactive-chart": frozenset({"chart_interaction"}),
    "analysis": frozenset({"analysis_result", "tests"}),
    "analysis-input-binding": frozenset({"input_binding"}),
    "external-data": frozenset({"collection", "freshness"}),
    "backend": frozenset({"integration", "security"}),
    "scheduled-automation": frozenset({"schedule", "cost"}),
    "publication": frozenset({"publication"}),
    "public-web": frozenset({"public_readback"}),
    "remote-release": frozenset({"release", "cost"}),
    "multi-agent-write": frozenset({"handoff_review"}),
    # The typed integration receipt validates every worker delivery, cleanup
    # result, artifact, and joined snapshot. Requiring the legacy
    # handoff_review lane as well would duplicate the same proof under two
    # gates.
    "agent-team-execution": frozenset({"team_integration"}),
}

CAPABILITY_ASSURANCE_FLOOR: dict[str, str] = {
    "repo-mutation": "light",
    "web-ui": "standard",
    "interactive-chart": "standard",
    "analysis": "standard",
    "analysis-input-binding": "strict",
    "external-data": "standard",
    "backend": "standard",
    "scheduled-automation": "standard",
    "publication": "standard",
    "public-web": "standard",
}

CORE_REFERENCES = (
    "core/invariants.md",
    "core/authority.md",
    "core/evidence-semantics.md",
    "core/context-routing.md",
)

CAPABILITY_REFERENCES: dict[str, tuple[str, ...]] = {
    "repo-mutation": ("capabilities/repo-mutation.md",),
    "web-ui": ("capabilities/web-ui.md",),
    "interactive-chart": ("capabilities/interactive-chart.md",),
    "analysis": ("capabilities/analysis.md",),
    "analysis-input-binding": ("capabilities/analysis-input-binding.md",),
    "external-data": ("capabilities/external-data.md",),
    "backend": ("capabilities/backend.md",),
    "scheduled-automation": ("capabilities/scheduled-automation.md",),
    "publication": ("capabilities/publication.md",),
    "public-web": ("capabilities/public-web.md",),
    "remote-release": ("capabilities/remote-release.md",),
    "multi-agent-write": ("capabilities/multi-agent-write.md",),
    "agent-team-execution": (
        "capabilities/agent-team-execution.md",
        "references/agent-orchestration.md",
    ),
}

PROFILE_REFERENCES: dict[str, tuple[str, ...]] = {
    "quant-research-web": (
        "profiles/quant-research-web.md",
        "references/web-design-source.md",
    ),
    "quant-public-dashboard-strict": (
        "profiles/quant-public-dashboard-strict.md",
        "references/operating-principles.md",
        "references/data-automation.md",
        "references/cost-and-authority.md",
        "references/developer-runbook.md",
    ),
}

ADAPTER_REFERENCES: dict[str, str] = {
    "github": "adapters/github.md",
    "github-actions": "adapters/github-actions.md",
    "github-pages": "adapters/github-pages.md",
    "vercel": "adapters/vercel.md",
    "fastapi": "adapters/fastapi.md",
    "supabase": "adapters/supabase.md",
}

PORTABLE_ID = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")

ZERO_SPEND_POLICY = (
    "zero-spend-unless-user-first-requests-specific-paid-action"
)

# These are aliases observed across provider APIs and earlier suite schemas.
# Keeping them in one module prevents a receipt from setting one spelling to
# false while enabling the same paid transition under another spelling.
PAID_TRANSITION_FIELDS = frozenset(
    {
        "auto_renewing_trial_active",
        "auto_renewing_trial_enabled",
        "payment_method_registration_required",
        "payment_method_change_required",
        "automatic_upgrade_possible",
        "automatic_upgrade_enabled",
        "plan_upgrade_required",
        "plan_upgrade_enabled",
        "overage_possible",
        "overage_enabled",
        "pay_as_you_go_enabled",
        "payg_enabled",
        "free_quota_exceedance_allowed",
        "free_quota_exceedance_possible",
        "paid_add_on_active",
        "paid_add_on_enabled",
        "paid_addon_active",
        "paid_addon_enabled",
        "spend_cap_disabled",
        "spend_cap_disablement_enabled",
        "paid_fallback_enabled",
        "paid_data_enabled",
        "paid_data_source_enabled",
        "paid_dataset_enabled",
        "billing_enabled",
        "charges_enabled",
        "allow_charges",
    }
)

# A secret-bearing key ends in the credential concept. Metadata such as
# token_count, token_budget, cookie_policy, or secret_description is not a
# credential value and must remain usable in generic projects.
SECRET_VALUE_KEY = re.compile(
    r"(?:^|_)(?:password|passwd|secret|secret_key|token|api_key|private_key|"
    r"service_role(?:_key)?|access_key|credential|bearer|cookie|"
    r"connection_string|dsn)(?:_(?:value|literal|material|pem))?$",
    re.IGNORECASE,
)
PAID_ACTION_TEXT_KEYS = frozenset(
    {
        "action",
        "command",
        "command_argv",
        "operation",
        "requested_action",
    }
)
SECRET_LITERAL_PATTERNS = (
    re.compile(
        r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|"
        r"github_pat_[A-Za-z0-9_]{20,})\b"
    ),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)
INLINE_CREDENTIAL = re.compile(
    r"""(?ix)
    (?:
      authorization\s*:\s*(?:bearer|basic)
      |(?:bearer|basic)\s+
      |--?(?:api[-_]?key|auth[-_]?token|access[-_]?key|secret[-_]?key|
         service[-_]?role(?:[-_]?key)?|private[-_]?key|
         connection[-_]?string|token|password|secret|credential|dsn)
         (?:\s+|=)
      |(?:api[-_]?key|auth[-_]?token|access[-_]?key|secret[-_]?key|
         service[-_]?role|
         connection[-_]?string|private[-_]?key|password|passwd|secret|
         token|credential|dsn)\s*(?:=|:)
    )
    \s*["']?([^\s"'`;]{8,})
    """
)
SENSITIVE_QUERY_KEY = re.compile(
    r"^(?:api_?key|access_?(?:key|token)|auth_?token|token|password|passwd|"
    r"secret|service_?role|private_?key|connection_?string|dsn)$",
    re.IGNORECASE,
)
SECRET_COMMAND_OPTIONS = frozenset(
    {
        "access_key",
        "api_key",
        "auth_token",
        "connection_string",
        "credential",
        "dsn",
        "password",
        "passwd",
        "private_key",
        "secret",
        "secret_key",
        "service_role",
        "service_role_key",
        "token",
    }
)
PAID_APPROVAL_CONCEPT_TEXT = re.compile(
    r"(?i)(?:\b(?:paid|billing|charge|overage|payg|payment[\s_-]*method|"
    r"plan[\s_-]*upgrade|auto[\s_-]*renew)\b|"
    r"유료|결제|과금|초과\s*요금|자동\s*갱신|플랜\s*업그레이드)"
)
POSITIVE_APPROVAL_TEXT = re.compile(
    r"(?i)(?:\b(?:approved|authorized|consented)\b|"
    r"\bapproval\s*(?::|=|\bis\b)\s*(?:granted|approved|true|yes)\b|"
    r"(?:승인|허용|동의)(?:됨|함|했다|완료|되었|했음))"
)
NEGATED_OR_PENDING_APPROVAL_TEXT = re.compile(
    r"(?i)(?:\bnot(?:\s+yet)?\s+(?:approved|authorized)\b|"
    r"\bapproval\s+(?:required|needed|pending)\b|"
    r"미승인|(?:승인|허용|동의)\s*(?:필요|대기|전|없음))"
)
URL_CANDIDATE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
SAFE_SECRET_PLACEHOLDER = re.compile(
    r"(?:"
    r"\$\{?[A-Z_][A-Z0-9_]*\}?"
    r"|<[^<>]{1,80}>"
    r"|\*{3,}"
    r"|redacted"
    r"|server[-_ ]only"
    r"|not[-_ ]configured"
    r"|none"
    r")",
    re.IGNORECASE,
)

SAFE_DISABLED_STATES = frozenset(
    {
        "blocked",
        "denied",
        "disabled",
        "forbidden",
        "not_allowed",
        "off",
        "prohibited",
        "rejected",
    }
)
UNSAFE_ENABLED_STATES = frozenset(
    {
        "active",
        "allow",
        "allowed",
        "enable",
        "enabled",
        "on",
        "required",
        "true",
    }
)
PAID_ACTIVATION_PREFIXES = (
    "activate_",
    "allow_",
    "enable_",
    "use_",
)
PAID_STATE_SUFFIXES = (
    "_activate",
    "_active",
    "_allow",
    "_allowed",
    "_enable",
    "_enabled",
    "_possible",
    "_required",
)
PAID_KEY_CONCEPTS = frozenset(
    {
        "automatic_upgrade",
        "billing",
        "charges",
        "free_quota_exceedance",
        "overage",
        "paid_add_on",
        "paid_addon",
        "paid_data",
        "paid_data_source",
        "paid_dataset",
        "paid_fallback",
        "pay_as_you_go",
        "payg",
        "payment_method",
        "plan_upgrade",
    }
)
DIRECT_PAID_STATE_KEYS = frozenset(
    {
        "paid_add_on",
        "paid_addon",
        "paid_data",
        "paid_data_source",
        "paid_dataset",
        "paid_fallback",
        "pay_as_you_go",
        "payg",
    }
)
COMMAND_ACTIVATION_WORDS = frozenset(
    {
        "activate",
        "active",
        "allow",
        "allowed",
        "enable",
        "enabled",
        "use",
    }
)
COMMAND_DISABLE_WORDS = frozenset(
    {"disable", "disabled", "off", "remove", "removed"}
)
COMMAND_TOKEN_ALIASES = {
    "auto renew": ("auto", "renew"),
    "auto-renew": ("auto", "renew"),
    "auto_renew": ("auto", "renew"),
    "pay as you go": ("pay", "as", "you", "go"),
    "pay-as-you-go": ("pay", "as", "you", "go"),
    "pay_as_you_go": ("pay", "as", "you", "go"),
    "paid add on": ("paid", "add", "on"),
    "paid-add-on": ("paid", "add", "on"),
    "paid_add_on": ("paid", "add", "on"),
    "spend cap": ("spend", "cap"),
    "spend-cap": ("spend", "cap"),
    "spend_cap": ("spend", "cap"),
}
COMMAND_CONCEPT_SEQUENCES = frozenset(
    {
        ("auto", "renew"),
        ("automatic", "upgrade"),
        ("billing",),
        ("charges",),
        ("free", "quota", "exceedance"),
        ("overage",),
        ("paid", "add", "on"),
        ("paid", "data"),
        ("paid", "data", "source"),
        ("paid", "dataset"),
        ("paid", "fallback"),
        ("pay", "as", "you", "go"),
        ("payg",),
        ("payment", "method"),
        ("plan",),
        ("quota", "overage"),
        ("spend", "cap"),
        ("subscription",),
        ("tier",),
    }
)
COMMAND_STATE_WORDS = frozenset(
    {
        "1",
        "active",
        "allowed",
        "auto",
        "default",
        "disabled",
        "enabled",
        "false",
        "none",
        "off",
        "on",
        "removed",
        "true",
        "unbounded",
        "unlimited",
        "yes",
    }
)
COMMAND_ENABLED_WORDS = frozenset(
    {"1", "active", "allowed", "enabled", "on", "true", "yes"}
)
SHELL_EXECUTABLES = frozenset(
    {
        "bash",
        "cmd",
        "cmd.exe",
        "dash",
        "ksh",
        "powershell",
        "powershell.exe",
        "pwsh",
        "pwsh.exe",
        "sh",
        "zsh",
    }
)
SHELL_COMMAND_FLAGS = frozenset(
    {"-c", "-command", "-ic", "-ilc", "-lc", "/c"}
)
INERT_OUTPUT_EXECUTABLES = frozenset(
    {
        "cat",
        "cp",
        "diff",
        "echo",
        "file",
        "git",
        "grep",
        "head",
        "logger",
        "ls",
        "mv",
        "printf",
        "rg",
        "sort",
        "stat",
        "tail",
        "touch",
        "wc",
    }
)
SIMPLE_COMMAND_WRAPPERS = frozenset(
    {"command", "exec", "nohup"}
)
COMMAND_WRAPPER_OPTIONS_WITH_VALUE = {
    "nice": frozenset({"--adjustment", "-n"}),
    "time": frozenset({"--format", "--output", "-f", "-o"}),
}
SUDO_OPTIONS_WITH_VALUE = frozenset(
    {
        "--chdir",
        "--group",
        "--host",
        "--prompt",
        "--role",
        "--type",
        "--user",
        "-c",
        "-d",
        "-g",
        "-h",
        "-p",
        "-r",
        "-t",
        "-u",
    }
)
ENV_OPTIONS_WITH_VALUE = frozenset(
    {"--chdir", "--split-string", "--unset", "-c", "-s", "-u"}
)
CODE_INTERPRETER_FLAGS = {
    "node": frozenset({"-e", "--eval", "-p", "--print"}),
    "perl": frozenset({"-e"}),
    "python": frozenset({"-c"}),
    "python3": frozenset({"-c"}),
    "ruby": frozenset({"-e"}),
}
CODE_COMMAND_EXECUTION = re.compile(
    r"\b(?:call|check_call|check_output|create_subprocess_exec|"
    r"exec(?:file|filesync|sync|v|ve)?|popen|posix_spawn|run|"
    r"spawn(?:sync)?|system)\s*\(",
    re.IGNORECASE,
)
QUOTED_CODE_LITERAL = re.compile(
    r"""(?s)(?P<quote>["'])(?P<value>.*?)(?P=quote)"""
)
STRONG_BARE_PAID_OPTIONS = frozenset(
    {
        ("auto", "renew"),
        ("paid", "add", "on"),
        ("paid", "data"),
        ("paid", "data", "source"),
        ("paid", "dataset"),
        ("paid", "fallback"),
        ("pay", "as", "you", "go"),
        ("payg",),
    }
)
FALSE_OPTION_STATES = frozenset(
    {"0", "disabled", "false", "no", "off"}
)
SHELL_CONTROL = re.compile(r"(?:;|&&|\|\||(?<!\|)\|(?!\|)|[\r\n]|`|\$\()")


def _empty_or_zero(value: Any) -> bool:
    return value is None or value is False or value == "" or value == 0 or value == []


def normalize_policy_key(value: str) -> str:
    """Normalize camelCase, kebab-case, and punctuation to snake_case."""

    acronym_boundaries = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", value)
    with_boundaries = re.sub(
        r"([a-z0-9])([A-Z])", r"\1_\2", acronym_boundaries
    )
    return re.sub(r"[^A-Za-z0-9]+", "_", with_boundaries).strip("_").lower()


def safe_secret_placeholder(value: Any) -> bool:
    return isinstance(value, str) and bool(
        SAFE_SECRET_PLACEHOLDER.fullmatch(value.strip())
    )


def literal_secret_reasons(value: str) -> list[str]:
    reasons: list[str] = []
    if any(pattern.search(value) for pattern in SECRET_LITERAL_PATTERNS):
        reasons.append("contains a credential-like literal")
    match = INLINE_CREDENTIAL.search(value)
    if match and not safe_secret_placeholder(match.group(1)):
        reasons.append("contains an inline credential")
    for candidate in URL_CANDIDATE.findall(value):
        try:
            parsed = urlsplit(candidate)
        except ValueError:
            continue
        if parsed.username is not None or parsed.password is not None:
            reasons.append("contains URL user information")
        try:
            query = parse_qsl(parsed.query, keep_blank_values=True)
        except ValueError:
            query = []
        if any(
            SENSITIVE_QUERY_KEY.fullmatch(normalize_policy_key(key))
            and bool(query_value)
            for key, query_value in query
        ):
            reasons.append("contains a credential-bearing URL query")
    return list(dict.fromkeys(reasons))


def command_argv_secret_reasons(argv: Iterable[str]) -> list[str]:
    """Detect explicit secret option values, including short literals."""

    tokens = [str(token) for token in argv]
    reasons: list[str] = []
    for index, token in enumerate(tokens):
        option, separator, inline_value = token.partition("=")
        normalized_option = normalize_policy_key(option.lstrip("-/"))
        if normalized_option not in SECRET_COMMAND_OPTIONS:
            continue
        candidate = inline_value if separator else (
            tokens[index + 1] if index + 1 < len(tokens) else ""
        )
        if candidate and not safe_secret_placeholder(candidate):
            reasons.append("contains an explicit credential option value")
    return list(dict.fromkeys(reasons))


def paid_approval_text_reasons(value: str) -> list[str]:
    """Detect positive paid-authority assertions in stored evidence prose."""

    for line in value.splitlines():
        normalized_line = re.sub(r"[_-]+", " ", line)
        if (
            PAID_APPROVAL_CONCEPT_TEXT.search(normalized_line)
            and POSITIVE_APPROVAL_TEXT.search(normalized_line)
            and not NEGATED_OR_PENDING_APPROVAL_TEXT.search(normalized_line)
        ):
            return ["must not store paid-action approval material"]
    return []


def prohibited_paid_data_reasons(
    value: str,
    *,
    allow_reported_violation: bool = False,
) -> list[str]:
    """Reject actionable paid-data prose while preserving explicit refusals.

    This guard is for instruction and proof prose, not arbitrary research
    discussion.  It deliberately recognizes free-to-paid transitions and
    subscription-shaped price/data acquisition without hard-coding providers.
    Clauses that explicitly refuse the same action remain valid. Typed blocker
    and finding fields may opt in to reporting a detected violation; that
    exception never applies to instructions, next actions, or passing proof.
    """

    data_context = re.compile(
        r"(?i)(?:\b(?:data|datasets?|feeds?|providers?|sources?|apis?|"
        r"pricing|prices?|quotes?|terminals?|services?|fundamentals?)\b|"
        r"(?:data|datasets?|feeds?|providers?|sources?|apis?|pricing|"
        r"prices?|quotes?|terminals?|services?|fundamentals?)"
        r"(?:를|을|이|가|은|는|에|에게|에서|로|으로|와|과|의|부터|"
        r"만|도|랑)|"
        r"\bcorporate[\s_-]*actions?\b|데이터|자료|소스|제공자|가격|"
        r"시세|기업\s*행위|펀더멘털)"
    )
    paid_concept = re.compile(
        r"(?i)(?:\b(?:paid|premium|chargeable|billable|billing|payment|"
        r"(?:credit[\s_-]*)?card|"
        r"subscription|payg|pay[\s_-]*as[\s_-]*you[\s_-]*go|overage|"
        r"paid[\s_-]*tier|trial|freemium|charge(?:d|s|ing)?|fees?|"
        r"provider[\s_-]*plan|"
        r"(?:buy|purchase|top[\s_-]*up|paid|expiring|promotional|"
        r"temporary|time[\s_-]*limited|trial)[\s_-]*credits?|"
        r"(?:buy|purchase).{0,20}\b(?:data[\s_-]*)?add[\s_-]*ons?)\b|"
        r"(?:[$€£]\s*\d|(?:usd|eur|gbp|krw)\s*\d|"
        r"\d+(?:\.\d+)?\s*(?:/|per\s+)(?:month|year|call|request))|"
        r"유료|프리미엄|결제|과금|청구|요금|카드|구독|체험|크레딧|"
        r"월정액|월\s*\d|(?:\d+\s*만?\s*원(?:짜리)?)|초과\s*요금)"
    )
    # These are analytical subjects, not purchase terms. Masking them before
    # paid-access classification prevents ordinary research language such as
    # "equity risk premium data" from being treated as a premium data product.
    legitimate_domain_term = re.compile(
        r"(?i)(?:\b(?:(?:equity[\s_-]+)?risk[\s_-]+premium|"
        r"(?:term|liquidity|credit|size|value|option)[\s_-]+premium|"
        r"dividend[\s_-]+payments?|"
        r"credit[\s_-]*card[\s_-]+transactions?|"
        r"clinical[\s_-]+trials?|"
        r"(?:mutual[\s_-]+)?fund[\s_-]+(?:expense[\s_-]+)?fees?|"
        r"subscription[\s_-]+rights?)\b|결제\s*거래)"
    )
    data_target_text = (
        r"(?:(?:an?|the)\s+)?(?:access\s+to\s+)?"
        r"(?:(?:historical|market|pricing|price|quote|real[\s_-]*time|"
        r"point[\s_-]*in[\s_-]*time|fundamentals?)\s+){0,3}"
        r"(?:data(?:sets?)?|feeds?|apis?|providers?|sources?|prices?|"
        r"quotes?|fundamentals?|corporate[\s_-]*actions?|terminals?|"
        r"services?)"
    )
    intrinsic_paid_acquisition = re.compile(
        rf"(?i)(?:"
        rf"\b(?:buy|buys|bought|buying|purchas(?:e|es|ed|ing)|"
        rf"rent(?:s|ed|ing)?|licens(?:e|es|ed|ing))\s+"
        rf"{data_target_text}\b|"
        rf"\b(?:pay|pays|paid|paying)\s+"
        rf"(?:for|to\s+(?:access|use))\s+{data_target_text}\b|"
        rf"\bsubscrib(?:e|es|ed|ing)\s+to\s+{data_target_text}\b|"
        rf"\bacquir(?:e|es|ed|ing)\s+{data_target_text}"
        rf".{{0,24}}\b(?:for\s+money|for\s+(?:a\s+)?fee|"
        rf"at\s+(?:a\s+)?cost)\b|"
        rf"\b{data_target_text}.{{0,32}}\b(?:costs?\s+money|"
        rf"requires?\s+payment|has\s+(?:a\s+)?fee|"
        rf"(?:with|has)\s+(?:a\s+)?nonzero\s+cost)\b|"
        r"(?:데이터|자료|가격\s*API|시세(?:\s*데이터)?|"
        r"기업\s*행위|펀더멘털).{0,32}(?:"
        r"구매(?:한다|했다|할|한다면)|"
        r"사용권.{0,8}(?:산다|사다|구매)|"
        r"이용료.{0,8}(?:낸다|납부)|"
        r"비용.{0,8}지불|라이선스.{0,8}(?:구매|구입))"
        r")"
    )
    action = re.compile(
        r"(?i)(?:\b(?:use[sd]?|using|buy|bought|purchase[sd]?|purchasing|"
        r"subscribe[sd]?|subscribing|register(?:ed|ing)?|enable[sd]?|"
        r"enabling|activate[sd]?|activating|upgrade[sd]?|upgrading|"
        r"start(?:s|ed|ing)?|allow(?:ed|ing)?|request(?:ed|ing)?|"
        r"integrate[sd]?|integrating|connect(?:ed|ing)?|adopt(?:ed|ing)?|"
        r"acquire[sd]?|acquiring|obtain(?:ed|ing)?|pay|paying|"
        r"download(?:s|ed|ing)?|fetch(?:es|ed|ing)?|ingest(?:s|ed|ing)?|"
        r"import(?:s|ed|ing)?|retrieve[sd]?|retrieving|load(?:s|ed|ing)?|"
        r"license[sd]?|licensing|leverage[sd]?|leveraging|"
        r"access(?:es|ed|ing)?|quer(?:y|ies|ied|ying)|"
        r"call(?:s|ed|ing)?|pull(?:s|ed|ing)?|"
        r"scrap(?:e|es|ed|ing)|stream(?:s|ed|ing)?|"
        r"read(?:s|ing)?|consume(?:s|d|ing)?|"
        r"rely(?:ing|ies|ied)?|rent(?:s|ed|ing)?|"
        r"continue[sd]?|continuing|registration|require[sd]?|requiring)\b|"
        r"사용|활용|이용|도입|구매|결제|등록|활성화|수집|다운로드|"
        r"조회|가져오|업그레이드|신청|연동|통합|구독|필요|접속|"
        r"호출|읽|스트리밍|의존|납부|지불)"
    )
    future_paid = re.compile(
        r"(?i)(?:\b(?:become[sd]?|turns?|convert(?:s|ed)?|switch(?:es|ed)?"
        r"|chargeable|billable|charge(?:d|s|ing)?|pay|paid|premium)\b"
        r".{0,32}\b(?:later|after|"
        r"eventually|continue|expiry|expires?|tomorrow|subsequently|next)\b|"
        r"\b(?:become[sd]?|turns?|convert(?:s|ed)?|switch(?:es|ed)?)\b"
        r".{0,24}\b(?:paid|premium|charged|chargeable|billable)\b|"
        r"\b(?:later|after|eventually)\b.{0,32}\b(?:pay|paid|charge|"
        r"billing|premium|fees?)\b|"
        r"\bfree\b.{0,48}\b(?:then|later|after|until|today|now)\b.{0,40}"
        r"\b(?:pay|paid|charge(?:d|s|ing)?|billing|premium|fees?|"
        r"(?:buy|purchase)[\s_-]*credits?)\b|"
        r"\bfree\b.{0,48}\b(?:become[sd]?|turns?|convert(?:s|ed)?|"
        r"switch(?:es|ed)?)\b.{0,24}\b(?:paid|premium|charged|"
        r"chargeable|billable)\b|"
        r"\b(?:freemium|free[\s_-]*to[\s_-]*paid)\b|"
        r"\bfree\b.{0,48}\buntil\b.{0,24}\b(?:fees?|charges?|"
        r"billing|payment)\b|"
        r"추후.{0,24}(?:유료|결제|과금)|무료.{0,32}(?:후|뒤|까지).{0,24}"
        r"(?:유료|결제|과금|청구|요금))"
    )
    explicit_refusal = re.compile(
        r"(?i)(?:\b(?:do\s+not|don't|never|must\s+not|should\s+not|"
        r"cannot|can't|will\s+not|did\s+not|does\s+not|forbid|"
        r"forbids|forbade|forbidden|forbidding|"
        r"prohibit(?:s|ed|ing)?|reject(?:s|ed|ing)?|"
        r"stop(?:s|ped|ping)?|avoid(?:s|ed|ing)?|"
        r"exclude(?:s|d|ing)?|disallow(?:s|ed|ing)?|"
        r"refuse(?:s|d|ing)?)\b"
        r".{0,48}\b(?:paid|premium|chargeable|billable|charges?|fees?|"
        r"trial|freemium|subscriptions?|overage)\b|"
        r"\b(?:paid|premium|chargeable|billable|subscriptions?)\b"
        r".{0,48}\b(?:(?:must\s+not|should\s+not|cannot\s+be|can't\s+be|"
        r"may\s+not|will\s+not|won't|is\s+not|are\s+not|was\s+not|"
        r"were\s+not)\b.{0,16}\b"
        r"(?:used|accessed|purchased|selected|subscribed|acquired|"
        r"obtained|downloaded|licensed|allowed|needed|an?\s+option)|"
        r"not\s+allowed|"
        r"not\s+used|forbidden|prohibited|disallowed|"
        r"(?:(?:is|are|was|were|has\s+been|have\s+been)\s+"
        r"(?:disabled|removed))|"
        r"ineligible|off\s+limits|out\s+of\s+scope|"
        r"outside(?:\s+the)?\s+solution\s+space|excluded|rejected)\b|"
        r"\bno\s+(?:paid|billable)\b.{0,32}\b(?:route|source|api|feed)"
        r".{0,24}\b(?:active|enabled|remains?)\b|"
        r"\bno\s+paid\b|\bwithout\b.{0,20}\b(?:paid|premium|billing|"
        r"payment|subscription|card)\b|"
        r"유료.{0,32}(?:금지|사용하지|활용하지|이용하지|구매하지|"
        r"결제하지|구독하지|불가|불필요|허용하지|제외|않|"
        r"안\s*(?:쓰|써|쓴)|"
        r"필요\s*없|피하|거부|대상이\s*아니)|"
        r"(?:금지|사용하지|활용하지|이용하지|구매하지|결제하지|"
        r"구독하지|불가|허용하지|제외|피하|거부).{0,32}유료|"
        r"(?:결제|과금|청구).{0,24}(?:하지|없|금지|불가)|없이)"
    )
    explicit_acquisition_refusal = re.compile(
        rf"(?i)(?:\b(?:do\s+not|don't|never|must\s+not|"
        rf"should\s+not|cannot|can't|will\s+not|won't)\s+"
        rf"(?:use|access|buy|purchase|pay\s+for|rent|license|"
        rf"subscribe\s+to|acquire)\s+{data_target_text}\b|"
        rf"\b{data_target_text}.{{0,32}}\b(?:must\s+not|"
        rf"should\s+not|cannot|can't|may\s+not)\s+be\s+"
        rf"(?:bought|purchased|rented|licensed|paid\s+for)\b|"
        r"(?:데이터|자료|가격\s*API|시세(?:\s*데이터)?|기업\s*행위|"
        r"펀더멘털).{0,32}(?:구매|구입|결제|지불|납부|구독)"
        r".{0,16}(?:하지|지\s*않|금지|불가))"
    )
    explicit_remediation = re.compile(
        rf"(?i)(?:\b(?:replace|remove|disable|drop|decommission|"
        rf"disconnect|stop\s+using)\s+(?:(?:an?|the)\s+)?"
        rf"(?:paid|premium|billable|chargeable)\s+{data_target_text}\b|"
        r"(?:유료|프리미엄).{0,24}(?:데이터|자료|가격\s*API|시세|"
        r"기업\s*행위|펀더멘털|소스|피드).{0,24}"
        r"(?:제거|중단|교체|해지|비활성화))"
    )
    reported_violation = re.compile(
        r"(?i)(?:\b(?:detected|discovered|found|currently\s+configured|"
        r"implementation\s+(?:uses?|accesses?)|"
        r"(?:was|were|has\s+been|had\s+been)\s+"
        r"(?:used|accessed|configured|selected|subscribed|licensed))\b|"
        r"(?:발견|감지|사용된|접근한|설정된))"
    )
    subscription_action = re.compile(
        r"(?i)\b(?:subscribe[sd]?|subscribing|subscription)\b"
    )
    safe_free_phrase = re.compile(
        r"(?i)\b(?:free[\s_-]*only|no[\s_-]*cost|zero[\s_-]*cost|"
        r"free\s+forever|permanently\s+free|"
        r"no[\s_-]*(?:payment(?:[\s_-]*(?:method|card))?|"
        r"(?:credit[\s_-]*)?card|billing|overage|fees?|charges?|"
        r"subscriptions?|trial|paid[\s_-]*tier|paid[\s_-]*add[\s_-]*on)"
        r"(?:\s+(?:or|and)\s+(?:payment(?:\s+(?:method|card))?|"
        r"credit\s+card|card|billing|overage|fees?|charges?|"
        r"subscriptions?|trial|paid\s+tier|paid\s+add-on))*)"
        r"\b|완전\s*무료"
    )
    hard_paid_prerequisite = re.compile(
        r"(?i)\b(?:registration|register(?:ed|ing)?|require[sd]?|"
        r"requiring|need(?:s|ed|ing)?)\b.{0,32}\b(?:payment|billing|"
        r"subscription|(?:credit[\s_-]*)?card)\b"
    )
    safe_prerequisite_refusal = re.compile(
        r"(?i)\b(?:registration|register(?:ed|ing)?|require[sd]?|"
        r"requiring|need(?:s|ed|ing)?)\b.{0,16}\b(?:no|without)\b"
        r".{0,16}\b(?:payment|billing|subscription|"
        r"(?:credit[\s_-]*)?card)\b"
    )
    # A contrast starts a new semantic clause so "do not use X, but subscribe
    # to Y" cannot borrow the refusal from the first clause.
    raw_clauses = re.split(
        r"(?i)(?:[\n.;—–]+|,\s*(?:but|however|instead|then|and\s+then|"
        r"yet|while|except)\b|"
        r"\b(?:but|however|instead|and\s+then)\b|"
        r"\b(?:and|while|except|yet)\b(?=\s+(?:(?:will|then)\s+)?"
        r"(?:use(?:s|d|ing)?|access(?:es|ed|ing)?|buy(?:s|ing)?|bought|"
        r"purchas(?:e|es|ed|ing)|"
        r"subscribe|register|enable|activate|upgrade|download|fetch|"
        r"ingest|import|retrieve|load|license|leverage|connect|adopt|"
        r"acquire|obtain|pay|rent|query|call|pull|scrape|stream|read|"
        r"consume|rely)\b)|"
        r"하지만|그러나|대신|말고[,\s]*|"
        r"그리고(?=\s*(?:사용|활용|이용|도입|구매|결제|등록|활성화|"
        r"수집|다운로드|조회|가져오|구독)))",
        value,
    )
    clauses: list[str] = []
    for index, raw_clause in enumerate(raw_clauses):
        clause = raw_clause.strip()
        if not clause:
            continue
        clauses.append(clause)
        if (
            not data_context.search(clause)
            and index > 0
            and raw_clauses[index - 1].strip()
            and data_context.search(raw_clauses[index - 1])
        ):
            # Preserve a nearby data subject across punctuation, e.g.
            # "Use a free API now; pay later to continue."
            previous = raw_clauses[index - 1].strip()
            if (
                explicit_refusal.search(previous)
                and action.search(clause) is None
            ):
                clauses.append(previous + " " + clause)
            else:
                clauses.append("data source " + clause)
    reasons: list[str] = []
    for clause in clauses:
        if not clause or not data_context.search(clause):
            continue
        semantic_clause = legitimate_domain_term.sub(
            "research_metric",
            clause,
        )
        has_future_transition = (
            future_paid.search(semantic_clause) is not None
        )
        risky_subscription = (
            subscription_action.search(semantic_clause) is not None
            and safe_free_phrase.search(semantic_clause) is None
        )
        has_intrinsic_paid_acquisition = (
            intrinsic_paid_acquisition.search(semantic_clause) is not None
        )
        risky = (
            paid_concept.search(semantic_clause) is not None
            or has_future_transition
            or risky_subscription
            or has_intrinsic_paid_acquisition
        )
        explicitly_refused = (
            explicit_refusal.search(semantic_clause) is not None
            or explicit_acquisition_refusal.search(semantic_clause)
            is not None
            or explicit_remediation.search(semantic_clause) is not None
        )
        explicitly_free = (
            safe_free_phrase.search(semantic_clause) is not None
        )
        paid_concept_outside_safe_phrase = paid_concept.search(
            safe_free_phrase.sub("", semantic_clause)
        ) is not None
        has_hard_paid_prerequisite = (
            hard_paid_prerequisite.search(semantic_clause) is not None
            and safe_prerequisite_refusal.search(semantic_clause) is None
        )
        is_reported_violation = (
            allow_reported_violation
            and reported_violation.search(semantic_clause) is not None
        )
        if (
            risky
            and not explicitly_refused
            and not is_reported_violation
            and (
                not explicitly_free
                or has_future_transition
                or has_hard_paid_prerequisite
                or has_intrinsic_paid_acquisition
                or paid_concept_outside_safe_phrase
            )
        ):
            reasons.append(
                "paid data acquisition is outside this workflow's solution "
                "space"
            )
    return list(dict.fromkeys(reasons))


def _disabled_state(value: Any) -> bool:
    if value is False:
        return True
    if not isinstance(value, str):
        return False
    return normalize_policy_key(value) in SAFE_DISABLED_STATES


def structured_paid_transition_reason(
    normalized_key: str, value: Any
) -> str | None:
    """Classify authority-shaped paid aliases without scanning ordinary prose."""

    if normalized_key in PAID_TRANSITION_FIELDS:
        if value is not False:
            return "must be false"
        return None

    for prefix in PAID_ACTIVATION_PREFIXES:
        if normalized_key.startswith(prefix):
            concept = normalized_key[len(prefix) :]
            if concept in PAID_KEY_CONCEPTS and not _disabled_state(value):
                return "must be false or explicitly disabled"

    for suffix in PAID_STATE_SUFFIXES:
        if normalized_key.endswith(suffix):
            concept = normalized_key[: -len(suffix)]
            if concept in PAID_KEY_CONCEPTS and not _disabled_state(value):
                return "must be false or explicitly disabled"

    if normalized_key in DIRECT_PAID_STATE_KEYS:
        if value is True:
            return "must not enable a paid state"
        if (
            isinstance(value, str)
            and normalize_policy_key(value) in UNSAFE_ENABLED_STATES
        ):
            return "must not enable a paid state"
        if isinstance(value, Mapping):
            for raw_state, state_value in value.items():
                state = normalize_policy_key(str(raw_state))
                if state in {
                    "activate",
                    "active",
                    "allow",
                    "allowed",
                    "enable",
                    "enabled",
                } and not _disabled_state(state_value):
                    return "must not contain an enabled paid configuration"
                if (
                    state in {"mode", "state", "status"}
                    and isinstance(state_value, str)
                    and normalize_policy_key(state_value)
                    in UNSAFE_ENABLED_STATES
                ):
                    return "must not contain an enabled paid configuration"

    if normalized_key in {"spend_cap", "spend_cap_status"}:
        if value is False:
            return "must not disable the spend cap"
        if isinstance(value, str) and normalize_policy_key(value) in {
            "disabled",
            "none",
            "off",
            "removed",
            "unlimited",
        }:
            return "must not disable the spend cap"
        if isinstance(value, Mapping):
            for raw_state, state_value in value.items():
                state = normalize_policy_key(str(raw_state))
                if state in {
                    "disable",
                    "disabled",
                    "remove",
                    "removed",
                } and not _disabled_state(state_value):
                    return "must not disable the spend cap"
                if (
                    state in {"mode", "state", "status"}
                    and isinstance(state_value, str)
                    and normalize_policy_key(state_value)
                    in {"disabled", "none", "off", "removed", "unlimited"}
                ):
                    return "must not disable the spend cap"

    if normalized_key in {
        "disable_spend_cap",
        "remove_spend_cap",
        "spend_cap_disablement",
        "spend_cap_removal",
    } and not _disabled_state(value):
        return "must be false or explicitly disabled"
    return None


def _inert_output_command(tokens: list[str], source: str) -> bool:
    if not tokens:
        return False
    executable = tokens[0].rsplit("/", 1)[-1].lower()
    return (
        executable in INERT_OUTPUT_EXECUTABLES
        and not SHELL_CONTROL.search(source)
    )


def _shell_words(value: str) -> list[str]:
    try:
        return shlex.split(value)
    except ValueError:
        return value.split()


def _unwrap_command_tokens(
    raw_tokens: list[str], source: str
) -> list[str]:
    tokens = list(raw_tokens)
    for _ in range(8):
        if not tokens or _inert_output_command(tokens, source):
            return []
        executable = tokens[0].rsplit("/", 1)[-1].lower()
        if executable == "env":
            index = 1
            split_tokens: list[str] | None = None
            while index < len(tokens):
                token = tokens[index].lower()
                if (
                    tokens[index] == "-S" or token == "--split-string"
                ) and index + 1 < len(tokens):
                    split_tokens = (
                        _shell_words(tokens[index + 1])
                        + tokens[index + 2 :]
                    )
                    break
                if token.startswith("--split-string="):
                    split_tokens = (
                        _shell_words(tokens[index].split("=", 1)[1])
                        + tokens[index + 1 :]
                    )
                    break
                if tokens[index].startswith("-S") and len(tokens[index]) > 2:
                    split_tokens = (
                        _shell_words(tokens[index][2:])
                        + tokens[index + 1 :]
                    )
                    break
                if token in ENV_OPTIONS_WITH_VALUE:
                    index += 2
                    continue
                if token.startswith("-") or (
                    "=" in token and not token.startswith("=")
                ):
                    index += 1
                    continue
                break
            tokens = split_tokens if split_tokens is not None else tokens[index:]
            continue
        if executable == "sudo":
            index = 1
            while index < len(tokens):
                token = tokens[index].lower()
                if token in SUDO_OPTIONS_WITH_VALUE:
                    index += 2
                elif token.startswith("-"):
                    index += 1
                else:
                    break
            tokens = tokens[index:]
            continue
        wrapper_options = COMMAND_WRAPPER_OPTIONS_WITH_VALUE.get(executable)
        if wrapper_options is not None:
            index = 1
            while index < len(tokens):
                token = tokens[index].lower()
                if token == "--":
                    index += 1
                    break
                if token in wrapper_options:
                    index += 2
                    continue
                if token.startswith("-"):
                    index += 1
                    continue
                break
            tokens = tokens[index:]
            continue
        if executable in SIMPLE_COMMAND_WRAPPERS:
            index = 1
            if index < len(tokens) and tokens[index] == "--":
                index += 1
            tokens = tokens[index:]
            continue
        if executable in SHELL_EXECUTABLES:
            payload: str | None = None
            for index, token in enumerate(tokens[:-1]):
                if token.lower() in SHELL_COMMAND_FLAGS:
                    payload = tokens[index + 1]
                    break
            if payload is None:
                return tokens
            source = payload
            tokens = _shell_words(payload)
            continue
        interpreter = re.sub(r"\d+(?:\.\d+)*$", "", executable)
        flags = CODE_INTERPRETER_FLAGS.get(interpreter)
        if flags is not None:
            for index, token in enumerate(tokens[:-1]):
                if token.lower() not in flags:
                    continue
                payload = tokens[index + 1]
                if CODE_COMMAND_EXECUTION.search(payload):
                    source = payload
                    literal_values = [
                        match.group("value")
                        for match in QUOTED_CODE_LITERAL.finditer(payload)
                    ]
                    tokens = (
                        _shell_words(" ".join(literal_values))
                        if literal_values
                        else re.findall(r"[A-Za-z0-9_-]+", payload)
                    )
                    break
            else:
                return tokens
            continue
        return tokens
    return tokens


def _compound_command_parts(value: str) -> tuple[str, ...] | None:
    option = value.strip().lower().lstrip("-")
    if not option:
        return None
    alias = COMMAND_TOKEN_ALIASES.get(option)
    if alias is not None:
        return alias
    parts = tuple(
        part for part in re.split(r"[-_=]+", option) if part
    )
    if not parts:
        return None
    if parts in COMMAND_CONCEPT_SEQUENCES:
        return parts
    if (
        len(parts) > 1
        and parts[-1] in COMMAND_STATE_WORDS
        and parts[:-1] in COMMAND_CONCEPT_SEQUENCES
    ):
        return parts
    transition_words = (
        COMMAND_ACTIVATION_WORDS
        | COMMAND_DISABLE_WORDS
        | {"add", "register", "upgrade"}
    )
    if parts[0] in transition_words:
        remainder = parts[1:]
        if remainder and remainder[-1] in COMMAND_STATE_WORDS:
            remainder = remainder[:-1]
        if remainder in COMMAND_CONCEPT_SEQUENCES:
            return parts
    return None


def _paid_option_is_enabled(
    raw_value: str, parts: tuple[str, ...]
) -> bool:
    if not raw_value.startswith("-"):
        return False
    explicit_value = (
        normalize_policy_key(raw_value.rsplit("=", 1)[1])
        if "=" in raw_value
        else None
    )
    if explicit_value in FALSE_OPTION_STATES:
        return False
    concept = (
        parts[:-1]
        if parts and parts[-1] in COMMAND_STATE_WORDS
        else parts
    )
    if concept in STRONG_BARE_PAID_OPTIONS:
        # A missing value enables a boolean option. Any explicit state other
        # than a known false state is cost-unknown and therefore fails closed.
        return explicit_value is None or explicit_value not in FALSE_OPTION_STATES
    return explicit_value in COMMAND_ENABLED_WORDS


def _command_tokens(value: str | Iterable[str]) -> list[str]:
    if isinstance(value, str):
        raw_tokens = _shell_words(value)
        source = value
    else:
        raw_tokens = [str(token) for token in value]
        source = " ".join(raw_tokens)

    raw_tokens = _unwrap_command_tokens(raw_tokens, source)

    tokens: list[str] = []
    for raw_token in raw_tokens:
        lowered = raw_token.strip().lower()
        alias = COMMAND_TOKEN_ALIASES.get(lowered)
        if alias is not None:
            tokens.extend(alias)
            continue
        compound = _compound_command_parts(lowered)
        if compound is not None:
            tokens.extend(compound)
            if _paid_option_is_enabled(lowered, compound):
                tokens.append("__paid_option_enabled__")
            continue
        if lowered.startswith("-"):
            tokens.append(lowered)
            continue
        word = re.sub(r"^[^a-z0-9]+|[^a-z0-9_]+$", "", lowered)
        if word:
            tokens.append(word)
    return tokens


def _contains_sequence(tokens: list[str], sequence: tuple[str, ...]) -> bool:
    size = len(sequence)
    return any(
        tuple(tokens[index : index + size]) == sequence
        for index in range(len(tokens) - size + 1)
    )


def paid_action_text_reasons(
    value: str | Iterable[str],
) -> list[str]:
    """Detect paid transitions in executable action or command fields.

    Callers deliberately apply this only to structured execution fields.
    Descriptions, notes, research text, and other inert prose are not scanned.
    A trailing denial such as ``; echo never`` cannot neutralize an earlier
    executable transition.
    """

    tokens = _command_tokens(value)
    token_set = set(tokens)
    activates = bool(
        token_set & (COMMAND_ACTIVATION_WORDS | COMMAND_ENABLED_WORDS)
    ) or "__paid_option_enabled__" in token_set
    payg = "payg" in token_set or _contains_sequence(
        tokens, ("pay", "as", "you", "go")
    )
    auto_renew = _contains_sequence(tokens, ("auto", "renew"))
    paid_fallback = _contains_sequence(tokens, ("paid", "fallback"))
    paid_add_on = _contains_sequence(tokens, ("paid", "add", "on"))
    paid_data = (
        _contains_sequence(tokens, ("paid", "data"))
        or _contains_sequence(tokens, ("paid", "data", "source"))
        or _contains_sequence(tokens, ("paid", "dataset"))
    )
    payment_method = _contains_sequence(tokens, ("payment", "method"))
    spend_cap = _contains_sequence(tokens, ("spend", "cap"))
    free_quota_exceedance = _contains_sequence(
        tokens, ("free", "quota", "exceedance")
    ) or _contains_sequence(tokens, ("quota", "overage"))

    reasons: list[str] = []
    if activates and payg:
        reasons.append("enables pay-as-you-go billing")
    if activates and auto_renew:
        reasons.append("enables an auto-renewing paid transition")
    if activates and (
        paid_fallback or paid_add_on or "overage" in token_set
    ):
        reasons.append("enables a paid fallback, add-on, or overage")
    if activates and paid_data:
        reasons.append("enables prohibited paid data")
    if activates and ("billing" in token_set or "charges" in token_set):
        reasons.append("enables billing or charges")
    if spend_cap and bool(
        token_set
        & (
            COMMAND_DISABLE_WORDS
            | {"false", "none", "unbounded", "unlimited"}
        )
    ):
        reasons.append("removes or disables the spend cap")
    if payment_method and bool(token_set & {"add", "register"}):
        reasons.append("registers a payment method")
    if "upgrade" in token_set and bool(
        token_set & {"plan", "subscription", "tier"}
    ):
        reasons.append("upgrades a paid plan")
    if free_quota_exceedance and bool(
        token_set & {"allow", "enable", "allowed", "enabled"}
    ):
        reasons.append("allows free-quota exceedance")
    if _contains_sequence(tokens, ("automatic", "upgrade")) and activates:
        reasons.append("enables automatic plan upgrade")
    return list(dict.fromkeys(reasons))


def policy_violations(value: Any, prefix: str = "") -> list[str]:
    """Find secret values and paid-transition aliases in untrusted JSON.

    The scanner is intentionally key-directed so ordinary prose that discusses
    pricing or secrets is not rejected.  Secret *names* may be declared, but
    secret values and authority-like configuration remain invalid.
    """

    errors: list[str] = []
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = str(raw_key)
            normalized_key = normalize_policy_key(key)
            child_prefix = f"{prefix}.{key}" if prefix else key
            secret_name_declaration = normalized_key.endswith(
                ("secret_names", "required_secret_names")
            )
            if (
                SECRET_VALUE_KEY.search(normalized_key)
                and not secret_name_declaration
                and not _empty_or_zero(child)
                and not safe_secret_placeholder(child)
            ):
                errors.append(f"{child_prefix} must not contain a secret value")
            paid_reason = structured_paid_transition_reason(
                normalized_key, child
            )
            if paid_reason is not None:
                errors.append(f"{child_prefix} {paid_reason}")
            if (
                normalized_key in PAID_ACTION_TEXT_KEYS
                and (
                    isinstance(child, str)
                    or (
                        isinstance(child, list)
                        and all(isinstance(item, str) for item in child)
                    )
                )
            ):
                for reason in paid_action_text_reasons(child):
                    errors.append(
                        f"{child_prefix} describes a prohibited paid action: "
                        f"{reason}"
                    )
                if isinstance(child, list):
                    joined_argv = " ".join(child)
                    for reason in literal_secret_reasons(joined_argv):
                        errors.append(f"{child_prefix} {reason}")
                    for reason in command_argv_secret_reasons(child):
                        errors.append(f"{child_prefix} {reason}")
            errors.extend(policy_violations(child, child_prefix))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(policy_violations(child, f"{prefix}[{index}]"))
    elif isinstance(value, str):
        for reason in literal_secret_reasons(value):
            errors.append(f"{prefix or '<value>'} {reason}")
    return errors


class CapabilityError(ValueError):
    """Raised when a capability configuration is invalid."""


def _string_list(value: Any, label: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise CapabilityError(f"{label} must be an array of non-empty strings")
    if len(value) != len(set(value)):
        raise CapabilityError(f"{label} must not contain duplicates")
    return [item.strip() for item in value]


def _validate_capability(name: str) -> None:
    if name in CAPABILITIES:
        return
    if name.startswith("x-") and PORTABLE_ID.fullmatch(name):
        return
    raise CapabilityError(f"unknown capability: {name}")


def _validate_profile(name: str) -> None:
    if name in PROFILE_CAPABILITIES:
        return
    if name.startswith("x-") and PORTABLE_ID.fullmatch(name):
        return
    raise CapabilityError(f"unknown profile: {name}")


def _validate_mutually_exclusive_capabilities(
    capabilities: Iterable[str],
) -> None:
    selected = set(capabilities)
    for group, members in MUTUALLY_EXCLUSIVE_CAPABILITY_GROUPS.items():
        conflicts = sorted(selected & members)
        if len(conflicts) < 2:
            continue
        raise CapabilityError(
            f"{group} capabilities are mutually exclusive "
            f"({', '.join(conflicts)}); select agent-team-execution for a "
            "host-native concurrent team, or multi-agent-write for a legacy "
            "single-root Story"
        )


def expand_capabilities(
    capabilities: Iterable[str],
    profiles: Iterable[str] = (),
) -> list[str]:
    expanded: set[str] = set()
    for profile in profiles:
        _validate_profile(profile)
        expanded.update(PROFILE_CAPABILITIES.get(profile, ()))
    for capability in capabilities:
        _validate_capability(capability)
        expanded.add(capability)

    changed = True
    while changed:
        changed = False
        for capability in tuple(expanded):
            implied = CAPABILITY_IMPLICATIONS.get(capability, ())
            missing = set(implied) - expanded
            if missing:
                expanded.update(missing)
                changed = True
    _validate_mutually_exclusive_capabilities(expanded)
    return sorted(expanded)


def resolve_assurance(
    requested: str | None,
    profiles: Iterable[str] = (),
    capabilities: Iterable[str] = (),
) -> str:
    assurance = requested or "standard"
    if assurance not in ASSURANCE_RANK:
        raise CapabilityError(
            "assurance must be one of " + ", ".join(ASSURANCE_LEVELS)
        )
    rank = ASSURANCE_RANK[assurance]
    for profile in profiles:
        profile_assurance = PROFILE_ASSURANCE.get(profile)
        if profile_assurance is not None:
            rank = max(rank, ASSURANCE_RANK[profile_assurance])
    for capability in capabilities:
        floor = CAPABILITY_ASSURANCE_FLOOR.get(capability)
        if floor is not None:
            rank = max(rank, ASSURANCE_RANK[floor])
    return ASSURANCE_LEVELS[rank]


def resolve_delivery(
    requested: str | None,
    assurance: str,
    capabilities: Iterable[str] = (),
) -> str:
    """Resolve delivery without raising risk assurance.

    ``assurance=release`` remains the historical Strict-plus-release
    compatibility value. Current capability-based work uses risk assurance
    ``light``/``standard``/``strict`` and delivery ``local``/``release``.
    """

    if requested is not None and requested not in DELIVERY_LEVELS:
        raise CapabilityError(
            "delivery must be one of " + ", ".join(DELIVERY_LEVELS)
        )
    has_remote_release = "remote-release" in set(capabilities)
    legacy_release = assurance == "release"
    inferred = "release" if has_remote_release or legacy_release else "local"
    delivery = requested or inferred
    if delivery == "local" and (has_remote_release or legacy_release):
        raise CapabilityError(
            "delivery=local conflicts with remote-release or legacy "
            "assurance=release"
        )
    if (
        delivery == "release"
        and not has_remote_release
        and not legacy_release
    ):
        raise CapabilityError(
            "delivery=release requires the remote-release capability"
        )
    return delivery


def required_gates(
    capabilities: Iterable[str],
    assurance: str,
) -> list[str]:
    if assurance not in ASSURANCE_GATES:
        raise CapabilityError(f"unknown assurance: {assurance}")
    gates = set(ASSURANCE_GATES[assurance])
    for capability in capabilities:
        gates.update(CAPABILITY_GATES.get(capability, ()))
    return sorted(gates)


def adapter_ids(adapters: Any) -> list[str]:
    if adapters is None:
        return []
    if not isinstance(adapters, Mapping):
        raise CapabilityError("adapters must be an object")
    values: list[str] = []
    for key, value in adapters.items():
        if not isinstance(key, str) or not PORTABLE_ID.fullmatch(key):
            raise CapabilityError("adapter roles must be portable IDs")
        if isinstance(value, str):
            candidate_values = [value]
        elif isinstance(value, list) and all(
            isinstance(item, str) and item.strip() for item in value
        ):
            candidate_values = value
        else:
            raise CapabilityError(
                f"adapters.{key} must be a string or string array"
            )
        for candidate in candidate_values:
            normalized = candidate.strip()
            if not PORTABLE_ID.fullmatch(normalized):
                raise CapabilityError(
                    f"adapter ID must be portable: {normalized!r}"
                )
            values.append(normalized)
    return sorted(set(values))


def required_references(
    capabilities: Iterable[str],
    profiles: Iterable[str],
    adapters: Any,
) -> list[str]:
    references = list(CORE_REFERENCES)
    for capability in capabilities:
        references.extend(CAPABILITY_REFERENCES.get(capability, ()))
    for profile in profiles:
        references.extend(PROFILE_REFERENCES.get(profile, ()))
    for adapter in adapter_ids(adapters):
        reference = ADAPTER_REFERENCES.get(adapter)
        if reference is not None:
            references.append(reference)
    return list(dict.fromkeys(references))


def resolve(
    manifest: Mapping[str, Any] | None = None,
    *,
    capabilities: Iterable[str] = (),
    profiles: Iterable[str] = (),
    assurance: str | None = None,
    delivery: str | None = None,
    adapters: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    manifest = manifest or {}
    manifest_capabilities = _string_list(
        manifest.get("capabilities"), "capabilities"
    )
    manifest_profiles = _string_list(manifest.get("profiles"), "profiles")
    selected_profiles = list(
        dict.fromkeys([*manifest_profiles, *profiles])
    )
    for profile in selected_profiles:
        _validate_profile(profile)

    selected_capabilities = list(
        dict.fromkeys([*manifest_capabilities, *capabilities])
    )
    effective_capabilities = expand_capabilities(
        selected_capabilities,
        selected_profiles,
    )
    effective_assurance = resolve_assurance(
        assurance or manifest.get("assurance"),
        selected_profiles,
        effective_capabilities,
    )
    effective_delivery = resolve_delivery(
        delivery or manifest.get("delivery"),
        effective_assurance,
        effective_capabilities,
    )
    manifest_adapters = manifest.get("adapters") or {}
    if not isinstance(manifest_adapters, Mapping):
        raise CapabilityError("adapters must be an object")
    selected_adapters = dict(manifest_adapters)
    if adapters:
        selected_adapters.update(adapters)

    custom_required_gates: list[str] = []
    configs = manifest.get("capability_config") or {}
    if not isinstance(configs, Mapping):
        raise CapabilityError("capability_config must be an object")
    for capability in effective_capabilities:
        if not capability.startswith("x-"):
            continue
        config = configs.get(capability)
        if not isinstance(config, Mapping):
            raise CapabilityError(
                f"{capability} requires capability_config.{capability}"
            )
        gates = _string_list(
            config.get("required_gates"),
            f"capability_config.{capability}.required_gates",
        )
        if not gates:
            raise CapabilityError(
                f"{capability} requires at least one custom required gate"
            )
        for gate in gates:
            if not PORTABLE_ID.fullmatch(gate):
                raise CapabilityError(
                    f"custom required gate must be a portable ID: {gate!r}"
                )
        custom_required_gates.extend(gates)

    gates = set(
        required_gates(effective_capabilities, effective_assurance)
    )
    gates.update(custom_required_gates)
    return {
        "assurance": effective_assurance,
        "delivery": effective_delivery,
        "profiles": selected_profiles,
        "declared_capabilities": selected_capabilities,
        "effective_capabilities": effective_capabilities,
        "adapters": selected_adapters,
        "adapter_ids": adapter_ids(selected_adapters),
        "required_gates": sorted(gates),
        "custom_required_gates": sorted(set(custom_required_gates)),
        "required_references": required_references(
            effective_capabilities,
            selected_profiles,
            selected_adapters,
        ),
    }
