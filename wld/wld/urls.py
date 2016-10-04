"""
Definition of urls for wld.
"""

from datetime import datetime
from django.contrib.auth.decorators import login_required, permission_required
from django.conf.urls import url
from django.core import urlresolvers
import django.contrib.auth.views
# Enable the admin:
from django.conf.urls import include
from django.shortcuts import redirect
from django.core.urlresolvers import reverse, reverse_lazy
from django.views.generic.base import RedirectView
from django.contrib import admin
from wld.settings import APP_PREFIX
admin.autodiscover()

# Imports for my own project
import wld.dictionary.forms
from wld.dictionary.views import *
from wld.dictionary.adminviews import EntryListView


# set admin site names
admin.site.site_header = 'RU-eWLD Admin'
admin.site.site_title = 'RU-eWLD Site Admin'

pfx = APP_PREFIX

urlpatterns = [
    # Examples:
    url(r'^$', wld.dictionary.views.home, name='home'),
    url(r'^contact$', wld.dictionary.views.contact, name='contact'),
    url(r'^about', wld.dictionary.views.about, name='about'),
    url(r'^definitions$', RedirectView.as_view(url='/'+pfx+'admin/'), name='definitions'),
    url(r'^entries$', RedirectView.as_view(url='/'+pfx+'admin/dictionary/entry/'), name='entries'),
    url(r'^lemmas$', LemmaListView.as_view(), name='lemmas'),
    url(r'^list/$', permission_required('dictionary.search_gloss')(EntryListView.as_view()), name='admin_entry_list'), 
    url(r'^dictionary/search/$', permission_required('dictionary.search_gloss')(EntryListView.as_view())),
    url(r'^entry/(?P<pk>\d+)', DictionaryDetailView.as_view(), name='output'),

    url(r'^login/$',
        django.contrib.auth.views.login,
        {
            'template_name': 'dictionary/login.html',
            'authentication_form': wld.dictionary.forms.BootstrapAuthenticationForm,
            'extra_context':
            {
                'title': 'Log in',
                'year': datetime.now().year,
            }
        },
        name='login'),
    url(r'^logout$',
        django.contrib.auth.views.logout,
        {
            'next_page': reverse_lazy('home'),
        },
        name='logout'),

    # Uncomment the admin/doc line below to enable admin documentation:
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls), name='admin_base'),
]
