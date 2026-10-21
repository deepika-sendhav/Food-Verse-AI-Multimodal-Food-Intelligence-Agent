# Final demo and sharing checklist

- [ ] `python scripts/check_all.py` passes.
- [ ] Backend pytest suite passes.
- [ ] Frontend tests pass.
- [ ] Frontend production build passes and bundle report is reviewed.
- [ ] No hardcoded secrets are found in tracked files.
- [ ] `git ls-files` contains no `.env`, virtual environment, build output,
      uploads, test media, or other sensitive files.
- [ ] `DEMO_MODE=true` returns labeled sample responses and the frontend
      persistent demo banner is visible.
- [ ] Live backend health reports configured status correctly.
- [ ] Food recognition tried with a non-sensitive real sample image.
- [ ] Freshness detector tried with a non-sensitive real sample image.
- [ ] Hygiene monitor tried with a non-sensitive real sample image/video.
- [ ] Kitchen assistant tried with the sample text (and optionally a safe
      browser dictation check).
- [ ] Meal planner tried with made-up profile data, including the safety gate.
- [ ] Screenshots taken at desktop and 360px mobile widths, with no personal
      data or secrets visible.
- [ ] Root README, demo script, deployment guide, and this checklist are
      complete.
- [ ] Repository link opens and contains only intended source and documentation.
