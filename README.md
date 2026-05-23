# Agents Cookbook

This repository demonstrates a multi-agent planning flow. One lead planning agent creates the final implementation plan, while specialist reviewer agents check it for missing details, validation, risk, feasibility, facts, and final-answer quality.

## Start Here

- [Browser demo](demo/index.html): open this first for a clickable stakeholder walkthrough.
- [Non-technical agent demo](.opencode/NON_TECH_AGENT_DEMO.md): use this for presenter notes, scripts, and a Markdown version of the walkthrough.
- [Technical flow reference](.opencode/PING_PONG_PLAN_FLOW.md): use this when editing or auditing the actual OpenCode planning flow.

## Run The Demo

Double-click `demo/index.html`, or open it from your browser with File > Open. The demo is self-contained and does not need a dev server, network access, installed packages, or a build step.

## Key Idea

The reviewer agents do not replace the lead planner. They provide focused feedback, and the lead planner returns one clear final plan.
