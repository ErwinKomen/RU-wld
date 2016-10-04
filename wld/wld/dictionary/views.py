"""
Definition of views.
"""

from django.views.generic.detail import DetailView
from django.shortcuts import get_object_or_404, render
from django.http import HttpRequest, HttpResponse
from django.template import RequestContext, loader
from datetime import datetime
from xml.dom import minidom
import xml.etree.ElementTree as ET
import os
from wld.dictionary.models import *
from wld.settings import APP_PREFIX, WSGI_FILE

# General help functions





def home(request):
    """Renders the home page."""
    assert isinstance(request, HttpRequest)
    return render(
        request,
        'dictionary/index.html',
        {
            'title':'RU-wld',
            'year':datetime.now().year,
        }
    )

def contact(request):
    """Renders the contact page."""
    assert isinstance(request, HttpRequest)
    return render(
        request,
        'dictionary/contact.html',
        {
            'title':'Contact',
            'message':'Henk van den Heuvel (H.vandenHeuvel@Let.ru.nl)',
            'year':datetime.now().year,
        }
    )

def about(request):
    """Renders the about page."""
    assert isinstance(request, HttpRequest)
    return render(
        request,
        'dictionary/about.html',
        {
            'title':'About',
            'message':'Radboud University Limburg Dialect Dictionary.',
            'year':datetime.now().year,
        }
    )

def overview(request):
    """Give an overview of the dictionary entries that have been entered"""

    overview_list = Entry.objects.order_by('woord')
    template = loader.get_template('dictionary/overview.html')
    context = {
        'overview_list': overview_list,
        'app_prefix': APP_PREFIX,
    }
    return HttpResponse(template.render(context, request))


def overzicht(request):
    """Give an overview of the dictionary entries that have been entered"""

    overzicht_lijst = Entry.objects.order_by('woord')
    template = loader.get_template('dictionary/overzicht.html')
    context = {
        'overview_list': overview_list,
        'app_prefix': APP_PREFIX,
    }
    return HttpResponse(template.render(context, request))


class DictionaryDetailView(DetailView):
    """Details of an entry from the dictionary"""

    model = Entry
    context_object_name = 'entry'