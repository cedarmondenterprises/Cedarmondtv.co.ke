from django import forms
from .models import ReaderMessage
class SubscribeForm(forms.Form):
    email = forms.EmailField(max_length=254,widget=forms.EmailInput(attrs={'placeholder':'Your email address','autocomplete':'email'}))
    consent = forms.BooleanField(label='I agree to receive Cedarmond TV emails. I can unsubscribe anytime.')
    website = forms.CharField(required=False,widget=forms.HiddenInput)
class ContactForm(forms.ModelForm):
    website = forms.CharField(required=False,widget=forms.HiddenInput)
    class Meta:
        model = ReaderMessage
        fields = ['name','email','subject','message']
