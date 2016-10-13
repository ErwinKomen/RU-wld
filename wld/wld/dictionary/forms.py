"""
Definition of forms.
"""

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import ugettext_lazy as _
from wld.dictionary.models import Entry, Lemma

DIALECT_CHOICES = (
        ('code', 'Nieuwe Kloekecode'),
        ('stad', 'Plaats'),
        ('alles', 'Plaats en code'),
    )

class BootstrapAuthenticationForm(AuthenticationForm):
    """Authentication form which uses boostrap CSS."""
    username = forms.CharField(max_length=254,
                               widget=forms.TextInput({
                                   'class': 'form-control',
                                   'placeholder': 'User name'}))
    password = forms.CharField(label=_("Password"),
                               widget=forms.PasswordInput({
                                   'class': 'form-control',
                                   'placeholder':'Password'}))

class EntrySearchForm(forms.ModelForm):

    search = forms.CharField(label=_("Woord in het dialect"))
    sortOrder = forms.CharField(label=_("Sort Order"), initial="woord")
    lemma = forms.CharField(label=_("Lemma"))
    dialectCode = forms.CharField(label=_("Kloeke code"))
    dialectCity = forms.CharField(label=_("Stad"))

    class Meta:

        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = Entry
        fields = ('lemma', 'dialect', 'trefwoord', 'woord')


class LemmaSearchForm(forms.ModelForm):

    search = forms.CharField(label=_("Begrip"))
    sortOrder = forms.CharField(label=_("Sort Order"), initial="lemma")
    woord = forms.CharField(label=_("Dialectopgave"))
    dialectCode = forms.CharField(label=_("Kloeke code"))
    dialectCity = forms.CharField(label=_("Stad"))
    bronnen = forms.CharField(label=_("Bronnen"))
    #optdialect = forms.MultipleChoiceField(label=_("Dialectweergave"), 
    #                                       choices=DIALECT_CHOICES)
    optdialect = forms.CharField(label=_("Dialectweergave"))
    #optdialect = forms.CharField(label=_("Dialectweergave"), 
    #                            widget=forms.Select(choices=DIALECT_CHOICES),
    #                            initial='stad')

    class Meta:

        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = Lemma
        fields = ('gloss', 'toelichting', 'bronnenlijst', 'optdialect')

    #def clean_optdialect(self):
    #    optdialect = self.cleaned_data['optdialect']
    #    if optdialect is None:
    #        return self.fields['optdialect'].initial
    #    return optdialect
