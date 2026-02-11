# Findings & Decisions

## Requirements
- School district slide deck: 7 pages, minimal style, English
- XHS content: 4 images, bold style, Chinese, targeting cross-border sellers
- All assets should reflect VOSB certification and 68K order track record

## Research Findings
- Planning-with-files skill based on Manus context engineering (Meta $2B acquisition)
- Core principle: filesystem = persistent memory, context window = volatile RAM
- 3-file pattern (task_plan + findings + progress) prevents context loss after 50+ tool calls
- "Read Before Decide" pattern refreshes goals in attention window
- 3-Strike Error Protocol: diagnose → alternative → rethink → escalate

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Use planning-with-files 3-file pattern | Persistent context across sessions for multi-project workflow |
| Created CLAUDE.md | Project-level context for all Claude Code sessions |
| baoyu-skills for content generation | Comprehensive skill set covering slides, images, social media |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| XHS workflow interrupted by task switch | Planning files will preserve state for resumption |
| Slide deck workflow interrupted at outline review | Outline saved in outline.md, ready to resume |

## Resources
- baoyu-skills repo: https://github.com/JimLiu/baoyu-skills
- planning-with-files repo: https://github.com/OthmanAdi/planning-with-files
- Manus context engineering: https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus
- Slide deck outline: `slide-deck/leisdeal-packaging-school-districts/outline.md`
- XHS analysis: `xhs-images/vosb-sell-to-us-gov/analysis.md`
