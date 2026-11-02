## Summary

<!-- What does this PR change, and why? -->

Closes #

## AI assistance

<!--
Required. Say whether AI was used for this PR (analysis, code, tests or description).
If it was, give the tool, the model, the reasoning effort (if the tool exposes it) and what the AI did.
-->

- AI used: <!-- yes / no -->
- Tool: <!-- e.g. Claude Code, GitHub Copilot, Cursor -->
- Model: <!-- e.g. Claude Opus 5.5 -->
- Effort: <!-- e.g. high -->
- What the AI did: <!-- e.g. root cause analysis, code, tests, PR description -->

## Checklist

- [ ] The PR title follows [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `refactor:`...), it is used to generate the changelog
- [ ] `uv run ruff format --check`, `uv run ruff check` and `uv run ty check custom_components tests` pass
- [ ] `uv run pytest tests/` passes, and tests cover the change
- [ ] I have reviewed and tested every AI-generated change
