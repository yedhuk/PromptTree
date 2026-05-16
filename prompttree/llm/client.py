from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Any, Iterator


class LLMClient:
    """Thin wrapper around LiteLLM for unified Azure OpenAI + Ollama/vLLM access."""

    def complete(
        self,
        prompt: str,
        model: str = "gpt-4o",
        temperature: float = 0.7,
        images: list[str] | None = None,
    ) -> str:
        import litellm

        messages = [{"role": "user", "content": self._build_content(prompt, images or [])}]
        response = litellm.completion(model=model, messages=messages, temperature=temperature)
        return response.choices[0].message.content or ""

    def stream(
        self,
        prompt: str,
        model: str = "gpt-4o",
        temperature: float = 0.7,
        images: list[str] | None = None,
    ) -> Iterator[str]:
        import litellm

        messages = [{"role": "user", "content": self._build_content(prompt, images or [])}]
        for chunk in litellm.completion(
            model=model,
            messages=messages,
            temperature=temperature,
            stream=True,
        ):
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_content(
        self, prompt: str, images: list[str]
    ) -> str | list[dict[str, Any]]:
        if not images:
            return prompt

        parts: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        for img_path in images:
            parts.append({"type": "image_url", "image_url": {"url": self._to_data_uri(img_path)}})
        return parts

    @staticmethod
    def _to_data_uri(path: str) -> str:
        mime = mimetypes.guess_type(path)[0] or "image/png"
        data = base64.standard_b64encode(Path(path).read_bytes()).decode()
        return f"data:{mime};base64,{data}"
