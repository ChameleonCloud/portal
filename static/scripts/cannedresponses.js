// PI Eligibility
const piApproval = `Congratulations, your Chameleon PI eligibility request has been approved!

Please, bear in mind that as project PI you will be responsible for ensuring that users gaining access to Chameleon via your project observe security best practices described in:
https://chameleoncloud.org/blog/2021/06/28/best-practices-making-your-experiments-secure/

Also, please remember that as a condition of use, all users are expected to acknowledge or reference Chameleon in their publications as explained in our FAQ:
https://chameleoncloud.org/learn/frequently-asked-questions/

We are looking forward to your project request!
`

function getCannedResponsesPIEligibility(status) {
    if (status == 'ELIGIBLE') {
    	document.getElementById('id_review_summary').value=piApproval;
    } else {
    	document.getElementById('id_review_summary').value="";
    }
}

// Allocations
const allocationNewApproval = `Congratulations, your Chameleon allocation request has been approved!

Please, bear in mind that as project PI you are responsible for ensuring that users gaining access to Chameleon via your project observe security best practices described in:
https://chameleoncloud.org/blog/2021/06/28/best-practices-making-your-experiments-secure/

Also, please remember that as a condition of use, all users are expected to acknowledge Chameleon in their publications as explained in our FAQ:
https://chameleoncloud.org/learn/frequently-asked-questions/

We maintain a list of publications that were enabled by Chameleon. To add your publications, please use the publication dashboard:
https://chameleoncloud.readthedocs.io/en/latest/user/project.html#manage-publications 

Good luck with your project! If you need any help, please contact us via the Help desk at https://chameleoncloud.org/user/help/!
`

const allocationRenewalApproval = `Congratulations, your Chameleon Renewal request has been approved to start on <Month> <Day>, <Year> immediately following the end of the current active allocation!

As a reminder, you are responsible for ensuring that users gaining access to Chameleon via your project observe security best practices described in:
https://chameleoncloud.org/blog/2021/06/28/best-practices-making-your-experiments-secure/

Also, please continue to acknowledge Chameleon in your publications as explained in our FAQ [1] and report your publications via the publication dashboard [2]. 

Good luck with your project!

[1] https://chameleoncloud.org/learn/frequently-asked-questions/
[2] https://chameleoncloud.readthedocs.io/en/latest/user/project.html#manage-publications
`

const allocationRechargeApproval = `Congratulations, your Recharge request has been approved, keeping the original end date of the current allocation of <Month> <Day>, <Year>!

As a reminder, you are responsible for ensuring that users gaining access to Chameleon via your project observe security best practices described in:
https://chameleoncloud.org/blog/2021/06/28/best-practices-making-your-experiments-secure/

Also, please continue to acknowledge Chameleon in your publications as explained in our FAQ [1] and report your publications via the publication dashboard [2].

Good luck with your project!

[1] https://chameleoncloud.org/learn/frequently-asked-questions/
[2] https://chameleoncloud.readthedocs.io/en/latest/user/project.html#manage-publications
`

function getCannedResponsesAllocation(type) {
    if (type == 'new') {
    	document.getElementById('idDecisionSummary').value=allocationNewApproval;
    } else if (type == 'renewal') {
    	document.getElementById('idDecisionSummary').value=allocationRenewalApproval;
    } else if (type == 'recharge') {
        document.getElementById('idDecisionSummary').value=allocationRechargeApproval;
    } else {
        document.getElementById('idDecisionSummary').value="";
    }
}
