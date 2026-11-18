"""Align existing public policy pages with Google advertising disclosures.

Only replace known outdated wording and leave other editorial changes intact.
"""
from django.db import migrations


PAGE_DESCRIPTIONS = {
    "about": "Learn about Cedarmond TV, our Kenyan news coverage, reporting approach and commitment to editorial independence.",
    "editorial-standards": "Read Cedarmond TV's standards for accuracy, verification, fairness, attribution, photographs, opinion and corrections.",
    "corrections": "Find out how to report a factual error, request a correction or raise a newsroom complaint with Cedarmond TV.",
    "advertising": "Explore advertising and sponsorship enquiries with Cedarmond TV and our policy protecting editorial independence.",
    "privacy": "How Cedarmond TV handles reader data, privacy rights, audience measurement and Google advertising when enabled.",
    "cookies": "Learn about essential cookies, browser storage, optional Google advertising cookies and privacy choices at Cedarmond TV.",
    "terms": "Read Cedarmond TV's terms on editorial content, copyright, reader comments, external links and use of the website.",
}

PRIVACY_CHANGES = [
    (
        "We do not sell personal information or use third-party behavioural advertising or analytics tools.",
        "We do not sell personal information. Where advertising or third-party measurement services are enabled, we disclose their use below.",
    ),
    (
        "<h2>Audience measurement</h2>",
        "<h2>Google advertising and third-party measurement</h2>"
        "<p>If Google AdSense is enabled, Google and other advertising vendors may place or read cookies, "
        "and use web beacons, IP addresses or other identifiers to serve, personalise where permitted, "
        "and measure advertising. Google's advertising cookies may be based on your previous visits "
        "to this website or other websites. You can manage personalised Google advertising at "
        "<a href='https://myadcenter.google.com/'>Google My Ad Center</a> and review other advertising "
        "opt-out tools at <a href='https://www.aboutads.info/'>aboutads.info</a>. "
        "We will provide consent choices where required by applicable law. "
        "Details of any additional enabled vendors will be added to this notice.</p>"
        "<h2>Audience measurement</h2>",
    ),
    (
        "The site does not store raw IP addresses or full browser/device identifiers, set analytics cookies, or build persistent device fingerprints.",
        "Our first-party article-view counts do not store raw IP addresses or full browser/device identifiers, "
        "set analytics cookies, or build persistent device fingerprints. "
        "Enabled third-party advertising or measurement services may separately process identifiers as described above.",
    ),
]

COOKIE_CHANGES = [
    (
        "The current site does not use analytics cookies or third-party behavioural advertising trackers.",
        "If Google AdSense or other measurement services are enabled, they may also use cookies or similar technologies as described below.",
    ),
    (
        "<h2>External services</h2>",
        "<h2>Advertising and optional third-party cookies</h2>"
        "<p>When Google AdSense is enabled, Google and its advertising partners may use cookies, IP addresses "
        "and web beacons to serve, personalise where permitted, and measure advertisements. "
        "You can manage personalised Google ads at <a href='https://myadcenter.google.com/'>Google My Ad Center</a>. "
        "We will provide consent choices for non-essential technologies where required by applicable law.</p>"
        "<h2>External services</h2>",
    ),
    (
        "If we add analytics, personalised advertising or other non-essential tracking in future, we will update this notice and provide any choices required by applicable law before that processing begins.",
        "We will update this notice when we enable or change analytics, personalised advertising or other non-essential tracking and provide any choices required by applicable law.",
    ),
]


def update_public_pages(apps, schema_editor):
    Page = apps.get_model("news", "Page")
    for slug, seo_description in PAGE_DESCRIPTIONS.items():
        page = Page.objects.filter(slug=slug).first()
        if page is None:
            continue
        changes = {}
        body = page.body or ""
        for old, new in (PRIVACY_CHANGES if slug == "privacy" else COOKIE_CHANGES if slug == "cookies" else []):
            if old in body:
                body = body.replace(old, new, 1)
        if body != page.body:
            changes["body"] = body
        if not page.seo_description:
            changes["seo_description"] = seo_description
        if changes:
            Page.objects.filter(pk=page.pk).update(**changes)


class Migration(migrations.Migration):
    dependencies = [
        ("news", "0011_adsenseconfiguration"),
    ]

    operations = [
        migrations.RunPython(update_public_pages, migrations.RunPython.noop),
    ]
