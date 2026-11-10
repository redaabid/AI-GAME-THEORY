"""Preserve V9 activation/cost counters without changing the shared engine."""

from collections import Counter
from copy import deepcopy
from pathlib import Path

import campaign
import tournament


def run_job(job):
    """Process-local factory observer; it performs no work inside bot turns."""
    original, created = tournament.make_agent, []

    def capture(spec):
        agent = original(spec)
        created.append((spec, agent))
        return agent

    tournament.make_agent = capture
    try:
        result = tournament._run_job(job)
    finally:
        tournament.make_agent = original
    for side in ("a", "b"):
        index = next(i for i, (spec, _) in enumerate(created) if spec == job[side])
        _, agent = created.pop(index)
        if hasattr(agent, "recruitment_totals"):
            result[side + "_stats"]["recruitment"] = deepcopy(agent.recruitment_totals)
    return result


def save_metrics(plan, directory):
    directory = Path(directory)
    games = campaign.read_games(directory, plan)
    totals = dict(decisions=0, guided_decisions=0, chosen_preferred=0,
                  planning_seconds=0.0, work=0, two_capture_decisions=0)
    statuses, per_map = Counter(), {}
    for game in games.values():
        metrics = game["a_stats"].get("recruitment", {})
        for key in totals:
            totals[key] += metrics.get(key, 0)
        statuses.update(metrics.get("statuses", {}))
        row = per_map.setdefault(game["map_name"], dict(games=0, decisions=0, guided_decisions=0))
        row["games"] += 1
        row["decisions"] += metrics.get("decisions", 0)
        row["guided_decisions"] += metrics.get("guided_decisions", 0)
    totals["statuses"] = dict(statuses)
    totals["mean_planning_ms"] = 1000 * totals["planning_seconds"] / max(1, totals["decisions"])
    report = dict(completed_games=len(games), total_games=len(plan["jobs"]),
                  totals=totals, per_map=per_map,
                  nn_assessment="Requires trace review and diverse training data; score alone cannot establish a need for a neural network.")
    campaign.atomic_json(directory / "recruitment.json", report)
    text = (f"Recruitment diagnostics: {len(games)}/{len(plan['jobs'])} completed games.\n\n"
            f"V9 decisions: {totals['decisions']}; root guidance applied: {totals['guided_decisions']}; "
            f"preferred itinerary chosen during guided decisions: {totals['chosen_preferred']}.\n\n"
            f"Decisions with a two-capture itinerary: {totals['two_capture_decisions']}. "
            f"Mean planning time: {totals['mean_planning_ms']:.3f} ms per decision.\n\n"
            "These are planner activations and proposed captures, not completed conversions or proof that guidance caused a move.\n\n"
            "| Map | Games | Decisions | Guided decisions |\n|---|---:|---:|---:|\n")
    for name, row in sorted(per_map.items()):
        text += f"| {name} | {row['games']} | {row['decisions']} | {row['guided_decisions']} |\n"
    text += "\nAnalysis statuses: " + str(dict(statuses)) + ".\n"
    (directory / "recruitment.md").write_text(text, encoding="utf-8")
    return report


def run_campaign(plan, directory, *, max_games=None, progress=None):
    """Use the existing strict checkpoints; submit our importable spawn worker."""
    original = campaign._run_job
    campaign._run_job = run_job

    def report(done, total, result):
        save_metrics(plan, directory)
        if progress is not None:
            progress(done, total, result)

    try:
        result = campaign.run_campaign(plan, directory, max_games=max_games, progress=report)
        save_metrics(plan, directory)
        return result
    finally:
        campaign._run_job = original
