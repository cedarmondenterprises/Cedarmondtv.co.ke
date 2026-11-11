def can_view_article(user,article):
    return user.is_active and user.is_staff and user.has_perm('news.view_article') and (user.has_perm('news.publish_article') or article.owner_id == user.pk)

def can_edit_article(user,article):
    return can_view_article(user,article) and user.has_perm('news.change_article') and (user.has_perm('news.publish_article') or article.status != 'published')
