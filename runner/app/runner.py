import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

import anthropic

from app.agent_tools import TOOL_DEFINITIONS, ToolExecutor
from app.config import settings
from app.models import TaskConfig
from app.reviewer import Reviewer

logger = logging.getLogger(__name__)

CODER_SYSTEM_PROMPT = (
    "You are an expert software engineer. You are given a task to fix or improve code in a repository. "
    "Use the provided tools to explore the repo, understand the codebase, make changes, and run tests. "
    "When you are confident your changes are correct, call submit_changes with a summary."
)


class AgentRunner:
    def __init__(self) -> None:
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.reviewer = Reviewer()

    def run(self) -> None:
        task = self._load_task()
        task_id = self._sanitize_branch_name(task.issue_id)
        repo_dir = self._clone_repo(task.repo_url, task_id)
        self._setup_git(repo_dir, task_id)
        executor = ToolExecutor(repo_dir)

        for attempt in range(settings.max_review_rejections):
            logger.info("Coder/reviewer attempt %d/%d", attempt + 1, settings.max_review_rejections)

            rejection_feedback = None
            if attempt > 0:
                rejection_feedback = self._last_rejection_reason

            summary = self._coder_loop(task.task_description, executor, rejection_feedback)
            if summary is None:
                logger.error("Coder loop ended without submitting changes")
                sys.exit(1)

            logger.info("Coder submitted: %s", summary)
            review = self.reviewer.review(repo_dir, task.task_description)
            logger.info("Review result: approved=%s reason=%s", review.approved, review.reason)

            if review.approved:
                self._commit_and_push(repo_dir, task_id, summary)
                self._create_pr(repo_dir, task, summary)
                logger.info("PR created successfully")
                return

            self._last_rejection_reason = review.reason
            logger.warning("Review rejected: %s", review.reason)

        logger.error("Max review rejections (%d) reached", settings.max_review_rejections)
        sys.exit(1)

    def _load_task(self) -> TaskConfig:
        path = Path(settings.context_path)
        logger.info("Loading task from %s", path)
        data = json.loads(path.read_text())
        return TaskConfig.model_validate(data)

    @staticmethod
    def _sanitize_branch_name(name: str) -> str:
        sanitized = re.sub(r"[^a-zA-Z0-9_-]", "-", name)
        return sanitized.strip("-")[:60]

    def _clone_repo(self, repo_url: str, task_id: str) -> str:
        repo_dir = str(Path(settings.work_dir) / task_id)
        auth_url = self._inject_token(repo_url)
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        subprocess.run(
            ["git", "clone", "--depth", "50", auth_url, repo_dir],
            check=True,
            env=env,
            capture_output=True,
            text=True,
        )
        logger.info("Cloned repo to %s", repo_dir)
        return repo_dir

    def _inject_token(self, repo_url: str) -> str:
        parsed = urlparse(repo_url)
        if parsed.scheme in ("http", "https"):
            return f"https://x-access-token:{settings.github_token}@{parsed.hostname}{parsed.path}"
        return repo_url

    @staticmethod
    def _setup_git(repo_dir: str, task_id: str) -> None:
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        cmds = [
            ["git", "checkout", "-b", f"fix/{task_id}"],
            ["git", "config", "user.name", "anton-bot"],
            ["git", "config", "user.email", "anton-bot@users.noreply.github.com"],
        ]
        for cmd in cmds:
            subprocess.run(cmd, cwd=repo_dir, check=True, env=env, capture_output=True, text=True)

    def _coder_loop(
        self, task_description: str, executor: ToolExecutor, rejection_feedback: str | None
    ) -> str | None:
        user_content = f"## Task\n{task_description}"
        if rejection_feedback:
            user_content += (
                f"\n\n## Previous Attempt Rejected\n"
                f"The reviewer rejected your previous changes with this feedback:\n{rejection_feedback}\n\n"
                "Please address the feedback and try again."
            )

        messages = [{"role": "user", "content": user_content}]

        for turn in range(settings.max_coder_turns):
            logger.info("Coder turn %d/%d", turn + 1, settings.max_coder_turns)

            response = self.client.messages.create(
                model=settings.anthropic_model,
                max_tokens=8192,
                system=CODER_SYSTEM_PROMPT,
                tools=TOOL_DEFINITIONS,
                messages=messages,
            )

            # Process response and collect tool uses
            assistant_content = response.content
            messages.append({"role": "assistant", "content": assistant_content})

            tool_uses = [b for b in assistant_content if b.type == "tool_use"]

            if not tool_uses:
                if response.stop_reason == "end_turn":
                    messages.append({
                        "role": "user",
                        "content": "You haven't submitted your changes yet. Please continue working or call submit_changes when done.",
                    })
                    continue
                break

            # Execute each tool and build results
            tool_results = []
            submit_summary = None
            for tool_use in tool_uses:
                result_text, is_submit = executor.execute(tool_use.name, tool_use.input)
                logger.info("Tool %s -> %s", tool_use.name, result_text[:100])
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": result_text,
                })
                if is_submit:
                    submit_summary = result_text

            messages.append({"role": "user", "content": tool_results})

            if submit_summary is not None:
                return submit_summary

        return None

    @staticmethod
    def _commit_and_push(repo_dir: str, task_id: str, summary: str) -> None:
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        subprocess.run(["git", "add", "-A"], cwd=repo_dir, check=True, env=env, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", summary],
            cwd=repo_dir, check=True, env=env, capture_output=True, text=True,
        )
        subprocess.run(
            ["git", "push", "-u", "origin", f"fix/{task_id}"],
            cwd=repo_dir, check=True, env=env, capture_output=True, text=True,
        )
        logger.info("Pushed branch fix/%s", task_id)

    @staticmethod
    def _create_pr(repo_dir: str, task: TaskConfig, summary: str) -> None:
        env = {**os.environ, "GH_TOKEN": settings.github_token, "GIT_TERMINAL_PROMPT": "0"}
        subprocess.run(
            [
                "gh", "pr", "create",
                "--title", f"fix({task.issue_id}): {summary[:60]}",
                "--body", (
                    f"## Summary\n{summary}\n\n"
                    f"**Issue:** {task.issue_id}\n\n"
                    "---\n*Automated by anton*"
                ),
            ],
            cwd=repo_dir, check=True, env=env, capture_output=True, text=True,
        )
