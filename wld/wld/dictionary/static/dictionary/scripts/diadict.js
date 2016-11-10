// var $ = django.jQuery.noConflict();

$(document).ready(function () {
  // Initialize Bootstrap popover
  // Note: this is used when hovering over the question mark button
  $('[data-toggle="popover"]').popover();
});

/**
 * Goal: initiate a lemma search
 * Source: http://www.javascript-coder.com/javascript-form/javascript-reset-form.phtml
 *
 * @param {string} sName - one of 'lemma', 'entry', 'trefwoord'
 * @returns {bool}
 */
function clearForm(sName) {

  var f = $("#"+sName+"search").get(0);
  var elements = f.elements;

  f.reset();

  for (i = 0; i < elements.length; i++) {

    field_type = elements[i].type.toLowerCase();

    switch (field_type) {

      case "text":
      case "password":
      case "textarea":
      case "hidden":

        elements[i].value = "";
        break;

      case "radio":
      case "checkbox":
        if (elements[i].checked) {
          elements[i].checked = false;
        }
        break;

      case "select-one":
      case "select-multiple":
        elements[i].selectedIndex = -1;
        break;

      default:
        break;
    }
  }
  return (false);
}

/**
 * Goal: initiate a sort
 *
 * @param {string} field_name - name of the field to sort on
 * @param {string} action     - one of: desc, asc, del
 * @param {string} frmName    - name of the <form ...> that contains the 'sortOrder' <input> field
 * @returns {void}
 */
function do_sort_column(field_name, action, frmName) {
  // Combine @field_name and @action into [sOrder]
  var sOrder = field_name;
  if (action == 'desc') {
    // Descending sort order is signified by a '-' prefix
    sOrder = '-' + sOrder;
  } else if (action == 'del') {
    // "Deleting" (pressing 'x') the sort order of a column means: return to the default 'woord' sort order
    sOrder = 'woord';
  }

  // Set the value of the [sortOrder] field defined in dictionary/forms.py::EntrySearchForm
  $("#" + frmName + " input[name='sortOrder']").val(sOrder);

  // Submit the form with the indicated name
  $("#" + frmName).submit();
}

/**
 * Goal: initiate a search
 *
 * @param {node}   el     - the calling node
 * @param {string} sName  - this can be 'lemma', 'trefwoord' or 'entry'
 * @param {string} sType  - when 'Herstel', then 
 * @returns {bool}
 */
function do_search(el, sName, sType) {
  var sSearch = 'search';

  // Check if this is resetting
  if (sType === 'Herstel')
    return clearForm(sName);
  if (sType === 'Csv')
    sSearch = 'csv';
  var f = $("#" + sName + "search");
  var sSearchType = $(el).attr('value');
  var url_prefix = $(".container").attr("url_home");
  var sPath = url_prefix;
  switch (sName) {
    case "admin":
      sPath += "dictionary/"+sSearch+"/";
      break;
    default:
      sPath += sName + "/" + sSearch + "/";
      break;
  }
  f.attr('action', sPath);
  // Set the submit type
  $("#submit_type").attr('value', sType);
  document.getElementById(sName+'search').submit();

  // Make sure we return positively
  return true;
}

/**
 * Goal: change dialect choice
 * @returns {bool}
 */
function do_dialect(el) {
  // Get the value of this option
  var sOptVal = $(el).attr('value');
  // Adapt hidden elements
  switch (sOptVal) {
    case 'code':
      $(".lemma-word-dialect-code").removeClass("hidden");
      $(".lemma-word-dialect-space").addClass("hidden");
      $(".lemma-word-dialect-stad").addClass("hidden");
      break;
    case 'stad':
      $(".lemma-word-dialect-code").addClass("hidden");
      $(".lemma-word-dialect-space").addClass("hidden");
      $(".lemma-word-dialect-stad").removeClass("hidden");
      break;
    case 'alles':
      $(".lemma-word-dialect-code").removeClass("hidden");
      $(".lemma-word-dialect-stad").removeClass("hidden");
      $(".lemma-word-dialect-space").removeClass("hidden");
      break;
  }

  // Make sure we return positively
  return true;
}

