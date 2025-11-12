import json
from typing import Any, Dict, List

from app_tasks import celery
from app_goals.models import Goal


def _tasks_to_history(tasks: List[Any], max_entries: int = 120) -> List[Dict[str, Any]]:
	history: List[Dict[str, Any]] = []
	for task in tasks[-max_entries:]:
		entry = {
			"title": getattr(task, "title", None),
			"description": getattr(task, "description", None),
			"assigned_date": getattr(task, "assigned_date", None).isoformat() if getattr(task, "assigned_date", None) else None,
			"status": getattr(task, "status", None),
			"difficulty": getattr(task, "difficulty", None),
		}
		history.append(entry)
	return history


#system prompts
NEXT_TASK_SYSTEM_PROMPT = """You are an AI Task Planner. ALWAYS return valid JSON only, matching the "next_task" schema provided in the user message. Do NOT include any explanatory text. Use deterministic behavior and avoid hallucinations. Dates MUST use ISO format YYYY-MM-DD. If you cannot compute a sensible task, return {"error":"<short reason>"}.

Business constraints:
- Max allowed goal duration (including AI extensions) is 120 days (4 months). Do not propose task that would make the goal exceed this.
- Use difficult_level in ["easy","medium","hard"].
- Use action in ["assigned","done","missed"] — for a new next-day task use "assigned".
- Title <= 100 chars. Description <= 2000 chars.
- Validate and ensure "assigned_date" is the date on which the task is being generated (i.e today).
- Output numeric fields as numbers (not strings).
Return only a single JSON object matching the schema specified in the user payload.
"""
WEEKLY_REPORT_SYSTEM_PROMPT = """You are the AI Weekly Reporter of a Task Planner App. ALWAYS return valid JSON only, matching the "weekly_report" schema provided in the user message. No extra text. Use ISO dates (YYYY-MM-DD). The "history" array will include full last-week task activity. Compute completed_tasks and missed_tasks by counting history. Provide an actionable ai_suggestion <= 500 chars. If invalid input, return {"error":"..."}."""

MONTHLY_REPORT_SYSTEM_PROMPT = """You are the AI Monthly Analyst. ALWAYS return ONLY JSON matching the "monthly_report" schema provided in the user message. Use last 30 days history provided. Compute completed_tasks and missed_tasks by counting history. Compute a performance_score in percent (0.00 - 100.00) with two decimals. Weight last 7 days 40%, prior days 60% as guidance (model may adapt for less data). Summary <= 1000 chars. If cannot produce, return {"error":"..."}."""


#full prompt builders
def create_next_task_prompt(goal: Goal, tasks: List[Any]) -> Dict[str, str]:
	history = _tasks_to_history(tasks)
	user_payload = {
		"output_schema": {
			"title": "string",
			"description": "string",
			"assigned_date": "YYYY-MM-DD",
			"status": "assigned",
			"difficulty": "easy|medium|hard",
		},
		"history": history,
		"goal": {
			"title": getattr(goal, "title", None),
			"description": getattr(goal, "description", None),
			"start_date": getattr(goal, "start_date", None).isoformat() if getattr(goal, "start_date", None) else None,
			"end_date": getattr(goal, "end_date", None).isoformat() if getattr(goal, "end_date", None) else None,
			"target_days": getattr(goal, "target_days", None)
		}
	}
	json_user_payload = json.dumps(user_payload, ensure_ascii=False, 
	default=str, indent=2)

	return {"system": NEXT_TASK_SYSTEM_PROMPT, "user": json_user_payload}


def create_weekly_report_prompt(goal: Goal, tasks: List[Any]) -> Dict[str, str]:
	history = _tasks_to_history(tasks)
	user_payload = {
		"schema": {
			"week_start": "YYYY-MM-DD",
			"week_end": "YYYY-MM-DD",
			"completed_tasks": "int",
			"missed_tasks": "int",
			"ai_suggestion": "string"
		},
		"goal": {
			"title": getattr(goal, "title", None),
			"description": getattr(goal, "description", None),
			"start_date": getattr(goal, "start_date", None).isoformat() if getattr(goal, "start_date", None) else None,
			"end_date": getattr(goal, "end_date", None).isoformat() if getattr(goal, "end_date", None) else None,
			"target_days": getattr(goal, "target_days", None)
		},
		"history": history
	} 
	json_user_payload = json.dumps(user_payload, ensure_ascii=False, 
	default=str, indent=2)

	return {"system": WEEKLY_REPORT_SYSTEM_PROMPT, "user": json_user_payload}


def create_monthly_report_prompt(goal: Goal, tasks: List[Any]) -> Dict[str, str]:
	history = _tasks_to_history(tasks)
	user_payload = {
		"schema": {
			"month": "1-12",
			"year": "YYYY",
			"completed_tasks": "int",
			"missed_tasks": "int",
			"summary": "string",
			"performance_score": "0.00-100.00"
		},
		"goal": {
			"title": getattr(goal, "title", None),
			"description": getattr(goal, "description", None),
			"start_date": getattr(goal, "start_date", None).isoformat() if getattr(goal, "start_date", None) else None,
			"end_date": getattr(goal, "end_date", None).isoformat() if getattr(goal, "end_date", None) else None,
			"target_days": getattr(goal, "target_days", None)
		},
		"history": history
	} 
	json_user_payload = json.dumps(user_payload, ensure_ascii=False, 
	default=str, indent=2)
	
	return {"system": MONTHLY_REPORT_SYSTEM_PROMPT, "user": json_user_payload}


def remove_user_tasks(task_ids: str):
    if ',' in task_ids:
        ids = task_ids.split(",")
        for task_id in ids:
            if task_id:
                celery.control.revoke(task_id, terminate=True)
    elif task_ids:
        celery.control.revoke(task_ids, terminate=True)
