from urllib.parse import urlencode

from django import template

register = template.Library()


@register.inclusion_tag('news/share_destinations.html')
def article_sharing(url, title):
    message = f'{title}\n{url}'
    destinations = (
        ('Facebook', 'https://www.facebook.com/sharer/sharer.php', {'u': url}),
        ('X', 'https://twitter.com/intent/tweet', {'url': url, 'text': title}),
        ('LinkedIn', 'https://www.linkedin.com/sharing/share-offsite/', {'url': url}),
        ('Telegram', 'https://t.me/share/url', {'url': url, 'text': title}),
        ('Reddit', 'https://www.reddit.com/submit', {'url': url, 'title': title}),
        ('Pinterest', 'https://www.pinterest.com/pin/create/button/', {'url': url, 'description': title}),
        ('Bluesky', 'https://bsky.app/intent/compose', {'text': message}),
        ('Threads', 'https://www.threads.net/intent/post', {'text': message}),
        ('Tumblr', 'https://www.tumblr.com/widgets/share/tool', {'canonicalUrl': url, 'title': title, 'posttype': 'link'}),
        ('Email', 'mailto:', {'subject': title, 'body': url}),
    )
    return {'destinations': [
        (label, f'{endpoint}?{urlencode(params)}')
        for label, endpoint, params in destinations
    ]}
