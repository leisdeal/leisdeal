# LEISDEAL Project

## About
LEISDEAL is a VOSB-certified (Veteran-Owned Small Business) packaging solutions company based in Riverside, California. Founded by a U.S. Navy veteran with 68,000+ orders fulfilled.

## Project Structure

```
leisdeal/
├── CLAUDE.md              # This file — project context
├── task_plan.md           # Current tasks and phases
├── findings.md            # Research and decisions log
├── progress.md            # Session progress log
├── slide-deck/            # Presentation decks
├── xhs-images/            # Xiaohongshu content
├── .claude/skills/        # Installed Claude skills
└── .agents/skills/        # Skill source files
```

## Business Context
- **Industry**: Packaging & shipping supplies
- **Certification**: VOSB (Veteran-Owned Small Business)
- **Location**: Riverside, CA
- **Track Record**: 68,000+ orders
- **Key Markets**: Government agencies, school districts, commercial
- **Differentiators**: No minimum orders, GPC accepted, local fulfillment

## Active Projects
1. **School District PPT** — 7-slide minimal deck for procurement officers (`slide-deck/leisdeal-packaging-school-districts/`)
2. **XHS Content** — 小红书 content about selling to US government (`xhs-images/vosb-sell-to-us-gov/`)

## Planning System (from planning-with-files)
- **task_plan.md** — Active task phases, decisions, errors
- **findings.md** — Research findings, requirements, resources
- **progress.md** — Session logs, test results, error history
- Re-read task_plan.md before major decisions
- Log ALL errors — never repeat failures
- Update after each phase completion

## Installed Skills
### Content Creation (baoyu-skills v1.31.2)
- `baoyu-xhs-images` — 小红书图文
- `baoyu-slide-deck` — PPT演示文稿
- `baoyu-cover-image` — 封面图
- `baoyu-infographic` — 信息图
- `baoyu-image-gen` — AI图片生成
- `baoyu-post-to-x` / `baoyu-post-to-wechat` — 社媒发布
- `baoyu-url-to-markdown` — 网页转Markdown
- `baoyu-format-markdown` — Markdown格式化

### Planning
- `planning-with-files` — Manus-style file-based task planning
