from import_export import resources
from news.models import Category, Tag

class CategoryResource(resources.ModelResource):
    class Meta:
        model = Category
        fields = ('name','slug','position')
        import_id_fields = ('slug',)
        use_transactions = True
        clean_model_instances = True

class TagResource(resources.ModelResource):
    class Meta:
        model = Tag
        fields = ('name','slug')
        import_id_fields = ('slug',)
        use_transactions = True
        clean_model_instances = True
