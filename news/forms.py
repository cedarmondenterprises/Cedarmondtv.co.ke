from django import forms
from .models import ReaderMessage
class SubscribeForm(forms.Form):
    email = forms.EmailField(max_length=254,widget=forms.EmailInput(attrs={'placeholder':'Your email address','autocomplete':'email'}))
    consent = forms.BooleanField(label='I agree to receive Cedarmond TV emails. I can unsubscribe anytime.')
    website = forms.CharField(required=False,widget=forms.HiddenInput)
class ContactForm(forms.ModelForm):
    SUBJECT_CHOICES = [
        ('Story tip', 'Story tip'),
        ('Correction', 'Correction'),
        ('Advertising enquiry', 'Advertising enquiry'),
        ('Privacy/data request', 'Privacy or data request'),
        ('General enquiry', 'General enquiry'),
    ]
    subject = forms.ChoiceField(choices=SUBJECT_CHOICES, widget=forms.Select())
    website = forms.CharField(required=False,widget=forms.HiddenInput)
    class Meta:
        model = ReaderMessage
        fields = ['name','email','subject','message']

class StoryCommentForm(forms.Form):
    display_name=forms.CharField(max_length=80,label='Name',widget=forms.TextInput(attrs={'autocomplete':'name','maxlength':'80'}))
    body=forms.CharField(max_length=2000,label='Comment',widget=forms.Textarea(attrs={'rows':5,'maxlength':'2000'}))
    consent=forms.BooleanField(label='I agree to the comment guidelines and understand my comment is reviewed before publication.')
    website=forms.CharField(required=False,widget=forms.HiddenInput)
