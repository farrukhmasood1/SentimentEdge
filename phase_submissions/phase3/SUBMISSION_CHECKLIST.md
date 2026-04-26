# Phase 3 Submission Checklist

**Due:** April 24, 2026 at 11:59 PM (Canvas)

---

## Files to Add Before Submitting

### 1. Final Report PDF — `docs/final_report.pdf`
Must cover:
- Problem and user
- Architecture and design choices
- Implementation or build summary
- Evaluation setup
- Results (8 TC + 4 SC outcomes)
- Failure analysis (reference failure_log.md F-01 to F-05)
- Governance and safety reflection (rumour_pending_review route)
- Lessons learned and future improvements

### 2. Video Link — `media/demo_video_link.txt`
- 5-minute project video (shareable URL)
- Must show: problem, architecture, full pipeline walkthrough, agent coordination, one failure case, final output

### 3. PDF Submission Packet — upload to Canvas
Single PDF containing:
- [ ] Project title: SentimentEdge
- [ ] Team members: Farrukh Masood, Pablo, Moid, Afaq
- [ ] Track: Track A
- [ ] One-paragraph project summary
- [ ] GitHub repo link
- [ ] Link to 5-minute video
- [ ] Final report (attached or linked)
- [ ] Architecture diagram (docs/architecture_diagram.pdf)
- [ ] Screenshot index (docs/screenshots/screenshot_index.md)
- [ ] Evaluation summary (eval/evaluation_results.csv summary)
- [ ] List of submitted files and folders

### 4. Individual Contribution Reflection
Each team member submits their own reflection (check Canvas for format).

---

## Already Complete

- [x] README.md — meets all minimum contents
- [x] AI_USAGE.md — complete with tool versions and prompts
- [x] requirements.txt
- [x] docs/architecture_diagram.pdf
- [x] docs/screenshots/ — 8 screenshots with caption index
- [x] eval/test_cases.md and test_cases.csv — 8 test cases
- [x] eval/evaluation_results.csv — 12 rows (8 TC + 4 SC)
- [x] eval/failure_log.md — 5 documented failures (F-01 to F-05)
- [x] eval/version_notes.md — v0.1 → v0.2 → v0.3
- [x] eval/case_outputs/ — TC-01 to TC-08 evidence files
- [x] outputs/main_run/run_20260425_174443/ — primary evidence run (4+ weeks)
- [x] outputs/sample_runs/run_20260412_110302/ — reference run
- [x] media/demo_video_link.txt — placeholder (fill in URL)
- [x] phase_submissions/phase1/ and phase2/
- [x] Runnable system (python main.py)
- [x] Replay mode (python main.py --replay)
- [x] Web dashboard (web/)
- [x] Governance layer (rumour_pending_review.csv route)

---

## Grader Reproduction Path

No API key needed:
```
python main.py --replay outputs/sample_runs/run_20260412_110302
```

Full run (requires ANTHROPIC_API_KEY and data files in data/raw/):
```
export ANTHROPIC_API_KEY=your_key_here
python main.py
```
