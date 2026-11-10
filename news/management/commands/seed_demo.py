from datetime import timedelta
from pathlib import Path
from django.conf import settings
from django.core.files import File
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify
from news.models import Article, Author, Category, Tag
class Command(BaseCommand):
    help = 'Add clearly labelled sample content. Never run automatically in production.'
    def handle(self,*args,**options):
        call_command('setup_newsroom')
        author,_ = Author.objects.get_or_create(slug='cedarmond-desk',defaults={'name':'Cedarmond Desk','bio':'The Cedarmond TV editorial desk. These sample articles demonstrate the publishing experience.'})
        tag,_ = Tag.objects.get_or_create(slug='the-big-picture',defaults={'name':'The big picture'})
        stories = [
          ('Kenya','Beyond the skyline: the conversations shaping Kenya’s next chapter','A closer look at the people, places and ideas that will define our coverage of a changing country.','landscape.jpg'),
          ('Business','The small businesses with big ambitions','Meet the questions behind our enterprise coverage: opportunity, resilience and the cost of doing business.','business.jpg'),
          ('Counties','Closer to home: a new lens on county stories','From Kisii to the coast, local perspectives belong at the centre of the national conversation.','landscape.jpg'),
          ('Technology','What a more connected Kenya could look like','Our technology desk explores access, digital skills and the everyday impact of new tools.','technology.jpg'),
          ('Politics','The public-interest questions our politics desk will ask','Accountability begins with clear questions, reliable documents and voices from across the country.','business.jpg'),
          ('Culture','A creative generation finding its own voice','A space for the artists, storytellers and cultural conversations shaping contemporary Kenya.','culture.jpg'),
          ('Sports','Beyond the final whistle: the stories behind the sport','Our sports coverage will look at the work, communities and ambitions behind every performance.','sports.jpg'),
          ('Opinion','Why local journalism deserves a wider conversation','A sample opinion column introducing the importance of context, curiosity and public trust.','landscape.jpg'),
          ('Kenya','The everyday stories worth paying attention to','Our newsroom starts with a simple idea: ordinary experiences can reveal the bigger picture.','culture.jpg'),
          ('Business','Reading the economy through everyday decisions','A sample explainer on the questions that connect household choices to the wider economy.','business.jpg'),
          ('Technology','Digital life, explained in plain language','A foundation for useful guides that make technology easier to understand.','technology.jpg'),
          ('Counties','A place for every county in the national conversation','Our county desk is being built around reporting that listens before it speaks.','landscape.jpg')]
        for index,(category,title,summary,image) in enumerate(stories):
            item,created = Article.objects.get_or_create(slug=slugify(title),defaults={'title':title,'summary':summary,'body':'This is sample editorial content created to demonstrate the Cedarmond TV publishing platform. It is not a report of a current event.\n\n'+summary+'\n\nOur newsroom will build this coverage through interviews, public documents and careful verification. Published reporting should identify its sources, explain what is known and make uncertainty clear.\n\nThis article demonstrates the reading layout, author attribution, sharing controls and related stories. Replace it with original, verified reporting before launch.','category':Category.objects.get(name=category),'author':author,'status':'published','published_at':timezone.now()-timedelta(hours=index),'featured':index==0,'editors_pick':index in [3,5,6],'demo':True})
            item.tags.add(tag)
            file = Path(settings.BASE_DIR)/'demo-assets'/image
            if created and file.exists():
                with file.open('rb') as stream: item.image.save(image,File(stream),save=False)
                item.image_alt = 'Illustrative photograph accompanying sample editorial content'
                item.image_credit = 'Illustrative stock photograph / Unsplash. Not a photograph of a reported event.'
                item.save()
        self.stdout.write(self.style.SUCCESS('12 labelled sample stories ready.'))
