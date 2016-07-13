'use strict';
(function( window, $, undefined ) {
    $('button[name="allocation-display-toggle"]').on('click', function(e) {
      e.preventDefault();
      $('.allocation').toggleClass('show');
    });

    if ($('.allocation-active').length != 0 || $('.allocation-pending').length != 0) {
            $('.allocation-rejected').toggleClass('hide');
    }

    // initialize the chart
    $('#usageChart').highcharts({
                options: {
                    chart: {
                        type: 'column'
                    },
                    xAxis: {
                        categories: []
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
                },
                title: {
                    text: ''
                },
                series: [],
                useHighstocks: true,
       });

       var chart=Highcharts.charts[0];
       var start =  $('#usageChart').attr('start');
       var end = $('#usageChart').attr('end');
          $.ajax({
            method: 'GET',
            dataType: "json",
            url: '/admin/usage/usage-by-users/' + $('#usageChart').attr('allocation-id') +'/?from=' + start + '&to=' + end,
            cache: 'true'
           }).done(function(response) {
            chart.series = [];
            chart.options.xAxis.categories = [];
            // we're initializing all the queues ahead of time since we know what the are, and that will simplify the logic below
            var data = {};
            data['kvm@tacc'] = [];
            data['kvm@uc'] = [];
            data['chi@tacc'] = [];
            data['chi@uc'] = [];
            // response data:
            // Object{ username = Object{ resource1 = total_usage, resource2 = total_usage }, username2 = Object{ resource2 = total_usage, resource3 = total_usage } }
            for (var key in response) {
              // push the username as an xAxis key
              chart.options.xAxis.categories.push(key)

              // for each xAxis key, set the usage per resource for every username
                if ('kvm@tacc' in response[key]) {
                  data['kvm@tacc'].push(response[key]['kvm@tacc']);
                } else {
                  data['kvm@tacc'].push(0);
                }

                if ('kvm@uc' in response[key]) {
                  data['kvm@uc'].push(response[key]['kvm@uc']);
                } else {
                  data['kvm@uc'].push(0);
                }

                 if ('CHI@TACC' in response[key]) {
                    data['chi@tacc'].push(response[key]['CHI@TACC']);
                } else {
                  data['chi@tacc'].push(0);
                }

                 if ('CHI@UC' in response[key]) {
                  data['chi@uc'].push(response[key]['CHI@UC']);
                } else {
                  data['chi@uc'].push(0);
                }
              }

              // after the data has been aggregated, set the chart series
              chart.series.push({
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
           });
})( this, $ );
