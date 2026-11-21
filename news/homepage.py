from django import forms
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.forms import modelformset_factory
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from .models import Article, Category


class HomepageForm(forms.Form):
    lead = forms.ModelChoiceField(queryset=Article.objects.none(), required=False, empty_label='Automatic: latest published story')
    top_one = forms.ModelChoiceField(queryset=Article.objects.none(), required=False, label='First supporting story')
    top_two = forms.ModelChoiceField(queryset=Article.objects.none(), required=False, label='Second supporting story')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.queryset = Article.objects.live()

    def clean(self):
        data = super().clean()
        ids = [item.pk for item in data.values() if item]
        if len(ids) != len(set(ids)):
            raise forms.ValidationError('Choose a different story for each position.')
        return data


def homepage_editor(request, site):
    if not request.user.has_perms(['news.change_article', 'news.publish_article', 'news.change_category']):
        raise PermissionDenied
    live = Article.objects.live()
    lead = live.filter(featured=True).order_by('-homepage_rank', '-published_at').first()
    top = list(live.exclude(pk=lead.pk if lead else None).filter(homepage_rank__gt=0).order_by('-homepage_rank', '-published_at')[:2])
    initial = {'lead': lead, 'top_one': top[0] if top else None, 'top_two': top[1] if len(top)>1 else None}
    form = HomepageForm(request.POST if request.method == 'POST' else None, initial=initial)
    CategoryFormSet = modelformset_factory(Category, fields=('position',), extra=0)
    sections = CategoryFormSet(request.POST if request.method == 'POST' else None, queryset=Category.objects.all(), prefix='sections')
    if request.method == 'POST' and form.is_valid() and sections.is_valid():
        with transaction.atomic():
            # Lock the placement rows and preserve their normal history records.
            stories = list(Article.objects.select_for_update().filter(pk__in=live.values('pk')))
            choices = form.cleaned_data
            ranks = {story.pk: 99-i for i, story in enumerate(choices.get(key) for key in ('lead','top_one','top_two')) if story}
            for story in stories:
                rank = ranks.get(story.pk, 0)
                featured = bool(choices['lead'] and story.pk == choices['lead'].pk)
                if (story.homepage_rank, story.featured) != (rank, featured):
                    story.homepage_rank, story.featured = rank, featured
                    story._history_user = request.user
                    story.save(update_fields=['homepage_rank', 'featured'])
            sections.save()
        messages.success(request, 'Homepage placement and section order saved.')
        return redirect('admin:homepage_editor')
    return TemplateResponse(request, 'admin/homepage_editor.html', dict(site.each_context(request), title='Homepage editor', form=form, sections=sections))
