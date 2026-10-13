"""
Reusable Lead Scoring Report.

Creates a summary from scored universal lead records.
This module is CRM-independent.
"""


def create_scoring_report(scored_leads):
    """
    Create a summary report from scored leads.
    """

    report = {
        "total_leads": len(scored_leads),
        "high": 0,
        "medium": 0,
        "low": 0,
        "leads": [],
    }

    for lead in scored_leads:

        priority = lead.get("priority")

        if priority == "High":
            report["high"] += 1

        elif priority == "Medium":
            report["medium"] += 1

        elif priority == "Low":
            report["low"] += 1

        report["leads"].append({
            "lead_id": lead.get("lead_id"),
            "customer": lead.get("customer"),
            "lead_score": lead.get("lead_score"),
            "priority": priority,
        })

    return report
