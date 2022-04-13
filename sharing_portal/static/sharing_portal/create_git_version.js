(function() {
  document.addEventListener('DOMContentLoaded', () => {
    const gitRemoteInput = document.getElementById('gitRemote');
    const gitRefDropdown = document.getElementById('gitRef');

    function onRemoteChange(e) {
      let remote_url = e.target.value
      fetch(`/experiment/share/api/git/?remote_url=${encodeURIComponent(remote_url)}`)
        .then(res => res.json())
        .then(res => {
          gitRefDropdown.innerHTML = '';
          let array = res["result"]
          if(array.length > 0){
            for (var i = 0; i < array.length; i++) {
              var option = document.createElement("option");
              option.value = array[i][0];
              option.text = array[i][1];
              gitRefDropdown.appendChild(option);
            }
            gitRefDropdown.disabled = false
          } else {
            var option = document.createElement("option");
            option.text = "Please enter a valid git remote";
            gitRefDropdown.appendChild(option);
          }
        })
    }

    if (gitRemoteInput && gitRefDropdown) {
      gitRefDropdown.disabled = true
      gitRemoteInput.addEventListener('keyup', onRemoteChange);
    }

  });
})();
