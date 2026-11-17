def can_view_article(user, article):
    return user.is_active and user.is_staff and user.has_perm('news.view_article') and (
        user.has_perm('news.publish_article') or article.owner_id == user.pk or
        user.has_perm('news.view_article', article) or user.has_perm('news.change_article', article))

def can_edit_article(user, article):
    return can_view_article(user, article) and user.has_perm('news.change_article') and (
        user.has_perm('news.publish_article') or (article.status != 'published' and (
            article.owner_id == user.pk or user.has_perm('news.change_article', article))))

def accessible_articles(user, queryset):
    from django.db.models import Q
    from guardian.shortcuts import get_objects_for_user
    if user.has_perm('news.publish_article'): return queryset
    shared = get_objects_for_user(user, ['news.view_article','news.change_article'],
                                  klass=queryset, any_perm=True, accept_global_perms=False)
    return queryset.filter(Q(owner=user) | Q(pk__in=shared.values('pk')))
