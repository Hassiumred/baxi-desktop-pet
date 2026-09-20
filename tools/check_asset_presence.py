"""Fail early for the deliberately asset-free source candidate."""
from pathlib import Path
import json
import sys
ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {"idle_v0_6":16,"observe_sit_v0_6":18,"walk_left_v0_6":18,"walk_right_v0_6":18,"groom_paw_v0_7":18,"stretch_front_v0_7":16,"feed_can_v0_9":16,**{f"dance_{i:02d}_v0_9":18 for i in range(1,6)}}
def main():
    missing=[]
    for action,count in EXPECTED.items():
        folder=ROOT / "app/assets/baxi/actions" / action
        try:
            data=json.loads((folder / "source_manifest.json").read_text(encoding="utf-8"))
            frames=data["frames"]
            if len(frames)!=count: raise ValueError("frame count mismatch")
            for item in frames:
                file=(folder / item["file"]).resolve()
                if not file.is_relative_to(folder.resolve()) or not file.is_file():
                    raise ValueError("missing or unsafe frame path")
        except (OSError,ValueError,KeyError,TypeError):
            missing.append(action)
    if missing:
        print("ASSETS_NOT_INCLUDED: source-only review candidate; see ASSETS.md. Missing/invalid: " + ", ".join(missing))
        return 2
    print("Asset files present. Run validate_baxi_assets.py before building; presence is not rights clearance.")
    return 0
if __name__ == "__main__":
    sys.exit(main())
