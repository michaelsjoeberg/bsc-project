$(document).ready(function() {
  /* remove ripple effect on elements */
  $('.no-ripple').off().data('plugin_ripples', null);

  /* keep ticker variable in modal window */
  $(document).on("click", ".data-remove", function () {
    var ticker = $(this).data('ticker');
    var name = $(this).data('name');
    $(".modal-body #formRemoveTicker").val(ticker);
    $(".modal-body #ticker").text(ticker);
    $(".modal-body #name").text(name);
  });

  /* company details modal */
  $(document).on("click", ".data-company", function () {
    var ticker = $(this).data('ticker');
    var name = $(this).data('name');
    var sector = $(this).data('sector');
    var industry = $(this).data('industry');
    var website = $(this).data('website');
    var description = $(this).data('description');
    var ceo = $(this).data('ceo');
    $(".modal-body #ticker").text(ticker);
    $(".modal-body #name").text(name);
    $(".modal-body #sector").text(sector);
    $(".modal-body #industry").text(industry);
    $(".modal-body #website").text(website);
    $(".modal-body #website_link").attr('href', website);
    $(".modal-body #description").text(description);
    $(".modal-body #ceo").text(ceo);
  });

  /* datatables config */
  var dataColumnValues = {
    "ticker": 0,
    "company": 1,
    "price": 2,
    "market_cap": 3,
    "change_day": 4,
    "change_ytd": 5,
    "shares": 6,
    "allocation": 7,
    "value": 8,
    "cost": 9,
    "change": 10
  };

  // set default visability setting if local storage is null
  // if (localStorage.getItem('hiddenColumns') == null) {
  //     localStorage.setItem('hiddenColumns', 'shares,allocation,value,cost,change');
  // }
  if (sessionStorage.getItem('hiddenColumns') == null) {
    sessionStorage.setItem('hiddenColumns', 'shares,allocation,value,cost,change');
  }
  // get column names as array
  // var hiddenColumns = localStorage.getItem('hiddenColumns').split(',');
  var hiddenColumns = sessionStorage.getItem('hiddenColumns').split(',');

  // create empty array for datatables plugin (need to be column indexes)
  var dt_columns = []

  // iterate each column button to add or remove active styling
  $('#data-columns').find('a').each(function(){
    var dt_column = $(this).attr('data-column')
    if (hiddenColumns.includes(dt_column)) { 
      // hide column if column name in local storage
      dt_columns.push(dataColumnValues[dt_column])
      $(this).removeClass('active')
    } else {
      $(this).addClass('active')
    }
  });

  // set default hidden columns in local storage
  var table = $('#tableStocks').DataTable({
    //scrollY       : true,
    scrollX         : true,
    columnDefs      : [{"orderable": false, "targets": "no-sort"},{ "visible": false, "targets": dt_columns}],
    order           : [[0, 'asc']],
    language        : {"search": "", "emptyTable": "You have not added any stocks yet", "zeroRecords": ""},
    paging          : false,
    bInfo           : false,
    dom             : '<"top">rt<"bottom">lpB<"clear">'
  });
  $('.dataTables_filter input[type="search"]').attr('placeholder','Search').css({'font-size':'1rem'});

  // toggle button style and visability
  $('a.toggle-vis').on('click', function (e) {
    e.preventDefault();

    // add or remove active class
    if ($(this).hasClass('active')) {
      $(this).removeClass('active');
    }
    else {
      $(this).addClass('active');
    }
    
    // get the column API object
    var dt_column = $(this).attr('data-column')
    var column = table.column(dataColumnValues[dt_column]);

    // add or remove from local storage
    if (hiddenColumns.includes(dt_column)) {
      var index = hiddenColumns.indexOf(dt_column);
      hiddenColumns.splice(index, 1);
    } else {
      hiddenColumns.push(dt_column)
    }
    // localStorage['hiddenColumns'] = hiddenColumns
    sessionStorage['hiddenColumns'] = hiddenColumns
    
    // toggle the visibility
    column.visible(!column.visible());
  });

  table_test = $('#tableStocks').DataTable();
  $('#mainTableSearch').keyup(function(){
    table_test.search($(this).val()).draw() ;
  })

  /* display selected file name before uploading */
  $(document).on('change', ':file', function() {
    var input = $(this),
      numFiles = input.get(0).files ? input.get(0).files.length : 1,
      label = input.val().replace(/\\/g, '/').replace(/.*\//, '');
    input.trigger('fileselect', [numFiles, label]);
  });
  $(':file').on('fileselect', function(event, numFiles, label) {
    var input = $(this).parents('.input-group').find(':text'),
      log = numFiles > 1 ? numFiles + ' files selected' : label;

    if( input.length ) {
      input.val(log);
      
    } else {
      if (log) alert(log);
    }
  });
});