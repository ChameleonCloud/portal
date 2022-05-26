// This data holds the set of questions to guide the user through.
// A question can have a description, a label, and a list of sub-questions.
// The label is shown to the user as something they can click on. When clicked,
// the description is shown.
let data = {
  "desc": "Which category fits your issue?",
  "questions": [
    {
      "label": "Reservations",
      "desc": "When submitting a ticket regarding reservations, please include the lease ID if possible.",
      "questions": [
        {
          "label": "Lease is missing resources",
          "desc": `If your lease is missing resources, then one of its nodes was
            detected as unhealthy. There was no replacement that could be
            found at the time. If you check the
            <a href="https://chameleoncloud.org/hardware/">availability calendar</a>
            for the site you are using, you may be able to create a second
            lease to make up for the missing resources.`,
        },
        {
          "label": "A node isn't working in my lease",
          "desc": `If a node in your lease is causing issues, you can try to create
            a second lease to make up the troublesome one. Please submit a
            ticket including the problematic lease ID, and if known, the
            ID of the node so that we can investigate the node.`,
        },
        {
          "label": "Creating a lease fails",
          "desc": `If your lease fails with a message saying "Not enough resources..."
                then either the resources matching your query are reserved (see the
                <a href="https://chameleoncloud.org/hardware/">availability calendar</a>
                to check) or your query doesn't match any resources, in which case
                double check that the resource type or ID you specify is correct.`
        },
        {
          "label": "I can't renew my lease",
          "desc": `Renewing a lease requires that it's resources are not reserved
                by others during the period you are renewing for. See the
                <a href="https://chameleoncloud.org/hardware/">availability calendar</a>
                to make sure your reserved resources are free. If they are not,
                you can create a
                <a href="https://chameleoncloud.readthedocs.io/en/latest/technical/images.html#the-cc-snapshot-utility">snapshot</a>
                of your image, and then relaunch it on a new lease.`
        },
      ],
    },
    {
      "label": "Instance Creation/Connectivity/Usage",
      "desc": "When submitting a ticket regarding instances, please include the instance ID if possible.",
      "questions": [
        {
          "label": "One of my nodes won't launch",
          "desc": `If you launch multiple nodes at the same time, sometimes the
            service may be overwhelmed. Try launching again, one node at a
            time for any failed nodes.`,
        },
        {
          "label": "The BIOS settings on my instance are incorrect",
          "desc": `If node functionality is not working as expected due to a
            BIOS setting, please submit a ticket letting us know.`
        }
      ]
    },
    {
      "label": "Jupyter/Trovi",
      "questions": [
        {
          "label": "Error 'The request you have made requires authentication'",
          "desc": `This error can appear if you are using the wrong project
            name. Make sure to update the project ID in the file you are
            running.`
        },
        {
          "label": "An artifact is not working as expected",
          "desc": `If an artifact isn't working, there may be a few causes. If
            the error message you are seeing is about "not enough resources",
            then the node type configured in the notebook. Check the
            <a href="https://chameleoncloud.org/hardware/">availability calendar</a>
            to see what nodes are free. For other issues, there may be an issue
            with the notebook's itself. In this case, please contact the author
            with specific questions.`,
        }
      ],
    },
    {
      "label": "Account Management",
      "questions": [
        {
          "label": "Linking/Migrating accounts",
          "desc": `For help migrating or linking accounts, please see our
            <a href="https://chameleoncloud.readthedocs.io/en/latest/user/federation/federation_migration.html">migration guide</a>.`
        }
      ],
    },
  ]
};

(function($, question_data) {
  function create_tree(parent_el, data_point){
    if(data_point.label){
      parent_el.append(`<summary>${data_point.label}</summary>`)
    }
    if(data_point.desc){
      parent_el.append(`<p>${data_point.desc}</p>`)
    }
    if(data_point.questions){
      data_point.questions.forEach(new_data_point => {
        let new_details = $("<details></details>")
        parent_el.append(new_details)
        create_tree(new_details, new_data_point)
      })
    }
  }
  create_tree($("#tree"), question_data)

  $("#expand_all").click(function(){
    $("details").attr("open","true")
  });
  $("#collapse_all").click(function(){
    $("details").removeAttr("open")
  });
})(jQuery, data);

