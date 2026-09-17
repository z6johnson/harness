# Governance

## Consent

Participation is voluntary. Before collection begins, the participant must receive:

- the purpose of the measurement
- what data stays local
- what data is submitted
- who can see each store
- how long records are kept
- how to correct or withdraw
- confirmation that records will not be used for performance review

Use `assets/consent-template.md` as the starting point.

## Pseudonymity

The analytical record contains a participant code, not a name or email address. The identity map is stored separately and available only to the designated record holder.

For a one-person dry run, the test subject may serve as record holder. For a multi-person pilot, use a record holder outside the participants' performance-review chain.

## Data Minimization

Keep local:

- message content
- thread titles
- raw session IDs
- attachment names
- file paths
- machine hostname
- local username

Submit only:

- participant code
- week
- work type
- confirmed time values
- baseline method and estimate
- checking, cleanup, learning, coordination, and redo hours
- new-capacity answer
- confidence and provenance
- thread and turn counts for the weekly aggregate

Thread references stay in the local metadata store. Historical detailed records may already contain a pseudonymous thread reference; do not add new ones to aggregate submissions.
The aggregate flow does not read or store thread titles.

## Access

- Store responses in a UCSD-owned Shared Drive.
- Disable public link sharing.
- Restrict the response Sheet to the analysis team.
- Store the identity map in a separate restricted location.
- Review access before the pilot, midway, and at closeout.

## Retention

Set a retention date before collection begins. Delete individual records on that date. Keep only aggregate totals afterward.

Disclose that Google Sheets version history may retain deleted values under administrator-controlled retention policy.

## Small Groups

Small groups can make people identifiable even without names. Use pilot-wide or weekly aggregate reporting. Suppress breakdowns that could identify a participant.
