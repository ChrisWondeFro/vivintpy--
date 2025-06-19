Prompting Guide for v0 (by Vercel)—merged with best practices from the v0 Crash Course—to help generate polished, production-ready UI and app prototypes.

⸻

1. 🎯 Start with a Specific & Structured Prompt
	•	Define purpose clearly (platform, target users, core flows).
	•	Provide a brief PRD: outline product overview, user flows, key pages/components (use bullet lists or numbered sections)  ￼ ￼.
	•	Optionally, refine your prompt using ChatGPT or Claude to ensure structure and clarity  ￼.

⸻

2. Iterative Refinement & Component-Level Control
	•	Use v0’s select mode to target and tweak individual components: resize, restyle, update behaviors .
	•	Break prompts into sections: request UI in logical chunks (e.g., navigation bar, input forms, result cards) for controlled buildout  ￼.

⸻

3. Include References & Context
	•	Provide URL or image snapshots of existing designs for inspiration or replication.
	•	v0 will attempt to mirror layouts using Tailwind + shadcn/ui  ￼ ￼.
	•	Include Figma links or frames, ideally structured into discrete components, to guide accuracy .

⸻

4. Pull from Component Libraries
	•	Ask for specific components (e.g., shadcn/ui Button, Modal). Use v0’s “Open in v0” directly from library repos to import and customize  ￼.

⸻

5. Enforce Tech Stack & Architecture Requirements
	•	Clearly state: “Use React + Next.js App Router, fetch from /api/..., integrate with Firebase/Supabase” to generate production-ready scaffolding .

⸻

6. Style, Accessibility & Microcopy
	•	Specify typographic styles, colors, hover/focus states early.
	•	For tone: e.g., “friendly financial coach” voice—use ChatGPT to rewrite microcopy before feeding it into v0  ￼.
	•	Include aria labels and a11y best practices in prompts .

⸻

7. Embed Data & Integrations
	•	Instruct v0 to scaffold API calls or fetch logic from endpoints.
	•	Ask it to map components over data arrays and handle dynamic formatting and error states .

⸻

8. Leverage Versioning & Collaboration
	•	Use v0’s version control to track iterations and rollback as needed .
	•	Use fork to branch off others’ shared templates while preserving your own baseline .

⸻

9. Share & Deploy with Ease
	•	Use built-in Share to share interactive preview and chat context.
	•	Hit Deploy to publish on Vercel with CLI or dashboard scaffolding  ￼.

⸻

10. Maximizing Overall Workflow Efficiency
	•	Start high-level, then drill down: generate page → revise components → refine style & copy → add data & deploy .
	•	Use external tools (ChatGPT PRD writer, Figma kits) for polished input.
	•	One UI piece per prompt, review, then build next—avoid “monolithic” prompts  ￼.

⸻

✅ Sample Starter Prompt

Build a responsive pricing page for a SaaS dashboard using React + Next.js App Router.
- Platform: Desktop + mobile web
- Target users: Small business owners
- Layout:
  1. Header with logo + nav
  2. Pricing toggle (monthly/yearly)
  3. Three plan cards: Basic, Pro, Enterprise
     - Features list, CTA
- Styling: brand colors (#00A8E8 primary, #F5A623 accent), Tailwind CSS
- Accessibility: aria-labels, focus outlines
- Fetch plan info from /api/plans (JSON)
- Use shadcn/ui components & Heroicons
Once generated, select the plan cards and update hover states and aria labels.


⸻

🧩 Quick Reference Table

Category	Prompt Focus
Structure	Detailed PRD → iterative, sectioned prompts
UI Tools	URL/snapshot, Figma, shadcn/ui components
Tech Stack	Specify React, Next.js, Tailwind, imports
Style & Copy	Define colors, typography, tone; refine microcopy via ChatGPT
Data	Instruct fetch calls and dynamic data rendering
Control	Use select mode, version control, and fork for branch experiments
Output	Use Share & Deploy features seamlessly via Vercel


⸻
