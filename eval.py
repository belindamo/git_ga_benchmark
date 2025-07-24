from models import Run, EvalResult, eval_function
from pathlib import Path
import sys
import os
import json
from typing import Optional, List
from pydantic import BaseModel, Field

from ai import dspy

class EvaluationResult(BaseModel):
    """Structured evaluation result from DSPy."""
    pattern_recognition: int = Field(description="Score for pattern recognition (0-25)")
    pattern_recognition_justification: str = Field(description="Brief justification for pattern recognition score")
    specific_evidence: int = Field(description="Score for specific evidence (0-25)")
    specific_evidence_justification: str = Field(description="Brief justification for specific evidence score")
    root_cause_analysis: int = Field(description="Score for root cause analysis (0-25)")
    root_cause_analysis_justification: str = Field(description="Brief justification for root cause analysis score")
    actionable_insights: int = Field(description="Score for actionable insights (0-25)")
    actionable_insights_justification: str = Field(description="Brief justification for actionable insights score")
    total_score: int = Field(description="Total score (sum of all criteria)")
    overall_assessment: str = Field(description="2-3 sentence summary of the evaluation")

def get_source_answer(task_id: str) -> str:
    """Load the source answer for the given task."""
    eval_dir = Path(__file__).parent
    source_file = eval_dir / "dataset_from_dspy" / "source_answers" / f"{task_id}.md"
    
    if not source_file.exists():
        return f"No source answer found for task {task_id}"
    
    return source_file.read_text()

def get_agent_answer(run: Run) -> str:
    """Get the agent's answer from the run."""
    # First check if a specific agent answer path is provided
    if run.agent_answer_path and Path(run.agent_answer_path).exists():
        return Path(run.agent_answer_path).read_text()
    
    # Otherwise look for common agent output files in the env path
    env_path = Path(run.env_path)
    output_files = [
        "answer.txt", "analysis.md", "response.txt", "output.txt",
        "result.md", "solution.txt", "findings.txt", "agent_output.txt"
    ]
    
    for filename in output_files:
        file_path = env_path / filename
        if file_path.exists():
            return file_path.read_text()
    
    # If no specific output file found, return indication
    return "No agent answer file found. Agent may have provided answer in terminal output only."

# DSPy evaluation using the EvaluationResult model

@eval_function
def evaluate_git_qa(run: Run) -> EvalResult:
    """Evaluate git repository Q&A task using DSPy structured output."""
    
    task_id = run.task_id
    
    # Get source and agent answers
    source_answer = get_source_answer(task_id)
    agent_answer = get_agent_answer(run)
    
    # Use DSPy for structured evaluation
    try:
        # Create a DSPy signature for evaluation
        class EvaluateGitQA(dspy.Signature):
            """Evaluate an AI agent's git repository analysis against a reference answer.
            
            Evaluate the agent's answer against the expected source answer on 4 criteria:
            1. Pattern Recognition (0-25): Does the agent identify recurring patterns across multiple issues/commits?
            2. Specific Evidence (0-25): Does the agent provide specific issue numbers, PR numbers, and commit evidence?
            3. Root Cause Analysis (0-25): Does the agent explain underlying causes, not just symptoms?
            4. Actionable Insights (0-25): Does the agent provide practical recommendations or solutions?
            
            For each criterion: 25=Excellent, 20=Good, 15=Fair, 10=Poor, 0=Missing.
            """
            
            task_id: str = dspy.InputField(desc="The task identifier")
            source_answer: str = dspy.InputField(desc="The expected reference answer")
            agent_answer: str = dspy.InputField(desc="The agent's actual answer")
            
            evaluation_result: EvaluationResult = dspy.OutputField(desc="Structured evaluation result")

        evaluator = dspy.ChainOfThought(EvaluateGitQA)
        
        result = evaluator(
            task_id=task_id,
            source_answer=source_answer,
            agent_answer=agent_answer
        )
        
        evaluation_result = result.evaluation_result
        
        # Normalize to 0-1 range
        normalized_score = evaluation_result.total_score / 100.0
        
        return EvalResult(
            score=normalized_score,
            details={
                "pattern_recognition": evaluation_result.pattern_recognition,
                "pattern_recognition_justification": evaluation_result.pattern_recognition_justification,
                "specific_evidence": evaluation_result.specific_evidence,
                "specific_evidence_justification": evaluation_result.specific_evidence_justification,
                "root_cause_analysis": evaluation_result.root_cause_analysis,
                "root_cause_analysis_justification": evaluation_result.root_cause_analysis_justification,
                "actionable_insights": evaluation_result.actionable_insights,
                "actionable_insights_justification": evaluation_result.actionable_insights_justification,
                "total_score": evaluation_result.total_score,
                "overall_assessment": evaluation_result.overall_assessment,
                "source_answer_length": len(source_answer),
                "agent_answer_length": len(agent_answer),
                "task_id": task_id
            }
        )
        
    except Exception as e:
        return EvalResult(
            score=0.0,
            details={
                "error": str(e),
                "task_id": task_id,
                "source_answer_length": len(source_answer),
                "agent_answer_length": len(agent_answer)
            }
        )


def load_tasks() -> List[dict]:
    """Load tasks from the dataset."""
    tasks_file = Path(__file__).parent / "dataset_from_dspy" / "questions.json"
    if not tasks_file.exists():
        raise FileNotFoundError(f"Tasks file not found: {tasks_file}")
    
    with open(tasks_file, 'r') as f:
        return json.load(f)


def evaluate_task(task_data: dict, env_path: str = None, agent_answer_path: str = None) -> EvalResult:
    """Evaluate a single task."""
    run = Run(
        task_id=task_data["task_id"],
        task=task_data["task"],
        env_path=env_path or f"./envs/{task_data['task_id']}",
        agent_answer_path=agent_answer_path
    )
    
    return evaluate_git_qa(run)


def main():
    """Main evaluation function."""
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="Evaluate git-qa-benchmark tasks")
    parser.add_argument("--task-id", help="Specific task ID to evaluate")
    parser.add_argument("--env-path", help="Path to the environment directory")
    parser.add_argument("--agent-answer", help="Path to the agent's answer file")
    parser.add_argument("--output", help="Output file for results (JSON)")
    args = parser.parse_args()
    
    # Load tasks
    tasks = load_tasks()
    
    if args.task_id:
        # Evaluate specific task
        task_data = next((task for task in tasks if task["task_id"] == args.task_id), None)
        if not task_data:
            print(f"Task {args.task_id} not found")
            return
        
        print(f"Evaluating task: {args.task_id}")
        result = evaluate_task(task_data, args.env_path, args.agent_answer)
        
        print(f"Score: {result.score:.2f}")
        print(f"Details: {json.dumps(result.details, indent=2)}")
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump({
                    "task_id": args.task_id,
                    "score": result.score,
                    "details": result.details
                }, f, indent=2)
    else:
        # Evaluate all tasks
        print(f"Evaluating {len(tasks)} tasks...")
        results = []
        
        for task_data in tasks:
            print(f"Evaluating: {task_data['task_id']}")
            try:
                result = evaluate_task(task_data, args.env_path)
                results.append({
                    "task_id": task_data["task_id"],
                    "score": result.score,
                    "details": result.details
                })
                print(f"  Score: {result.score:.2f}")
            except Exception as e:
                print(f"  Error: {e}")
                results.append({
                    "task_id": task_data["task_id"],
                    "score": 0.0,
                    "error": str(e)
                })
        
        # Calculate average score
        valid_scores = [r["score"] for r in results if "error" not in r]
        avg_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0.0
        
        print(f"\nEvaluation complete!")
        print(f"Average score: {avg_score:.2f}")
        print(f"Tasks evaluated: {len(valid_scores)}/{len(tasks)}")
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump({
                    "summary": {
                        "average_score": avg_score,
                        "tasks_evaluated": len(valid_scores),
                        "total_tasks": len(tasks)
                    },
                    "results": results
                }, f, indent=2)


if __name__ == "__main__":
    main()