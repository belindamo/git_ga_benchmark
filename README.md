# git-qa-benchmark

A benchmark for evaluating AI agents' ability to answer temporal questions about Git repositories using only commit history.

## Features

- **5 temporal question categories** - Tests different aspects of repository understanding
- **Universal generation** - Works on any GitHub repository
- **Fair evaluation** - Agents only see commits, not PRs/issues used for question generation
- **Automated pipeline** - From repository to questions to evaluation

## Installation

```bash
git clone https://github.com/belindamo/git-qa-benchmark
cd git-qa-benchmark
uv sync
```

### Generate tasks

Generate 10 tasks per category (default):
```bash
uv run utils/generate_tasks/github_tasks.py https://github.com/stanfordnlp/dspy
```
  
Generate 5 tasks per category, skip comments for speed:
```bash
uv run utils/generate_tasks/github_tasks.py https://github.com/stanfordnlp/dspy --num-tasks 5 --skip-comments
```

### Evaluate

Try out the evaluation by running `uv run tests/test_eval.py`.

You can also run the evaluation with the following commands.

Evaluate all tasks:
```bash
uv run eval.py
```

Evaluate a specific task:
```bash
uv run eval.py --task-id pattern_recognition_teleprompter_crash
```

Evaluate with custom agent answer file:
```bash
uv run eval.py --task-id pattern_recognition_teleprompter_crash --agent-answer ./my_agent_answer.txt
```

Save results to JSON file:
```bash
uv run eval.py --output results.json
```

# 5 Task Types

These tasks test 5 core capabilities that distinguish basic git agents from intelligent repository analysts:

#### 1. 🐛 Bug Patterns (`bug_patterns`)
Tests pattern recognition across multiple issues and commits. Agents must identify recurring problems, root causes, and solutions by analyzing commit history and issue patterns.

#### 2. ⏱️ Timeline Questions (`timeline_questions`) 
Tests timeline understanding and evolution tracking. Agents must trace how features developed over time, including challenges, phases, and implementation details from git history.

#### 3. 🔧 System Interactions (`system_interactions`)
Tests understanding of how different code components affect each other. Agents must explain design rationale and system architecture decisions by analyzing code relationships.

#### 4. 👥 People & Process (`people_process`)
Tests expertise mapping from contribution patterns. Agents must identify the right people for tasks based on actual commit patterns and areas of expertise.

#### 5. 🚀 Performance & Evolution (`performance_evolution`)
Tests understanding of optimization attempts and outcomes. Agents must track what approaches were tried, what worked, what failed, and why.
