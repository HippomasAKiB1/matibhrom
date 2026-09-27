"""
Prompt template builder for Matibhrom.
"""

from pathlib import Path
from typing import Any

from src.schema import Item
from src.hashing import hash_prompt, hash_template


class PromptBuilder:
    """Builds prompts from templates for different conditions and languages."""

    def __init__(self, prompt_dir: str | Path):
        self.prompt_dir = Path(prompt_dir)
        self._templates: dict[str, str] = {}
        self._abstention_phrase: str | None = None
        self._load_templates()
        self._load_abstention_phrase()

    def _load_templates(self) -> None:
        """Load all prompt templates from the prompt directory."""
        template_files = {
            "C0_bn": "c0_no_evidence_bn.txt",
            "C0_banglish": "c0_no_evidence_banglish.txt",
            "C1_bn": "c1_oracle_bn.txt",
            "C1_banglish": "c1_oracle_banglish.txt",
            "C2_bn": "c2_rag_bn.txt",
            "C2_banglish": "c2_rag_banglish.txt",
            "C3_bn": "c3_rag_abstention_bn.txt",
            "C3_banglish": "c3_rag_abstention_banglish.txt",
        }

        for key, filename in template_files.items():
            path = self.prompt_dir / filename
            if path.exists():
                self._templates[key] = path.read_text(encoding="utf-8")
            else:
                raise FileNotFoundError(f"Template not found: {path}")

    def _load_abstention_phrase(self) -> None:
        """Load the abstention phrase from abstention_phrase.txt."""
        path = self.prompt_dir / "abstention_phrase.txt"
        if path.exists():
            self._abstention_phrase = path.read_text(encoding="utf-8").strip()
        else:
            raise FileNotFoundError(f"Abstention phrase not found: {path}")

    def get_abstention_phrase(self) -> str:
        """Get the abstention phrase."""
        if self._abstention_phrase is None:
            self._load_abstention_phrase()
        return self._abstention_phrase

    def get_template_name(self, condition: str, language: str) -> str:
        """Get the template key for a condition and language."""
        return f"{condition}_{language}"

    def build_prompt(
        self,
        item: Item,
        language: str,
        condition: str,
        evidence: str | None = None,
        retrieved_context: str | None = None,
    ) -> tuple[str, str]:
        """
        Build a prompt for the given item, language, and condition.

        Returns:
            (prompt_text, template_name)
        """
        template_key = self.get_template_name(condition, language)
        template = self._templates.get(template_key)

        if template is None:
            raise ValueError(f"No template for {template_key}")

        # Select question based on language
        question = item.question_bn if language == "bn" else item.question_banglish

        # Build prompt based on condition
        if condition == "C0":
            prompt = template.format(question=question)

        elif condition == "C1":
            if evidence is None:
                raise ValueError("C1 requires evidence")
            prompt = template.format(evidence=evidence, question=question)

        elif condition == "C2":
            if retrieved_context is None:
                raise ValueError(f"{condition} requires retrieved_context")
            prompt = template.format(retrieved_context=retrieved_context, question=question)

        elif condition == "C3":
            if retrieved_context is None:
                raise ValueError(f"{condition} requires retrieved_context")
            prompt = template.format(
                retrieved_context=retrieved_context,
                question=question,
                abstention_phrase=self.get_abstention_phrase(),
            )

        else:
            raise ValueError(f"Unknown condition: {condition}")

        return prompt, template_key

    def hash_template(self, template_key: str) -> str:
        """Get the hash of a template."""
        if template_key not in self._templates:
            raise ValueError(f"Unknown template: {template_key}")
        return hash_template(self._templates[template_key])

    def get_template_hashes(self) -> dict[str, str]:
        """Get hashes of all templates."""
        return {key: hash_template(text) for key, text in self._templates.items()}

    def get_abstention_phrase_hash(self) -> str:
        """Get the hash of the abstention phrase."""
        return hash_prompt(self.get_abstention_phrase())


def load_templates(prompt_dir: str | Path) -> dict[str, str]:
    """Load all templates from a directory. Convenience function."""
    builder = PromptBuilder(prompt_dir)
    return builder._templates.copy()


def build_prompt(
    item: Item,
    language: str,
    condition: str,
    evidence: str | None = None,
    retrieved_context: str | None = None,
    abstention_phrase: str = "",
    prompt_dir: str | Path = "configs/prompts",
) -> tuple[str, str]:
    """Convenience function to build a prompt."""
    builder = PromptBuilder(prompt_dir)
    if condition == "C3" and abstention_phrase:
        builder._abstention_phrase = abstention_phrase
    return builder.build_prompt(item, language, condition, evidence, retrieved_context)