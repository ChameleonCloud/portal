import logging
import re

from django import forms
from pytas.http import TASClient

logger = logging.getLogger(__name__)

ELIGIBLE = "Eligible"
INELIGIBLE = "Ineligible"
REQUESTED = "Requested"
PI_ELIGIBILITY = (
    ("", "Choose One"),
    (ELIGIBLE, ELIGIBLE),
    (INELIGIBLE, INELIGIBLE),
    (REQUESTED, REQUESTED),
)


USER_PROFILE_TITLES = (
    ("", "Choose one"),
    ("Center Non-Researcher Staff", "Center Non-Researcher Staff"),
    ("Center Researcher Staff", "Center Researcher Staff"),
    ("Faculty", "Faculty"),
    ("Government User", "Government User"),
    ("Graduate Student", "Graduate Student"),
    ("High School Student", "High School Student"),
    ("High School Teacher", "High School Teacher"),
    ("Industrial User", "Industrial User"),
    ("Unaffiliated User", "Unaffiliated User"),
    ("Nonprofit User", "Nonprofit User"),
    ("NSF Graduate Research Fellow", "NSF Graduate Research Fellow"),
    ("Other User", "Other User"),
    ("Postdoctorate", "Postdoctorate"),
    ("Undergraduate Student", "Undergraduate Student"),
    ("Unknown", "Unknown"),
    ("University Non-Research Staff", "University Non-Research Staff"),
    (
        "University Research Staff",
        "University Research Staff (excluding postdoctorates)",
    ),
)

# ISO-3166 list; this matches what is in the keycloak-chameleon extension.
# TODO(jason): pull this list from an endpoint exposed by Keycloak? Hard to keep
# this in sync (but how often do new countries come around?)
COUNTRY_LIST = (
    ("", "Choose one"),
    ("Afghanistan", "Afghanistan"),
    ("Åland Islands", "Åland Islands"),
    ("Albania", "Albania"),
    ("Algeria", "Algeria"),
    ("American Samoa", "American Samoa"),
    ("Andorra", "Andorra"),
    ("Angola", "Angola"),
    ("Anguilla", "Anguilla"),
    ("Antarctica", "Antarctica"),
    ("Antigua and Barbuda", "Antigua and Barbuda"),
    ("Argentina", "Argentina"),
    ("Armenia", "Armenia"),
    ("Aruba", "Aruba"),
    ("Australia", "Australia"),
    ("Austria", "Austria"),
    ("Azerbaijan", "Azerbaijan"),
    ("Bahamas", "Bahamas"),
    ("Bahrain", "Bahrain"),
    ("Bangladesh", "Bangladesh"),
    ("Barbados", "Barbados"),
    ("Belarus", "Belarus"),
    ("Belgium", "Belgium"),
    ("Belize", "Belize"),
    ("Benin", "Benin"),
    ("Bermuda", "Bermuda"),
    ("Bhutan", "Bhutan"),
    ("Bolivia (Plurinational State of)", "Bolivia (Plurinational State of)"),
    ("Bonaire, Sint Eustatius and Saba", "Bonaire, Sint Eustatius and Saba"),
    ("Bosnia and Herzegovina", "Bosnia and Herzegovina"),
    ("Botswana", "Botswana"),
    ("Bouvet Island", "Bouvet Island"),
    ("Brazil", "Brazil"),
    ("British Indian Ocean Territory", "British Indian Ocean Territory"),
    ("Brunei Darussalam", "Brunei Darussalam"),
    ("Bulgaria", "Bulgaria"),
    ("Burkina Faso", "Burkina Faso"),
    ("Burundi", "Burundi"),
    ("Cabo Verde", "Cabo Verde"),
    ("Cambodia", "Cambodia"),
    ("Cameroon", "Cameroon"),
    ("Canada", "Canada"),
    ("Cayman Islands", "Cayman Islands"),
    ("Central African Republic", "Central African Republic"),
    ("Chad", "Chad"),
    ("Chile", "Chile"),
    ("China", "China"),
    ("Christmas Island", "Christmas Island"),
    ("Cocos (Keeling) Islands", "Cocos (Keeling) Islands"),
    ("Colombia", "Colombia"),
    ("Comoros", "Comoros"),
    ("Congo", "Congo"),
    ("Congo, Democratic Republic of the", "Congo, Democratic Republic of the"),
    ("Cook Islands", "Cook Islands"),
    ("Costa Rica", "Costa Rica"),
    ("Côte d'Ivoire", "Côte d'Ivoire"),
    ("Croatia", "Croatia"),
    ("Cuba", "Cuba"),
    ("Curaçao", "Curaçao"),
    ("Cyprus", "Cyprus"),
    ("Czechia", "Czechia"),
    ("Denmark", "Denmark"),
    ("Djibouti", "Djibouti"),
    ("Dominica", "Dominica"),
    ("Dominican Republic", "Dominican Republic"),
    ("Ecuador", "Ecuador"),
    ("Egypt", "Egypt"),
    ("El Salvador", "El Salvador"),
    ("Equatorial Guinea", "Equatorial Guinea"),
    ("Eritrea", "Eritrea"),
    ("Estonia", "Estonia"),
    ("Eswatini", "Eswatini"),
    ("Ethiopia", "Ethiopia"),
    ("Falkland Islands (Malvinas)", "Falkland Islands (Malvinas)"),
    ("Faroe Islands", "Faroe Islands"),
    ("Fiji", "Fiji"),
    ("Finland", "Finland"),
    ("France", "France"),
    ("French Guiana", "French Guiana"),
    ("French Polynesia", "French Polynesia"),
    ("French Southern Territories", "French Southern Territories"),
    ("Gabon", "Gabon"),
    ("Gambia", "Gambia"),
    ("Georgia", "Georgia"),
    ("Germany", "Germany"),
    ("Ghana", "Ghana"),
    ("Gibraltar", "Gibraltar"),
    ("Greece", "Greece"),
    ("Greenland", "Greenland"),
    ("Grenada", "Grenada"),
    ("Guadeloupe", "Guadeloupe"),
    ("Guam", "Guam"),
    ("Guatemala", "Guatemala"),
    ("Guernsey", "Guernsey"),
    ("Guinea", "Guinea"),
    ("Guinea-Bissau", "Guinea-Bissau"),
    ("Guyana", "Guyana"),
    ("Haiti", "Haiti"),
    ("Heard Island and McDonald Islands", "Heard Island and McDonald Islands"),
    ("Holy See", "Holy See"),
    ("Honduras", "Honduras"),
    ("Hong Kong", "Hong Kong"),
    ("Hungary", "Hungary"),
    ("Iceland", "Iceland"),
    ("India", "India"),
    ("Indonesia", "Indonesia"),
    ("Iran (Islamic Republic of)", "Iran (Islamic Republic of)"),
    ("Iraq", "Iraq"),
    ("Ireland", "Ireland"),
    ("Isle of Man", "Isle of Man"),
    ("Israel", "Israel"),
    ("Italy", "Italy"),
    ("Jamaica", "Jamaica"),
    ("Japan", "Japan"),
    ("Jersey", "Jersey"),
    ("Jordan", "Jordan"),
    ("Kazakhstan", "Kazakhstan"),
    ("Kenya", "Kenya"),
    ("Kiribati", "Kiribati"),
    (
        "Korea (Democratic People's Republic of)",
        "Korea (Democratic People's Republic of)",
    ),
    ("Korea, Republic of", "Korea, Republic of"),
    ("Kuwait", "Kuwait"),
    ("Kyrgyzstan", "Kyrgyzstan"),
    ("Lao People's Democratic Republic", "Lao People's Democratic Republic"),
    ("Latvia", "Latvia"),
    ("Lebanon", "Lebanon"),
    ("Lesotho", "Lesotho"),
    ("Liberia", "Liberia"),
    ("Libya", "Libya"),
    ("Liechtenstein", "Liechtenstein"),
    ("Lithuania", "Lithuania"),
    ("Luxembourg", "Luxembourg"),
    ("Macao", "Macao"),
    ("Madagascar", "Madagascar"),
    ("Malawi", "Malawi"),
    ("Malaysia", "Malaysia"),
    ("Maldives", "Maldives"),
    ("Mali", "Mali"),
    ("Malta", "Malta"),
    ("Marshall Islands", "Marshall Islands"),
    ("Martinique", "Martinique"),
    ("Mauritania", "Mauritania"),
    ("Mauritius", "Mauritius"),
    ("Mayotte", "Mayotte"),
    ("Mexico", "Mexico"),
    ("Micronesia (Federated States of)", "Micronesia (Federated States of)"),
    ("Moldova, Republic of", "Moldova, Republic of"),
    ("Monaco", "Monaco"),
    ("Mongolia", "Mongolia"),
    ("Montenegro", "Montenegro"),
    ("Montserrat", "Montserrat"),
    ("Morocco", "Morocco"),
    ("Mozambique", "Mozambique"),
    ("Myanmar", "Myanmar"),
    ("Namibia", "Namibia"),
    ("Nauru", "Nauru"),
    ("Nepal", "Nepal"),
    ("Netherlands", "Netherlands"),
    ("New Caledonia", "New Caledonia"),
    ("New Zealand", "New Zealand"),
    ("Nicaragua", "Nicaragua"),
    ("Niger", "Niger"),
    ("Nigeria", "Nigeria"),
    ("Niue", "Niue"),
    ("Norfolk Island", "Norfolk Island"),
    ("North Macedonia", "North Macedonia"),
    ("Northern Mariana Islands", "Northern Mariana Islands"),
    ("Norway", "Norway"),
    ("Oman", "Oman"),
    ("Pakistan", "Pakistan"),
    ("Palau", "Palau"),
    ("Palestine, State of", "Palestine, State of"),
    ("Panama", "Panama"),
    ("Papua New Guinea", "Papua New Guinea"),
    ("Paraguay", "Paraguay"),
    ("Peru", "Peru"),
    ("Philippines", "Philippines"),
    ("Pitcairn", "Pitcairn"),
    ("Poland", "Poland"),
    ("Portugal", "Portugal"),
    ("Puerto Rico", "Puerto Rico"),
    ("Qatar", "Qatar"),
    ("Réunion", "Réunion"),
    ("Romania", "Romania"),
    ("Russian Federation", "Russian Federation"),
    ("Rwanda", "Rwanda"),
    ("Saint Barthélemy", "Saint Barthélemy"),
    (
        "Saint Helena, Ascension and Tristan da Cunha",
        "Saint Helena, Ascension and Tristan da Cunha",
    ),
    ("Saint Kitts and Nevis", "Saint Kitts and Nevis"),
    ("Saint Lucia", "Saint Lucia"),
    ("Saint Martin (French part)", "Saint Martin (French part)"),
    ("Saint Pierre and Miquelon", "Saint Pierre and Miquelon"),
    ("Saint Vincent and the Grenadines", "Saint Vincent and the Grenadines"),
    ("Samoa", "Samoa"),
    ("San Marino", "San Marino"),
    ("Sao Tome and Principe", "Sao Tome and Principe"),
    ("Saudi Arabia", "Saudi Arabia"),
    ("Senegal", "Senegal"),
    ("Serbia", "Serbia"),
    ("Seychelles", "Seychelles"),
    ("Sierra Leone", "Sierra Leone"),
    ("Singapore", "Singapore"),
    ("Sint Maarten (Dutch part)", "Sint Maarten (Dutch part)"),
    ("Slovakia", "Slovakia"),
    ("Slovenia", "Slovenia"),
    ("Solomon Islands", "Solomon Islands"),
    ("Somalia", "Somalia"),
    ("South Africa", "South Africa"),
    (
        "South Georgia and the South Sandwich Islands",
        "South Georgia and the South Sandwich Islands",
    ),
    ("South Sudan", "South Sudan"),
    ("Spain", "Spain"),
    ("Sri Lanka", "Sri Lanka"),
    ("Sudan", "Sudan"),
    ("Suriname", "Suriname"),
    ("Svalbard and Jan Mayen", "Svalbard and Jan Mayen"),
    ("Sweden", "Sweden"),
    ("Switzerland", "Switzerland"),
    ("Syrian Arab Republic", "Syrian Arab Republic"),
    ("Taiwan, Province of China", "Taiwan, Province of China"),
    ("Tajikistan", "Tajikistan"),
    ("Tanzania, United Republic of", "Tanzania, United Republic of"),
    ("Thailand", "Thailand"),
    ("Timor-Leste", "Timor-Leste"),
    ("Togo", "Togo"),
    ("Tokelau", "Tokelau"),
    ("Tonga", "Tonga"),
    ("Trinidad and Tobago", "Trinidad and Tobago"),
    ("Tunisia", "Tunisia"),
    ("Turkey", "Turkey"),
    ("Turkmenistan", "Turkmenistan"),
    ("Turks and Caicos Islands", "Turks and Caicos Islands"),
    ("Tuvalu", "Tuvalu"),
    ("Uganda", "Uganda"),
    ("Ukraine", "Ukraine"),
    ("United Arab Emirates", "United Arab Emirates"),
    (
        "United Kingdom of Great Britain and Northern Ireland",
        "United Kingdom of Great Britain and Northern Ireland",
    ),
    ("United States of America", "United States of America"),
    ("United States Minor Outlying Islands", "United States Minor Outlying Islands"),
    ("Uruguay", "Uruguay"),
    ("Uzbekistan", "Uzbekistan"),
    ("Vanuatu", "Vanuatu"),
    ("Venezuela (Bolivarian Republic of)", "Venezuela (Bolivarian Republic of)"),
    ("Viet Nam", "Viet Nam"),
    ("Virgin Islands (British)", "Virgin Islands (British)"),
    ("Virgin Islands (U.S.)", "Virgin Islands (U.S.)"),
    ("Wallis and Futuna", "Wallis and Futuna"),
    ("Western Sahara", "Western Sahara"),
    ("Yemen", "Yemen"),
    ("Zambia", "Zambia"),
    ("Zimbabwe", "Zimbabwe"),
)


class EmailConfirmationForm(forms.Form):
    code = forms.CharField(
        label="Enter Your Verification Code",
        required=True,
        error_messages={
            "required": "Please enter the verification code you received via email."
        },
    )

    username = forms.CharField(label="Enter Your Chameleon Username", required=True)


def check_password_policy(user, password, confirm_password):
    """
    Checks the password for meeting the minimum password policy requirements:
    * Must be a minimum of 8 characters in length
    * Must contain characters from at least three of the following: uppercase letters,
      lowercase letters, numbers, symbols
    * Must NOT contain the username or the first or last name from the profile

    Returns:
        A boolean value indicating if the password meets the policy,
        An error message string or None
    """
    if password != confirm_password:
        return False, "The password provided does not match the confirmation."

    if len(password) < 8:
        return (
            False,
            "The password provided is too short. Please review the password criteria.",
        )

    char_classes = 0
    for cc in ["[a-z]", "[A-Z]", "[0-9]", "[^a-zA-Z0-9]"]:
        if re.search(cc, password):
            char_classes += 1

    if char_classes < 3:
        return False, "The password provided does not meet the complexity requirements."

    pwd_without_case = password.lower()
    if user["username"].lower() in pwd_without_case:
        return (
            False,
            "The password provided must not contain parts of your name or username.",
        )

    if (
        user["firstName"].lower() in pwd_without_case
        or user["lastName"].lower() in pwd_without_case
    ):
        return (
            False,
            "The password provided must not contain parts of your name or username.",
        )

    return True, None


class RecoverUsernameForm(forms.Form):
    email = forms.CharField(label="Enter Your Email Address", required=True)


class PasswordResetRequestForm(forms.Form):
    username = forms.CharField(label="Enter Your Chameleon Username", required=True)


class PasswordResetConfirmForm(forms.Form):
    username = forms.CharField(label="Enter Your Chameleon Username", required=True)
    code = forms.CharField(label="Reset Code", required=True)
    password = forms.CharField(
        widget=forms.PasswordInput, label="Password", required=True
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput,
        label="Confirm Password",
        required=True,
        help_text="Passwords must meet the following criteria:<ul>"
        "<li>Must not contain your username or parts of "
        "your full name;</li><li>Must be a minimum of 8 characters "
        "in length;</li><li>Must contain characters from at least "
        "three of the following: uppercase letters, "
        "lowercase letters, numbers, symbols</li></ul>",
    )

    def clean(self):
        cleaned_data = self.cleaned_data
        username = cleaned_data.get("username")

        try:
            tas = TASClient()
            user = tas.get_user(username=username)
        except:
            self.add_error(
                "username", "The username provided does not match an existing user."
            )
            raise forms.ValidationError(
                "The username provided does not match an existing user."
            )

        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        valid, error_message = check_password_policy(user, password, confirm_password)
        if not valid:
            self.add_error("password", error_message)
            self.add_error("confirm_password", "")
            raise forms.ValidationError(error_message)


class UserProfileForm(forms.Form):
    firstName = forms.CharField(label="First name")
    lastName = forms.CharField(label="Last name")
    email = forms.EmailField()
    phone = forms.CharField(
        required=False,
        error_messages={
            "invalid": (
                "For security reasons, we require all PIs have a contact "
                "phone number registered."
            ),
        },
    )
    institution = forms.CharField(
        label="Institution",
        error_messages={
            "invalid": "Please select your affiliated institution",
        },
    )
    department = forms.CharField(label="Department", required=False)
    title = forms.ChoiceField(
        label="Position/Title", required=False, choices=USER_PROFILE_TITLES
    )
    country = forms.ChoiceField(
        label="Country of residence",
        required=False,
        choices=COUNTRY_LIST,
        error_messages={
            "invalid": "Please select your country of residence.",
        },
    )
    citizenship = forms.ChoiceField(
        label="Country of citizenship",
        required=False,
        choices=COUNTRY_LIST,
        error_messages={
            "invalid": "Please select your country of citizenship.",
        },
    )

    disabled_fields = ["firstName", "lastName"]
    required_for_pi = ["phone", "institution", "country", "citizenship"]

    def __init__(self, *args, **kwargs):
        pi_eligibility_requested = kwargs.pop("is_pi_eligible", False)
        super(UserProfileForm, self).__init__(*args, **kwargs)

        for field in self.disabled_fields:
            self.fields[field].widget.attrs["readonly"] = True
            self.fields[field].disabled = True

        if pi_eligibility_requested:
            for field in self.required_for_pi:
                self.fields[field].required = True

        # Prevent users from editing citizenship if  already set
        # Ensure this comes after we set fields to required! We have to
        # explicitly set this field to not required for it to pass validation
        # due to using 'disabled' to prevent overwrites.
        if self.initial.get("citizenship"):
            citizenship_field = self.fields["citizenship"]
            citizenship_field.widget.attrs["readonly"] = True
            citizenship_field.disabled = True
            citizenship_field.required = False
            citizenship_field.help_text = (
                "Please file a support ticket if you need to update your "
                "citizenship on file."
            )


class TasUserProfileAdminForm(forms.Form):
    """
    Admin Form for TAS User Profile. Adds a field to trigger a password reset
    on the User's behalf.
    """

    firstName = forms.CharField(label="First name")
    lastName = forms.CharField(label="Last name")
    email = forms.EmailField()
    phone = forms.CharField()
    piEligibility = forms.ChoiceField(choices=PI_ELIGIBILITY, label="PI Eligibility")
    reset_password = forms.BooleanField(
        required=False,
        label="Reset user's password",
        help_text="Check this box to reset the user's password. The user will be "
        "notified via email with instructions to complete the password reset.",
    )
