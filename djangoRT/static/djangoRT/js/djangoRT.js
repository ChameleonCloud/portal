(function($) {
	$(document).ready(function() {
		var show = $('#select option:selected').val();
		if (show === 'all') {
			$('.tickets').removeClass('none');
		} else {
			$('.tickets.' + show).removeClass('none');
		}

		$('#select').on('change', function() {
			show = $('#select option:selected').val();

			if ($(this).val() != "all") {
				$('.tickets').addClass('none');
				$('.tickets.' + show).removeClass('none');

				if ($('.tickets.' + show + ' .ticket').length == 0) {
					$('.empty').removeClass('none');
				} else {
					$('.empty').addClass('none');
				}
			} else {
				$('.tickets').removeClass('none');

				if ($('.tickets .ticket').length == 0) {
					$('.empty').removeClass('none');
				} else {
					$('.empty').addClass('none');
				}
			}

		});

		$(".search").keyup( function() {
			var searchTerms = $(this).val();
			// console.log(searchTerms);
			// console.log(show);
			if (searchTerms != "") {
				$(".ticket").filter( function() {
					return !$(this).is(":contains('" + searchTerms + "')");
				}).addClass("none");

				$(".ticket").filter( function() {
					return $(this).is(":contains('" + searchTerms + "')");
				}).removeClass("none");
			} else {
				$(".ticket").removeClass("none");
			}
		});

	});
})(jQuery);
