import logging
import os
import subprocess

import openai

from app.config import settings
from app.models import ReviewResult

logger = logging.getLogger(__name__)

REVIEW_SYSTEM_PROMPT = (
    "You are a senior code reviewer. Review the following git diff for a task. "
    "Look for bugs, security issues, incomplete implementations, and correctness problems. "
    "If the changes are acceptable, reply with exactly 'APPROVED'. "
    "If not, reply with 'REJECTED: <reason>' where <reason> explains what must be fixed."
)


class Reviewer:
    def __init__(self) -> None:
        self.client = openai.OpenAI(api_key=settings.openai_api_key)

    def review(self, repo_dir: str, task_description: str) -> ReviewResult:
        diff = self._get_diff(repo_dir)
        if not diff.strip():
            return ReviewResult(approved=False, reason="No changes detected")

        if len(diff) > 80_000:
            diff = diff[:80_000] + "\n... [truncated at 80k chars]"

        response = self.client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"## Task\n{task_description}\n\n"
                        f"## Diff\n```diff\n{diff}\n```"
                    ),
                },
            ],
            temperature=0.2,
            max_tokens=1024,
        )

        reply = response.choices[0].message.content.strip()
        logger.info("Reviewer response: %s", reply[:200])
        return self._parse(reply)

    def _get_diff(self, repo_dir: str) -> str:
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        result = subprocess.run(
            "git diff HEAD",
            shell=True,
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
        return result.stdout

    @staticmethod
    def _parse(reply: str) -> ReviewResult:
        upper = reply.upper()
        if upper.startswith("APPROVED"):
            return ReviewResult(approved=True, reason="Approved")
        if upper.startswith("REJECTED:"):
            reason = reply[len("REJECTED:"):].strip()
            return ReviewResult(approved=False, reason=reason or "Rejected without reason")
        return ReviewResult(approved=False, reason=f"Ambiguous reviewer response: {reply[:500]}")
