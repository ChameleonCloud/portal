/* When the user clicks on the button, 
toggle between hiding and showing the dropdown content */
function dropdown() {
  var x = document.getElementById("id_labels");
  
  if (x.style.display == "none") {
    console.log("showing");
    x.style.display = "block";
  } else {
    console.log("hiding");
    x.style.display = "none";
  }
}

// Close the dropdown menu if the user clicks outside of it
/*
window.onclick = function(event) {
  if (!event.target.matches('.dropbtn')) {
    var dropdowns = document.getElementsByClassName("dropdown-content");
    var i;
    for (i = 0; i < dropdowns.length; i++) {
      var openDropdown = dropdowns[i];
      if (openDropdown.classList.contains('show')) {
        openDropdown.classList.remove('show');
      }
    }
  }
}
*/
