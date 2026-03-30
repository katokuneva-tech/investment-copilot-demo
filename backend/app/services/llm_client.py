import os
import json
import httpx
from pathlib import Path

# Load .env manually (no extra deps)
_env_path = Path(__file__).parent.parent.parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


class LLMClient:
    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "cotype")
        self.cotype_url = os.getenv("COTYPE_API_URL", "https://demo5-fundres.dev.mts.ai/v1/chat/completions")
        self.cotype_token = os.getenv("COTYPE_API_TOKEN", "")
        self.cotype_model = os.getenv("COTYPE_MODEL", "cotype_pro_2.6")
        self.claude_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.claude_model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
        self.claude_model_deep = os.getenv("CLAUDE_MODEL_DEEP", "claude-opus-4-20250514")
        self._http = None

    @property
    def http(self):
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=15.0))
        return self._http

    async def chat(self, system: str, messages: list[dict], temperature: float = 0.15, tier: str = "standard", max_tokens: int = 4096) -> str:
        # Select model based on tier (for Claude only)
        model_override = None
        if tier == "deep" and self.claude_key:
            model_override = self.claude_model_deep
            print(f"[LLM] Using deep tier: {model_override}")

        try:
            if self.provider == "cotype":
                return await self._call_cotype(system, messages, temperature, max_tokens=max_tokens)
            elif self.provider == "claude":
                return await self._call_claude(system, messages, temperature, model_override=model_override, max_tokens=max_tokens)
            else:
                raise ValueError(f"Unknown LLM provider: {self.provider}")
        except Exception as e:
            # Auto-fallback to the other provider
            fallback = "cotype" if self.provider == "claude" else "claude"
            print(f"[LLM] {self.provider} failed: {e}. Trying {fallback}...")
            try:
                if fallback == "cotype":
                    return await self._call_cotype(system, messages, temperature, max_tokens=max_tokens)
                else:
                    return await self._call_claude(system, messages, temperature, max_tokens=max_tokens)
            except Exception:
                raise e  # re-raise original if fallback also fails

    async def stream(self, system: str, messages: list[dict], temperature: float = 0.15):
        """Async generator yielding text chunks. Auto-fallbacks to other provider on error."""
        try:
            if self.provider == "cotype":
                async for chunk in self._stream_cotype(system, messages, temperature):
                    yield chunk
            elif self.provider == "claude":
                async for chunk in self._stream_claude(system, messages, temperature):
                    yield chunk
        except Exception as e:
            fallback = "cotype" if self.provider == "claude" else "claude"
            print(f"[LLM STREAM] {self.provider} failed: {e}. Falling back to {fallback}...")
            yield f"[Переключение на {fallback}...] "
            try:
                if fallback == "cotype":
                    async for chunk in self._stream_cotype(system, messages, temperature):
                        yield chunk
                else:
                    async for chunk in self._stream_claude(system, messages, temperature):
                        yield chunk
            except Exception:
                yield f"Ошибка обоих провайдеров: {e}"

    async def _call_cotype(self, system: str, messages: list[dict], temperature: float, max_tokens: int = 4096) -> str:
        all_messages = [{"role": "system", "content": system}] + messages
        resp = await self.http.post(
            self.cotype_url,
            headers={
                "Authorization": f"Bearer {self.cotype_token}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.cotype_model,
                "messages": all_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    async def _stream_cotype(self, system: str, messages: list[dict], temperature: float):
        all_messages = [{"role": "system", "content": system}] + messages
        async with self.http.stream(
            "POST",
            self.cotype_url,
            headers={
                "Authorization": f"Bearer {self.cotype_token}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.cotype_model,
                "messages": all_messages,
                "temperature": temperature,
                "max_tokens": 4096,
                "stream": True,
            },
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                line = line.strip()
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except (json.JSONDecodeError, IndexError, KeyError):
                    continue

    async def _call_claude(self, system: str, messages: list[dict], temperature: float, model_override: str = None, max_tokens: int = 4096) -> str:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.claude_key)
            message = client.messages.create(
                model=model_override or self.claude_model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
                temperature=temperature,
            )
            return message.content[0].text
        except ImportError:
            raise RuntimeError("anthropic package not installed")

    async def _stream_claude(self, system: str, messages: list[dict], temperature: float):
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.claude_key)
            with client.messages.stream(
                model=self.claude_model,
                max_tokens=4096,
                system=system,
                messages=messages,
                temperature=temperature,
            ) as stream:
                for text in stream.text_stream:
                    yield text
        except ImportError:
            raise RuntimeError("anthropic package not installed")


# Singleton
llm_client = LLMClient()
