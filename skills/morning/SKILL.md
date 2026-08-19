# Morning Brief

This page is my 30-second morning glance: one calm view of the shape of my day and the few things worth knowing, so I start oriented instead of overwhelmed.

Draw one warm, hand-sketched single-file HTML page. The top half is a visual anchor: the day drawn as terrain with a few words underneath. The bottom half is important things: what needs me, what's already sorted, and any extra sections I've asked for.

## Setup

When I ask to set this up as a recurring task, infer which language the brief should be in: during the interactive session, the language I wrote to you in; otherwise the language I wrote my setup request in. Write the inferred language into the scheduled task's prompt, so unattended runs don't have to guess. When summarizing content from connected sources, make sure the language is consistent.

## Gather

Let the user know this skill will take a few minutes.

Check connections and sort available tools into roles: calendar · email · chat · other (task trackers, docs). A missing role is skipped; the page adapts.

When a core role (calendar, email, chat) has no connected tool and the session is interactive, surface the fix as connector suggestion cards, not prose.

For each missing role, search the connector catalog by its everyday names — calendar: "google calendar", "outlook calendar" · email: "gmail", "email" · chat: "slack", "teams", "chat". The mainstream matches are typically Google Calendar, Gmail, Slack, and Microsoft 365 (Outlook mail/calendar and Teams in one). Offer them as one card of suggestions covering every missing role together, alongside the delivered page.

Checking my existing connections only shows what's already installed — an empty or off-role result there still means the catalog needs searching, and the card shown by that check is not the suggestion. Not every session can search the catalog or offer suggestion cards; when this one can't, skip the cards and let the Write fallbacks carry the ask.

Skip all of this on an unattended scheduled run: no one is there to click, so just render the brief.

Calendar: one fetch, today 00:00 → tomorrow 24:00 in home timezone. Only today's events are drawn and classified. Tomorrow's events are for context: they can colour the evening act, earn a motif, or result in a prep item on Needs attention. From tomorrow's events, extract the project name from any I organize or that name a project and search for the latest context.

Remaining calls on connected roles, in priority:

Email: threads where I was asked and haven't replied. A group [-mention,](-mention,) team alias, or review-requested-from-team where anyone on the list could answer isn't a bottleneck. (fallback: unread last 2d)
Chat: mentions/DMs from ~2d ending in a question I haven't answered or reacted to with an emoji.
Tomorrow prep: for each project from the step above, one chat search — {keyword} after:{7d ago} — and skim the linked doc if the event has one. This finds what's open on the project so a prep item has something concrete to say.
