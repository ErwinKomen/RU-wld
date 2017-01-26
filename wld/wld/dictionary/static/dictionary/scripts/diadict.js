// var $ = django.jQuery.noConflict();

$(document).ready(function () {
  // Initialize Bootstrap popover
  // Note: this is used when hovering over the question mark button
  $('[data-toggle="popover"]').popover();
});

var oProgressTimer = null;

// GOOGLE TRACKING STATISTICS
(function (i, s, o, g, r, a, m) {
  i['GoogleAnalyticsObject'] = r; i[r] = i[r] || function () {
    (i[r].q = i[r].q || []).push(arguments)
  }, i[r].l = 1 * new Date(); a = s.createElement(o),
  m = s.getElementsByTagName(o)[0]; a.async = 1; a.src = g; m.parentNode.insertBefore(a, m)
})(window, document, 'script', 'https://www.google-analytics.com/analytics.js', 'ga');

ga('create', 'UA-90924826-1', 'auto');
ga('send', 'pageview');
// ==================================

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

  var elements = $("#" + sName + "search .form-control");

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
  /*
  if (sType === 'Csv')
    sSearch = 'csv';
    */
  var f = $("#" + sName + "search");
  // var sSearchType = $(el).attr('value');
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

function repair_start(sRepairType) {
  // Indicate that we are starting
  $("#repair_progress_" + sRepairType).html("Repair is starting: "+sRepairType);
  // Start looking only after some time
  var oJson = { 'status': 'started' };
  oRepairTimer = window.setTimeout(function () { repair_progress(sRepairType, oJson); }, 3000);

  // Make sure that at the end: we stop
  var oData = { 'type': sRepairType };
  sUrl = $("#repair_start_"+sRepairType).attr('repair-start');
  $.ajax({
    "url": sUrl,
    "dataType": "json",
    "data": oData,
    "cache": false,
    "success": function () { repair_stop(); }
  })(jQuery);
}

function repair_progress(sRepairType) {

  var oData = { 'type': sRepairType };
  sUrl = $("#repair_start_" + sRepairType).attr('repair-progress');
  $.ajax({
    "url": sUrl,
    "dataType": "json",
    "data": oData,
    "cache": false,
    "success": function (json) {
      repair_handle(sRepairType, json); }
  })(jQuery);
}

function repair_handle(sRepairType, json) {
  // Action depends on the status in [json]
  switch (json.status) {
    case 'error':
      // Show we are ready
      $("#repair_progress_" + sRepairType).html("Error repairing: " + sRepairType);
      // Stop the progress calling
      window.clearInterval(oRepairTimer);
      // Leave the routine, and don't return anymore
      return;
    default:
      // Default action is to show the status
      $("#repair_progress_" + sRepairType).html(json.status);
      oRepairTimer = window.setTimeout(function (json) { repair_progress(sRepairType); }, 1000);
      break;
  }
}

function repair_stop(sRepairType) {
  // Show we are ready
  $("#repair_progress_" + sRepairType).html("Finished repair: " + sRepairType);

  // Stop the progress calling
  window.clearInterval(oRepairTimer);
}

function import_start(bUseDbase) {
  // Retrieve the values Deel/Sectie/AflNum
  var sDeel = $("#id_deel").val();
  var sSectie = $("#id_sectie").val();
  var sAflnum = $("#id_aflnum").val();
  // Get the value of the CSV file
  var sCsvFile = $("#id_csv_file").val();
  if (sCsvFile === undefined || sCsvFile === "") {
    sCsvFile = $("#id_csv_file").parent().find('a').text();
  }
  if (sCsvFile === undefined || sCsvFile === "") {
    // It is no use to start--
    var sMsg = "Eerst dit record opslaan (SAVE) en dan hiernaartoe terugkeren";
    $("#info_progress").html(sMsg);
    $("#info_button").addClass("hidden");
    $("#info_button2").addClass("hidden");
    return;
  } else {
    $("#info_progress").html("Please wait...");
  }
  // Start looking only after some time
  oProgressTimer = window.setTimeout(progress_request, 3000);
  // Start reading this file
  sUrl = $("#info_button").attr('import-start');
  var oData = {
    'deel': sDeel, 'sectie': sSectie,
    'aflnum': sAflnum, 'filename': sCsvFile,
    'usedbase': bUseDbase
  };
  $.ajax({
    "url": sUrl,
    "dataType": "json",
    "data": oData,
    "cache": false,
    "success": function () { progress_stop(); }
  })(jQuery);
}

function progress_request() {
  // Prepare an AJAX call to ask for the progress
  sUrl = $("#info_button").attr('import-progress');
  // Retrieve the values Deel/Sectie/AflNum
  var sDeel = $("#id_deel").val();
  var sSectie = $("#id_sectie").val();
  var sAflnum = $("#id_aflnum").val();
  // Prepare these values for the request
  var oData = {
    'deel': sDeel, 'sectie': sSectie,
    'aflnum': sAflnum
  };
  $.ajax({
    "url": sUrl,
    "dataType": "json",
    "data": oData,
    "cache": false,
    "success": function (json) { progress_handle(json); }
  })(jQuery);
}

function progress_handle(json) {
  // Handle the progress report
  var sStatus = json.status;
  var iRead = json.read;
  var iSkipped = json.skipped;
  var sProgress = "";
  var sMsg = json.msg;
  var sMethod = json.method;
  // Deal with error
  if (sStatus === "error") {
    // Stop the progress calling
    // window.clearInterval(oProgressTimer);
    sProgress = "An error has occurred - stopped";
  } else {
    if (sMsg === undefined || sMsg === "") {
      sProgress = sStatus + " " + sMethod + " (read=" + iRead + ", skipped=" + iSkipped + ")";
    } else {
      sProgress = sStatus + " " + sMethod + " (read=" + iRead + ", skipped=" + iSkipped + "): " + sMsg;
    }
    if (iRead > 0 || iSkipped > 0) {
      $("#id_read").val(iRead);
      $("#id_skipped").val(iSkipped);
    }
  }
  if (sStatus !== "idle") {
    $("#info_progress").html(sProgress);
  }
  switch (sStatus) {
    case "error":
      break;
    case "done":
      progress_stop();
      break;
    case "idle":
      // Make an additional request but wait longer
      oProgressTimer = window.setTimeout(progress_request, 5000);
      break;
    default:
      // Make an additional request in 1 second
      oProgressTimer = window.setTimeout(progress_request, 1000);
      break;
  }

}

function progress_stop() {
  var currentdate = new Date();
  var sDateString = currentdate.getDate() + "/"
                + (currentdate.getMonth() + 1) + "/"
                + currentdate.getFullYear() + " @ "
                + currentdate.getHours() + ":"
                + currentdate.getMinutes() + ":"
                + currentdate.getSeconds();
  var sMsg = "Processed on: " + sDateString;
  $("#id_processed").val(sMsg);
  $("#info_progress").html("The conversion is completely ready");
  // Stop the progress calling
  window.clearInterval(oProgressTimer);
}

function set_search(sId) {
  var lSearchId = ['lemmasearch', 'locationsearch', 'trefwoordsearch'];
  for (i = 0; i < lSearchId.length; i++) {
    $("#top" + lSearchId[i]).addClass("hidden");
  }
  $("#top" + sId).removeClass("hidden");
}