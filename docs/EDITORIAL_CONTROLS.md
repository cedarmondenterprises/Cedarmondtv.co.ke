# Editorial controls

## Homepage

Open /admin/homepage/ or the newsroom homepage link. Publishing editors with
change-article and change-category permission can select a lead and two
supporting stories and set section navigation order. Only currently published
stories are selectable. Saving replaces existing homepage ranks and featured
flags for current published stories; it does not publish or unpublish content.
Leaving the lead blank restores the latest-story fallback. Lower section
position numbers appear first. These controls do not add new homepage section
blocks. Other editor picks remain managed on the article form.

## Related reporting

Under Reader key facts on an article, optionally choose related stories.
The public Keep reading section selects up to three: manual selections first,
then shared topics, then the same category. Drafts, future stories and the
current story are excluded. Manual selections use publication date order.

## Author profiles

Edit Authors to fill in Role, Reporting interests and Biography. The existing
author URL shows these alongside published work and matching ProfilePage data.
No credentials, biographies or headshots are invented. Optional fields can be
left blank. Existing author URLs are retained.

## Deployment

Migration 0016 adds optional author fields and a related-story relation. Back up
the production database before deploying. No external service is required.
