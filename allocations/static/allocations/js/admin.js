document.addEventListener('DOMContentLoaded', () => {
    // Opening/closing modal code
    const modal = document.getElementById("alloc-modal-approve");
    const modalReject = document.getElementById("alloc-modal-reject");
    const modalContact = document.getElementById("alloc-modal-contact");
    const closeButton = document.getElementById("close-btn");
    const approveBtn = document.getElementById("approve-btn");
    const rejectBtn = document.getElementById("reject-btn");
    const contactBtn = document.getElementById("contact-btn");
    const closeBtnReject = document.getElementById("close-btn-reject");
    const closeBtnContact = document.getElementById("close-btn-contact");
    approveBtn.addEventListener("click", function () {
        modal.style.display = "block";
    });
    rejectBtn.addEventListener("click", function () {
        modalReject.style.display = "block";
    });
    contactBtn.addEventListener("click", function () {
        modalContact.style.display = "block";
    });
    closeButton.addEventListener("click", function () {
        modal.style.display = "none";
    });
    closeBtnReject.addEventListener("click", function () {
        modalReject.style.display = "none";
    });
    closeBtnContact.addEventListener("click", function () {
        modalContact.style.display = "none";
    });
    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = "none";
        }
        if (event.target == modalContact) { 
            modalContact.style.display = "none"
        }
        if (event.target == modalReject) {
            modalReject.style.display = "none";
        }
    }      

    // Setting defaults on form
    const inputStartDate = document.getElementById("alloc-start-date");
    const today = new Date();
    inputStartDate.value = today.toISOString().split('T')[0];

    const inputEndDate = document.getElementById("alloc-end-date");
    const sixMonthsLater = new Date();
    sixMonthsLater.setMonth((today.getMonth() + 6) % 12);
    sixMonthsLater.setFullYear(today.getFullYear() + ((today.getMonth() + 6) >= 12 ? 1 : 0));
    if (sixMonthsLater.getDate() !== today.getDate()) {
        sixMonthsLater.setDate(0); // Set to the last day of the previous month
    }
    inputEndDate.value = sixMonthsLater.toISOString().split('T')[0];

    // Handling for prefilled responses
    const decisionSummary = document.getElementById("idDecisionSummary")
    function updateDecisionSummary() {
        const selectedType = typeSelect.value;
        if (selectedType == 'new') {
            decisionSummary.value=allocationNewApproval;
        } else if (selectedType == 'renewal') {
            decisionSummary.value=allocationRenewalApproval;
        } else if (selectedType == 'recharge') {
            decisionSummary.value=allocationRechargeApproval;
        } else {
            decisionSummary.value="";
        }
    }
    const typeSelect = document.getElementById("allocationApprovalType")
    typeSelect.addEventListener("change", updateDecisionSummary);

    function formatErrors(errors) {
        return Object.entries(errors)
            .map(([field, message]) => `- ${field.charAt(0).toUpperCase() + field.slice(1)}: ${message}`)
            .join("\n");
    }    

    // Submitting approval
    const approveSubmitBtn = document.getElementById("approve-submit-btn");
    approveSubmitBtn.addEventListener("click", function () {
        let payload = {
            "status": "approved",
            "dateReviewed": new Date().toISOString().split("T")[0],
            "start": inputStartDate.value,
            "end": inputEndDate.value,
            "decisionSummary": document.getElementById("idDecisionSummary").value,
            "computeAllocated": parseInt(document.getElementById("alloc-compute-allocated").value),
            "project": document.getElementById("chargeCode").value,
            "requestorId": document.getElementById("requestorId").value,
            "id": document.getElementById("allocationId").value,
        }
        fetch("/admin/allocations/approval/", {
            method: "POST",
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded',
                "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value,
            },
            body: JSON.stringify(payload)
        })
        .then( res => res.json())
        .then( res => {
            if(res.status == "error"){
                console.error(res.errors)
                alert(`Error approving allocation:\n${formatErrors(res.errors)}`)
            } else {
                alert("Approved allocation")
                location.reload(); // Refresh admin form
            }
        });
    });

    const contactSubmitBtn = document.getElementById("contact-submit-btn")
    const inputContactMessage = document.getElementById("idContactMessage")
    contactSubmitBtn.addEventListener("click", function(){
        let message = inputContactMessage.value
        let payload = {
            "allocation": {
                "status": document.getElementById("allocationStatus").value,
                "id": document.getElementById("allocationId").value,
            },
            "rt": {
                "requestor": document.getElementById("requestor").value, // requestor username
                "problem_description": message, 
            },
        }
        fetch("/admin/allocations/contact/", {
            method: "POST",
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded',
                "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value,
            },
            body: JSON.stringify(payload)
        })
        .then( res => res.json())
        .then( res => {
            if(res.status == "error"){
                alert(`Error contacting PI:\n${formatErrors(res.errors)}`)
            } else {
                alert(`Successfully contacted PI.`)
                location.reload(); // Refresh admin form
            }
        });
    })
});
