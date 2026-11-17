"""Only public fields enter the search service; results are always rechecked in Django."""
import logging
from django.conf import settings
from django.db.models import Case, When
from django.utils.html import strip_tags
from news.models import Article
logger = logging.getLogger(__name__)

def client():
    import meilisearch
    return meilisearch.Client(settings.MEILISEARCH_URL, settings.MEILISEARCH_KEY, timeout=5)

def search_articles(query):
    if not settings.MEILISEARCH_URL or not settings.MEILISEARCH_KEY: return None
    try:
        hits = client().index(settings.MEILISEARCH_INDEX).search(query, {'limit':200})['hits']
        ids = [int(hit['id']) for hit in hits]
        return Article.objects.live().filter(pk__in=ids).order_by(Case(*[When(pk=pk, then=i) for i,pk in enumerate(ids)]))
    except Exception:
        logger.warning('Search service unavailable; using database search.')
        return None

def refresh_search():
    if not settings.MEILISEARCH_URL or not settings.MEILISEARCH_KEY: return 0
    c = client()
    # Replace via a temporary index, then swap, so an incomplete sync is never public.
    staging_name = settings.MEILISEARCH_INDEX + '_staging'
    def wait(task):
        result = c.wait_for_task(task.task_uid, timeout_in_ms=60000)
        if result.status != 'succeeded': raise RuntimeError('Search indexing task failed')
    if settings.MEILISEARCH_INDEX not in [x.uid for x in c.get_indexes()['results']]:
        wait(c.create_index(settings.MEILISEARCH_INDEX, {'primaryKey':'id'}))
    if staging_name in [x.uid for x in c.get_indexes()['results']]: wait(c.delete_index(staging_name))
    wait(c.create_index(staging_name, {'primaryKey':'id'}))
    stage = c.index(staging_name)
    wait(stage.update_searchable_attributes(['title','summary','body','author','category']))
    wait(stage.update_filterable_attributes(['category','author']))
    batch=[]; count=0
    for item in Article.objects.live().iterator(chunk_size=100):
        batch.append({'id':item.pk,'title':item.title,'summary':item.summary,'body':strip_tags(item.body),
                      'author':item.author.name,'category':item.category.name})
        count+=1
        if len(batch)==100: wait(stage.add_documents(batch)); batch=[]
    if batch: wait(stage.add_documents(batch))
    wait(c.swap_indexes([{'indexes':[settings.MEILISEARCH_INDEX,staging_name]}]))
    wait(c.delete_index(staging_name))
    return count
