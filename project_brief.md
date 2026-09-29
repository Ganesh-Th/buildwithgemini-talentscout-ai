# My agent: TalentScout AI
One-liner: A conversational career scout that helps tech professionals find matching job opportunities and tech events in AI/ML and Full-Stack with a curated catalog of openings, conferences, and custom email digests.

Tool coverage:
- Memory: User resume highlights (skills, experience level, preferences), target locations/remote preferences, and delivery history of previously recommended jobs/events to prevent duplicates.
- Tools: Event search (`search_tech_events`), job postings search (`search_jobs`), and email dispatcher (`send_digest_email`).
- Catalog/UI: Job opportunity cards, event/conference cards, and required-vs-resume skills match tables rendered with A2UI.
- Image gen: Personalized digest header banners and event highlight cards using Gemini image generation.
- Sandbox: Python code sandbox to compute quantitative resume-to-job match percentages and relevance scores.

Recommended for every project: memory, storage, tools, image generation, A2UI
Agent-specific / stretch (pick what fits): Code sandbox for resume-job matching calculations, Cloud Scheduler for periodic background digest triggering, Cloud Trace for observability.
