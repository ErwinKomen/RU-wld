from django.views.generic.list import ListView
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.core.exceptions import PermissionDenied

import operator
import re

from wld.dictionary.models import *
from wld.dictionary.forms import *
from wld.settings import APP_PREFIX, MEDIA_ROOT
from wld.dictionary.views import paginateSize, paginateValues

def order_queryset_by_sort_order(get, qs):
    """Change the sort-order of the query set, depending on the form field [sortOrder]

    This function is used by EntryListView.
    The value of [sortOrder] is 'woord' by default.
    [sortOrder] is a hidden field inside the "adminsearch" html form in the template admin_gloss_list.html
    Its value is changed by clicking the up/down buttons in the second row of the search result table
    """

    def get_string_from_tuple_list(lstTuples, number):
        """Get the string value corresponding to a number in a list of number-string tuples"""
        sBack = [tup[1] for tup in lstTuples if tup[0] == number]
        return sBack

    # Helper: order a queryset on field [sOrder], which is a number from a list of tuples named [sListName]
    def order_queryset_by_tuple_list(qs, sOrder, sListName):
        """Order a queryset on field [sOrder], which is a number from a list of tuples named [sListName]"""

        # Get a list of tuples for this sort-order
        tpList = build_choice_list(sListName)
        # Determine sort order: ascending is default
        bReversed = False
        if (sOrder[0:1] == '-'):
            # A starting '-' sign means: descending order
            sOrder = sOrder[1:]
            bReversed = True

        # Order the list of tuples alphabetically
        # (NOTE: they are alphabetical from 'build_choice_list()', except for the values 0,1)
        tpList = sorted(tpList, key=operator.itemgetter(1))
        # Order by the string-values in the tuple list
        return sorted(qs, key=lambda x: get_string_from_tuple_list(tpList, getattr(x, sOrder)), reverse=bReversed)

    # Set the default sort order
    sOrder = 'woord'  # Default sort order if nothing is specified
    # See if the form contains any sort-order information
    if ('sortOrder' in get and get['sortOrder'] != ''):
        # Take the user-indicated sort order
        sOrder = get['sortOrder']

    # The ordering method depends on the kind of field:
    # (1) text fields are ordered straightforwardly
    # (2) fields made from a choice_list need special treatment
    if (sOrder.endswith('handedness')):
        ordered = order_queryset_by_tuple_list(qs, sOrder, "Handedness")
    elif (sOrder.endswith('domhndsh') or sOrder.endswith('subhndsh')):
        ordered = order_queryset_by_tuple_list(qs, sOrder, "Handshape")
    elif (sOrder.endswith('locprim')):
        ordered = order_queryset_by_tuple_list(qs, sOrder, "Location")
    else:
        # Use straightforward ordering on field [sOrder]
        ordered = qs.order_by(sOrder)

    # return the ordered list
    return ordered

class EntryListView(ListView):
    
    model = Entry
    template_name = 'dictionary/admin_entry_list.html'
    paginate_by = paginateSize

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(EntryListView, self).get_context_data(**kwargs)

        # Get parameters for the search
        initial = self.request.GET
        search_form = EntrySearchForm(initial)

        context['searchform'] = search_form

        # Determine the count 
        context['entrycount'] = self.get_queryset().count()

        # Make sure the paginate-values are available
        context['paginateValues'] = paginateValues

        if 'paginate_by' in initial:
            context['paginateSize'] = int(initial['paginate_by'])
        else:
            context['paginateSize'] = paginateSize

        # Set the prefix
        context['app_prefix'] = APP_PREFIX

        # Return the calculated context
        return context

    def get_paginate_by(self, queryset):
        """
        Paginate by specified value in querystring, or use default class property value.
        """
        return self.request.GET.get('paginate_by', self.paginate_by)
        
    def get_queryset(self):

        # Get the parameters passed on with the GET request
        get = self.request.GET

        # Queryset: start out with *ALL* the entries
        qs = Entry.objects.all()

        # Fine-tuning: search string
        if 'search' in get and get['search'] != '':
            val = get['search']
            query = Q(woord__istartswith=val) 

            # check for possible exact numbers having been given
            if re.match('^\d+$', val):
                query = query | Q(sn__exact=val)

            # Apply the filter
            qs = qs.filter(query)

        # Check for dialect city
        if 'dialectCity' in get and get['dialectCity'] != '':
            val = adapt_search(get['dialectCity'])
            # query = Q(entry__dialect__stad__istartswith=val)
            query = Q(entry__dialect__stad__iregex=val)
            qs = qs.filter(query)

        # Check for dialect code (Kloeke)
        if 'dialectCode' in get and get['dialectCode'] != '':
            val = adapt_search(get['dialectCode'])
            # query = Q(entry__dialect__code__istartswith=val)
            query = Q(entry__dialect__code__iregex=val)
            qs = qs.filter(query)

        # Check for lemma
        if 'lemma' in get and get['lemma'] != '':
            val = get['lemma']
            query = Q(lemma__gloss__istartswith=val)
            qs = qs.filter(query)

        # Make sure we only have distinct values
        qs = qs.distinct()

        # Sort the queryset by the parameters given
        qs = order_queryset_by_sort_order(self.request.GET, qs)

        # Return the resulting filtered and sorted queryset
        return qs


class InfoListView(ListView):

    model = Info
    template_name = 'dictionary/admin_info_list.html'



