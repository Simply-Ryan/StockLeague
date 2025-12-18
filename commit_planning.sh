#!/bin/bash

unset GITHUB_TOKEN

cd /workspaces/codespaces-blank/StockLeague

git add ENGAGEMENT_*.md

git commit -m "docs: add comprehensive engagement features implementation plan

- ENGAGEMENT_IMPLEMENTATION_PLAN.md: Technical architecture and detailed specifications for 7 features
  - League-specific activity feed
  - League performance metrics
  - Announcements and system event feed
  - Side-by-side player comparison
  - Integrated league chat sidebar
  - Extended notifications system
  - League analytics dashboard
  
- ENGAGEMENT_TODO_LIST.md: Granular task breakdown with 80+ actionable items
  - Phase 1: Foundation (13 hrs, 3 features)
  - Phase 2: Enhancement (10 hrs, 3 features)
  - Phase 3: Analytics (6 hrs, 1 feature)
  - Database setup, testing, deployment tasks
  - Progress tracking templates
  - Risk assessment matrix
  
- ENGAGEMENT_SUMMARY.md: Executive summary and quick reference
  - Overview of all 7 features
  - Documentation guide
  - Expected outcomes per phase
  - Success metrics and KPIs
  - Readiness checklist
  
Total estimated effort: 22-29 hours over 1-2 weeks
Status: Ready for implementation (pending approval)"

echo "✓ Planning documents committed"
