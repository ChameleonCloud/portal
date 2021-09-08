function resetRole(selectorId) {
  var selector = document.getElementById(selectorId);
  selector.value = selector.dataset.initial;
  selector.disabled = true;
  document.getElementById("submit_" + selectorId).style.display = "none";
  document.getElementById("cancel_" + selectorId).style.display = "none";
}

function enableChangeRole(userId) {
  var elemId = "role_" + userId;
  var selectors = document.getElementsByClassName("role_selector");
  for (var i = 0; i < selectors.length; i++) {
    var selector = selectors[i];
    if (selector.id == elemId) {
      selector.disabled = false;
      document.getElementById("submit_" + selector.id).style.display = "";
      document.getElementById("cancel_" + selector.id).style.display = "";
    } else {
      resetRole(selector.id);
    }
  }
}
