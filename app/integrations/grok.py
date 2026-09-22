"""Grok (x.ai) employee-insight engine. Calls the x.ai chat API when XAI_API_KEY
is set; otherwise returns a deterministic local heuristic so the feature works
without a key. Same output shape either way."""
import json
import httpx

from ..config import GROQ_API_KEY, GROQ_BASE_URL, GROQ_MODEL


def _heuristic(emp: dict, progress: list[dict], results: list[dict]) -> dict:
    readiness = emp.get("readinessScore", 0)
    skills = emp.get("skills", [])
    weak = sorted(skills, key=lambda s: s.get("proficiency", 0))[:3]
    done = [p for p in progress if p.get("status") == "completed"]
    completion = round(100 * len(done) / len(progress)) if progress else 0
    passed = [r for r in results if r.get("passed")]
    pass_rate = round(100 * len(passed) / len(results)) if results else 0

    suggestions = []
    for s in weak:
        suggestions.append(
            f"Strengthen {s.get('skill')}: currently {s.get('proficiency')}/10 — "
            f"take an advanced module and a hands-on project.")
    if completion < 60 and progress:
        suggestions.append(
            f"Training completion is {completion}% — finish assigned material to lift readiness.")
    if pass_rate < 60 and results:
        suggestions.append(
            f"Assessment pass rate is {pass_rate}% — schedule a re-attempt after focused prep.")
    if readiness >= 80:
        suggestions.append("Readiness is strong — propose for deployment / client interviews.")
    if not suggestions:
        suggestions.append("On track. Maintain momentum and pick one stretch skill.")

    summary = (f"{emp.get('name')} is at {readiness}% readiness with {completion}% "
               f"training completion and a {pass_rate}% assessment pass rate.")
    return {
        "provider": "heuristic",
        "summary": summary,
        "readinessScore": readiness,
        "trainingCompletionPct": completion,
        "assessmentPassRatePct": pass_rate,
        "focusSkills": [s.get("skill") for s in weak],
        "suggestions": suggestions,
    }


def employee_insights(emp: dict, progress: list[dict], results: list[dict]) -> dict:
    if not GROQ_API_KEY:
        return _heuristic(emp, progress, results)
    try:
        prompt = (
            "You are a talent-development analyst. Given this engineer's data, "
            "return STRICT JSON with keys: summary (string), suggestions (array of "
            "strings, concrete upskilling actions), focusSkills (array of strings). "
            f"DATA:\n{json.dumps({'employee': emp, 'progress': progress, 'results': results})}")
        r = httpx.post(
            f"{GROQ_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={"model": GROQ_MODEL, "temperature": 0.2,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=30)
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        content = content.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
        data = json.loads(content)
        base = _heuristic(emp, progress, results)
        base.update({k: v for k, v in data.items() if v})
        base["provider"] = "grok"
        return base
    except Exception as e:
        fallback = _heuristic(emp, progress, results)
        fallback["provider"] = "heuristic"
        fallback["grokError"] = str(e)
        return fallback
