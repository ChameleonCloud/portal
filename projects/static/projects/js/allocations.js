'use strict';
(function( window, $, undefined ) {
    $('button[name="allocation-display-toggle"]').on('click', function(e) {
      e.preventDefault();
      if($('.allocation-inactive, .allocation-rejected').css('visibility') == 'collapse') {
        $('.allocation-inactive, .allocation-rejected').css('visibility', 'visible');
      } else {
        $('.allocation-inactive, .allocation-rejected').css('visibility', 'collapse');
      }
    });
    
    $(document).on("click", ".open-charge", function (e) {
      e.preventDefault();
      var $popup = $("#popup");
      var popup_url = $(this).data("charge-popup-url");
      $(".modal-body", $popup).load(popup_url, function () {
        $popup.modal("show");
      });
    });

    $('#icon_show_edit,#btn_cancel').on('click', function(e) {
        $('#project_nickname').toggleClass('hidden');
        $('#icon_show_edit').toggleClass('hidden');
        $('#project_edit_form').toggleClass('hidden');
      });

    $('#icon_show_type_edit,#btn_type_cancel').on('click', function(e) {
        $('#project_type').toggleClass('hidden');
        $('#icon_show_type_edit').toggleClass('hidden');
        $('#project_type_edit_form').toggleClass('hidden');
      });
      
    $('#icon_show_pi_edit,#btn_pi_cancel').on('click', function(e) {
        $('#project_pi').toggleClass('hidden');
        $('#icon_show_pi_edit').toggleClass('hidden');
        $('#project_pi_edit_form').toggleClass('hidden');
      });

       var start =  $('#usageChart').attr('start');
       var end = $('#usageChart').attr('end');
       var projectId = $('#usageChart').attr('project-id');
          $.ajax({
            method: 'GET',
            dataType: "json",
            url: '/admin/usage/usage-by-users/' + $('#usageChart').attr('allocation-id') +'/?from=' + start + '&to=' + end + '&projectId=' + projectId,
            cache: 'true'
           }).done(function(response) {
            // we're initializing all the queues ahead of time since we know what the are, and that will simplify the logic below
            var data = {};
            data['kvm@tacc'] = [];
            data['kvm@uc'] = [];
            data['chi@tacc'] = [];
            data['chi@uc'] = [];

            var seriesData = [];
            var categories = [];
            // response data:
            // Object{ username = Object{ resource1 = total_usage, resource2 = total_usage }, username2 = Object{ resource2 = total_usage, resource3 = total_usage } }
            for (var key in response) {
              // push the username as a category
              categories.push(key)

              // for each category key, set the usage per resource for every username
                if ('kvm@tacc' in response[key]) {
                  data['kvm@tacc'].push(Math.ceil(response[key]['kvm@tacc']));
                }

                if ('kvm@uc' in response[key]) {
                  data['kvm@uc'].push(Math.ceil(response[key]['kvm@uc']));
                }

                 if ('CHI@TACC' in response[key]) {
                    data['chi@tacc'].push(Math.ceil(response[key]['CHI@TACC']));
                }

                 if ('CHI@UC' in response[key]) {
                  data['chi@uc'].push(Math.ceil(response[key]['CHI@UC']));
                }
              }

              // after the data has been aggregated, set the chart series
              seriesData.push({
                  name: 'kvm@tacc',
                  data: data['kvm@tacc'],
                }, {
                  name: 'kvm@uc',
                  data: data['kvm@uc'],
                }, {
                  name: 'chi@tacc',
                  data: data['chi@tacc'],
                }, {
                  name: 'chi@uc',
                  data: data['chi@uc'],
              });

                  // initialize the chart
                $('#usageChart').highcharts({
                    chart: {
                        type: 'column'
                    },
                    xAxis: {
                        categories: categories
                    },
                    yAxis: {
                        min: 0,
                        title: {
                            text: 'Total SUs Used'
                        },
                        stackLabels: {
                            enabled: true,
                            style: {
                                fontWeight: 'bold',
                                color: 'gray'
                            }
                        }
                    },
                    legend: {
                        align: 'right',
                        x: -30,
                        verticalAlign: 'top',
                        y: 25,
                        floating: true,
                        backgroundColor: 'white',
                        borderColor: '#CCC',
                        borderWidth: 1,
                        shadow: false
                    },
                    plotOptions: {
                        column: {
                            stacking: 'normal',
                            dataLabels: {
                                enabled: true,
                                color: 'white',
                                style: {
                                    textShadow: '0 0 3px black'
                                }
                            }
                        }
                    },
                    tooltip: {
                        formatter: function() {
                            return '<b>' + this.x + '</b><br/>' +
                                this.series.name + ': ' + this.y + '<br/>' +
                                'Total: ' + this.point.stackTotal;
                        }
                    },
                    credits: {
                        enabled: false
                    },
                title: {
                    text: ''
                },
                series: seriesData,
                useHighstocks: true,
                });

           });

})( this, $ );
