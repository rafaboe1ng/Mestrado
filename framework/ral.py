"""RAL: Responsive Application Layer for the FDM case: a print-profile serialiser.

Receives only the approved steps of a plan. Each operation declares the geometry it needs
(``OPERATION_INPUTS``); a step whose feature lacks one of those dimensions is refused, never guessed,
and the refusal goes back to the KEFC store as a ``serialisation_input_missing`` request. Accounting
is explicit: handed = serialised + refused.

Output is a per-feature modifier profile (JSON plus a slicer-style INI text), each value carrying the
rule identifier it came from. No machine is driven from here.
"""
from __future__ import annotations

import json
from pathlib import Path

from framework.expert_validation import ExpertValidationStore
from framework.skl.build_ontologies import PARAMETER_NAMES

OPERATION_INPUTS = {
    "BaseDepositionOp": ("length_mm", "width_mm", "thickness_mm"),
    "WallDepositionOp": ("height_mm", "thickness_mm"),
    "HoleDepositionOp": ("diameter_mm",),
    "RibDepositionOp": ("thickness_mm", "height_mm"),
    "OverhangDepositionOp": ("length_mm", "angle_deg", "thickness_mm"),
}


class PrintProfileSerialiser:
    def __init__(self, expert_store: ExpertValidationStore):
        self.store = expert_store

    def partition_steps(self, approved_steps: list[dict]) -> tuple[list[dict], list[dict]]:
        serialisable, refused = [], []
        for s in approved_steps:
            required = OPERATION_INPUTS.get(s["operation"])
            if required is None:
                refused.append({"step": s, "reason": f"no serialisation contract for {s['operation']}"})
                continue
            missing = [d for d in required if d not in s["dimensions"]]
            if missing:
                refused.append({"step": s, "reason": f"{s['operation']} needs {list(required)}; missing {missing}"})
                continue
            absent = [p for p in PARAMETER_NAMES if p not in s["parameters"]]
            if absent:
                refused.append({"step": s, "reason": f"parameter records missing for {absent}"})
                continue
            serialisable.append(s)
        return serialisable, refused

    def serialise(self, plan: dict, output_dir: str | Path) -> dict:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        approved = plan["approved_steps"]
        ok, refused = self.partition_steps(approved)
        refusals = []
        for r in refused:
            s = r["step"]
            req = self.store.create_request(s["feature_id"], s["feature_type"], "serialisation_input_missing", r["reason"], operation=s["operation"])
            refusals.append({"step_number": s["step_number"], "feature_id": s["feature_id"], "operation": s["operation"],
                             "reason": r["reason"], "request_id": req.request_id})
        self.store.save()
        profile = {
            "job_id": plan["job_id"], "material": plan["material"], "machine": plan["machine"],
            "generated_from": "manufacturing_plan.json", "skl_version": plan["skl_version"], "reasoner": plan["reasoner"],
            "steps": [{
                "step_number": s["step_number"], "feature_id": s["feature_id"], "feature_local_id": s["feature_local_id"],
                "feature_type": s["feature_type"], "operation": s["operation"],
                "geometry": {d: s["dimensions"][d] for d in OPERATION_INPUTS[s["operation"]]},
                "parameters": {p: {"value": s["parameters"][p]["value"], "unit": s["parameters"][p]["unit"]} for p in PARAMETER_NAMES},
                "provenance": {p: s["parameters"][p]["rule_id"] for p in PARAMETER_NAMES},
                "validation_status": s["validation_status"],
            } for s in ok],
            "accounting": {"handed": len(approved), "serialised": len(ok), "refused": len(refused)},
        }
        (out / "print_profile.json").write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")
        (out / "print_profile.ini").write_text(self._ini(profile), encoding="utf-8")
        (out / "ral_refusals.json").write_text(json.dumps({"accounting": profile["accounting"], "refusals": refusals}, indent=2), encoding="utf-8")
        return {**profile["accounting"], "refusals": refusals, "profile_path": str(out / "print_profile.json")}

    @staticmethod
    def _ini(profile: dict) -> str:
        lines = [f"; print profile for {profile['job_id']} | material {profile['material']} | machine {profile['machine']}",
                 f"; skl_version {profile['skl_version']} | reasoner {profile['reasoner']} | every value cites its rule", ""]
        for s in profile["steps"]:
            lines.append(f"[step {s['step_number']}: {s['feature_local_id']} ({s['feature_type']}) {s['operation']}]")
            for p, v in s["parameters"].items():
                lines.append(f"{p} = {v['value']:g} {v['unit']}    ; rule {s['provenance'][p]}")
            lines.append("")
        return "\n".join(lines)
