(function() {

// dynamically adding a form to a Django formset
// ref: https://stackoverflow.com/questions/501719/dynamically-adding-a-form-to-a-django-formset

function updateElementIndex(el, ndx) {
    // re-index the row form element
    var id_regex = new RegExp('(form-\\d+)');
    var replacement = 'form-' + ndx;
    if ($(el).attr("for")) $(el).attr("for", $(el).attr("for").replace(id_regex, replacement));
    if (el.id) el.id = el.id.replace(id_regex, replacement);
    if (el.name) el.name = el.name.replace(id_regex, replacement);
}

function cloneMore(selector) {
    // add one empty row to the funding form table
    var newElement = $(selector).clone(true);
    var total = $('#id_form-TOTAL_FORMS').val();
    newElement.find(':input:not([type=button]):not([type=submit]):not([type=reset])').each(function() {
        var name = $(this).attr('name').replace('-' + (total-1) + '-', '-' + total + '-');
        var id = 'id_' + name;
        $(this).attr({'name': name, 'id': id}).val('').removeAttr('checked');
    });
    total++;
    $('#id_form-TOTAL_FORMS').val(total);
    $(selector).after(newElement);
    var conditionRow = $('.funding-form-row:not(:last)');
    conditionRow.find('.btn.add-funding-form-row')
    .removeClass('btn-success').addClass('btn-danger')
    .removeClass('add-funding-form-row').addClass('remove-funding-form-row')
    .html('<span class="glyphicon glyphicon-trash" aria-hidden="true"></span>');
}

function deleteForm(btn) {
    // delete the selected row from the funding form table
    var total = parseInt($('#id_form-TOTAL_FORMS').val());
    if (total > 1){
        btn.closest('.funding-form-row').remove();
        var forms = $('.funding-form-row');
        $('#id_form-TOTAL_FORMS').val(forms.length);
        for (var i=0, formCount=forms.length; i<formCount; i++) {
            $(forms.get(i)).find(':input').each(function() {
                updateElementIndex(this, i);
            });
        }
    }
}

$(document).on('click', '.add-funding-form-row', function(e){
    e.preventDefault();
    cloneMore('.funding-form-row:last');
});

$(document).on('click', '.remove-funding-form-row', function(e){
    e.preventDefault();
    deleteForm($(this));
});

})()
