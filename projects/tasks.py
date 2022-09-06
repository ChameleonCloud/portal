import logging
from collections import namedtuple, Counter, defaultdict
from datetime import datetime

from celery.decorators import task
from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from django.utils.html import strip_tags

from allocations.models import Allocation
from projects.models import Invitation, Project, Tag
from sharing_portal import trovi
from sharing_portal.models import DaypassRequest, DaypassProject
from util.keycloak_client import KeycloakClient
from .views import get_invitations_beyond_duration, get_project_membership_managers

LOG = logging.getLogger(__name__)


@task
def activate_expire_invitations():
    now = timezone.now()

    expired_invitations = Invitation.objects.filter(
        status=Invitation.STATUS_ISSUED, date_expires__lte=now
    )
    expired_invitation_count = 0
    for invitation in expired_invitations:
        charge_code = invitation.project.charge_code
        try:
            invitation.delete()
            expired_invitation_count += 1
        except Exception:
            LOG.exception(
                f"Error expiring invitation with code {invitation.email_address}"
            )
        LOG.info(f"Expired invitation {invitation.email_code} on project {charge_code}")
    LOG.debug(
        "need to expire {} invitations, and {} were actually expired".format(
            len(expired_invitations), expired_invitation_count
        )
    )


@task
def end_daypasses():
    beyond_duration_invitations = get_invitations_beyond_duration()
    for invitation in beyond_duration_invitations:
        try:
            LOG.info(f"Removing user from project with invite {invitation.id}\n")
            project = Project.objects.get(pk=invitation.project_id)
            user = User.objects.get(pk=invitation.user_accepted_id)
            keycloak_client = KeycloakClient()
            keycloak_client.update_membership(
                project.charge_code, user.username, "delete"
            )
            invitation.status = Invitation.STATUS_BEYOND_DURATION
            invitation.save()

            try:
                daypass_request = DaypassRequest.objects.get(invitation=invitation)
                approved_requests = (
                    DaypassRequest.objects.all()
                    .filter(
                        artifact_uuid=daypass_request.artifact_uuid,
                        status=DaypassRequest.STATUS_APPROVED,
                        invitation__status=Invitation.STATUS_BEYOND_DURATION,
                    )
                    .count()
                )
                if approved_requests == settings.DAYPASS_LIMIT:
                    # Send an email
                    handle_too_many_daypass_users(daypass_request.artifact_uuid)
            except DaypassRequest.DoesNotExist:
                pass
        except Exception as e:
            LOG.error(f"Error ending daypass invite {invitation.id}: {e}")


def handle_too_many_daypass_users(artifact_uuid):
    # Make allocation expire
    reproducibility_project = DaypassProject.objects.get(
        artifact_uuid=artifact_uuid
    ).project
    allocations = Allocation.objects.filter(
        status="active", project=reproducibility_project
    )
    now = datetime.now(timezone.utc)
    for alloc in allocations:
        # Prevent this from running multiple times
        # NOTE: We cannot change status or something of the allocation,
        # as it needs to still be 'active' for the allocation expiration task
        # to kick in.
        if alloc.expiration_date <= now:
            return
        alloc.expiration_date = now
        alloc.save()

    admin_token = trovi.get_client_admin_token()
    artifact = trovi.get_artifact(admin_token, artifact_uuid)
    artifact_title = artifact["title"]
    project = trovi.get_linked_project(artifact)
    managers = [u.email for u in get_project_membership_managers(project)]

    subject = "Pause on daypass requests"
    help_url = "https://chameleoncloud.org/user/help/"
    body = f"""
    <p>
    Thank you for using our daypass feature for Trovi artifacts!
    We have noticied that {settings.DAYPASS_LIMIT} users have been approved to
    reproduce '{artifact_title}'. As a status check, we have put a pause on the
    allocation in order to request more details. Please submit a ticket to
    our <a href="{help_url}">help desk</a> mentioning the situation so we can
    discuss this further.
    </p>
    <p><i>This is an automatic email, please <b>DO NOT</b> reply!
    If you have any question or issue, please submit a ticket on our
    <a href="{help_url}">help desk</a>.
    </i></p>
    <p>Thanks,</p>
    <p>Chameleon Team</p>
    """
    send_mail(
        subject=subject,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=managers,
        message=strip_tags(body),
        html_message=body,
    )


def get_project_link(project):
    return f"https://chameleoncloud.org/user/projects/{project.pk}"


def email_subject_1_project(project):
    return f"Your project {project.charge_code} has been automatically tagged!"


def email_subject_n_projects(n):
    return f"{n} of your projects have been automatically tagged!"


BASE_INTRO = """
            <p>
            As part of a recent change in our project organization, we have implemented 
            a new project tagging system.
"""


def email_body_intro_1_project(project, runners_up):
    body = (
        BASE_INTRO
        + f"""
             We automatically selected the following tag
             for your project <b>{project.charge_code} — {project.title}</b>:
             
            <p><i>{project.tag.name} — {project.tag.description}</i></p>
            
            </p>
            """
    )
    if runners_up:
        body += f"""
            <p>The following tags were considered, but not chosen:</p>
                
            <p>{runners_up}</p>
        """

    body += f"""
    <p>
    If our selection does not seem correct to you, you may freely update your
    tag <a href="{get_project_link(project)}" target="_blank">here</a>.
    </p>
    """

    return body


def email_body_intro_n_projects(projects):
    project_list = "\n<br>".join(
        f'<li> <b><a href="{get_project_link(p)}" target="_blank">{p.charge_code}</a> '
        f"— {p.description}</b>\n<ul><li>{p.tag.name} — {p.tag.description}</ul>"
        for p in projects
    )
    return (
        BASE_INTRO
        + f"""
    We automatically selected new tags for your projects:<br><br>
    <ol>
    {project_list}
    </ol>
    </p>
    
    <p>
    If our selections do not seem correct to you, you may freely update your tags by
    visiting the links to your projects above.
    </p>
    """
    )


def automatically_tag_projects():
    other_tag = Tag.objects.get(name="Other")
    uncategorized_projects = Project.objects.filter(tag=other_tag)
    # Container class to group tag models to keywords
    TagKeywords = namedtuple("TagKeywords", ("tag", "keywords"))
    # Custom hash function so we can store these containers in counters
    TagKeywords.__hash__ = lambda s: hash(s.tag.name)
    TagKeywords.__repr__ = lambda s: s.tag.name

    # Map all tags to a list of keyword stem matches
    tag_matchers = [
        TagKeywords(
            Tag.objects.get(name="Computing Education"),
            [
                "educ",
                "learn",
                "teach",
                "class",
                "cours",
                "curriculum",
                "student",
                "studi",
                "professor",
                "faculti",
                "k-12",
                "school",
                "introductori",
                "tutori",
                "webinar",
            ],
        ),
        TagKeywords(
            Tag.objects.get(name="COVID"),
            ["covid-19", "infect", "sars-cov-2", "viru", "viral"],
        ),
        TagKeywords(
            Tag.objects.get(name="Innovative Application"),
            ["innov", "scientif", "scienc"],
        ),
        TagKeywords(
            Tag.objects.get(name="Computer Architecture"),
            [
                "architectur",
                "driver",
                "kernel",
                "x86",
                "x64",
                "x86_64",
                "arm",
                "intel",
                "amd",
                "cpu",
                "memory",
                "frequenc",
                "assembl",
                "ram",
                "server",
                "thread",
                "process",
            ],
        ),
        TagKeywords(
            Tag.objects.get(name="Data Science"),
            [
                "data",
                "pandas",
                "scikit",
                "tkinter",
                "pytorch",
                "numpy",
                "tensorflow",
                "matplotlib",
                "jupyter",
                "model",
                "graph",
                "chart",
                "plot",
                "normal",
                "mean",
                "averag",
                "mode",
                "pipelin",
                "aggreg",
            ],
        ),
        TagKeywords(
            Tag.objects.get(name="Database Systems"),
            [
                "databas",
                "sql",
                "mysql",
                "mongodb",
                "mariadb",
                "relat",
                "non-rel",
                "table",
                "shard",
                "replic",
                "storag",
                "disk",
                "persist",
            ],
        ),
        TagKeywords(
            Tag.objects.get(name="Human Computer Interaction"),
            [
                "hci",
                "human",
                "interact",
                "interfac",
                "user",
                "ergonom",
                "psycholog",
                "display",
            ],
        ),
        TagKeywords(
            Tag.objects.get(name="AI and Machine Learning"),
            [
                "ai",
                "ml",
                "learn",
                "train",
                "model",
                "deep",
                "neural",
                "network",
                "tensor",
                "tensorflow",
                "decis",
                "nlp",
                "natur",
                "languag",
                "process",
                "reinforc",
                "recombin",
                "gpu",
                "pipelin",
                "perceptron",
                "vision",
                "recurr",
                "convolut",
                "classifi",
                "algorithm",
            ],
        ),
        TagKeywords(
            Tag.objects.get(name="Networking"),
            [
                "network",
                "router",
                "rout",
                "dns",
                "gateway",
                "subnet",
                "mbps",
                "gbps",
                "gigabit",
                "megabit",
                "latenc",
                "topolog",
                "ip",
                "mac",
                "address",
                "dhcp",
                "lan",
                "wan",
                "vlan",
                "area",
                "internet",
                "server",
                "client",
                "synchron",
                "asynchron",
                "source",
                "sink",
                "packet",
                "tcp",
                "udp",
            ],
        ),
        TagKeywords(
            Tag.objects.get(name="Programming Languages"),
            [
                "language",
                "compil",
                "parser",
                "pars",
                "lexic",
                "lexer",
                "grammar",
                "function",
                "imper",
                "pardigm",
                "multi-paradigm",
                "dsl",
                "stack",
                "heap",
                "assembl",
                "instruct",
                "synchron",
                "asynchron",
            ],
        ),
        TagKeywords(
            Tag.objects.get(name="Robotics"),
            ["robot", "mechan", "kit", "electron", "sensor", "control", "motor"],
        ),
        TagKeywords(
            Tag.objects.get(name="Scientific and High-Performance Computing"),
            [
                "comput",
                "high",
                "perform",
                "high-perform",
                "scientif",
                "super",
                "supercomput",
                "hpc",
                "cloud",
                "thread",
                "process",
                "synchron",
                "asynchron",
                "simul",
                "workload",
            ],
        ),
        TagKeywords(
            Tag.objects.get(name="Security and Privacy"),
            [
                "secur",
                "cybersecur",
                "privat",
                "privaci",
                "encrypt",
                "cryptographi",
                "crypto",
                "secret",
                "network",
                "selinux",
                "end-to-end",
                "tls",
                "ssl",
                "vulner",
                "exploit",
                "mitm",
                "intrud",
                "eavesdrop",
                "eavesdropp",
                "harden",
                "scan",
                "monitor",
                "adversari",
                "cloud",
                "malware",
                "infect",
                "viru",
                "trust",
                "zero-trust",
                "handshak",
                "exchang",
            ],
        ),
        TagKeywords(
            Tag.objects.get(name="Software Engineering"),
            [
                "software",
                "design",
                "engin",
                "agile",
                "test",
                "maintain",
                "mainten",
                "open",
                "source",
                "develop",
                "program",
                "programm",
                "plan",
                "plann",
                "packag",
                "releas",
                "version",
                "applic",
                "app",
            ],
        ),
        TagKeywords(
            Tag.objects.get(name="Distributed Systems"),
            [
                "distribut",
                "system",
                "network",
                "node",
                "load",
                "balanc",
                "workload",
                "manag",
                "pool",
                "replica",
                "replicat",
                "server",
                "client",
                "cloud",
                "synchron",
                "asynchron",
                "cluster",
                "resourc",
                "scale",
                "scalabl",
                "orchestr",
                "workload",
            ],
        ),
        TagKeywords(
            Tag.objects.get(name="Operating Systems"),
            [
                "oper",
                "system",
                "kernel",
                "driver",
                "modul",
                "acl",
                "uac",
                "user",
                "access",
                "linux",
                "unix",
                "nt",
                "bsd",
                "init",
                "boot",
                "stack",
                "heap",
                "assembl",
                "instruct",
                "schedul",
                "context",
                "thread",
                "process",
            ],
        ),
        TagKeywords(
            Tag.objects.get(name="Storage Systems"),
            [
                "disk",
                "storag",
                "raid",
                "stripe",
                "array",
                "replicat",
                "replica",
                "persist",
                "ssd",
                "hdd",
                "hard",
                "drive",
                "flash",
                "sata",
                "sas",
                "network",
                "attach",
                "volum",
                "object",
                "tape",
                "memory",
            ],
        ),
        TagKeywords(
            Tag.objects.get(name="Edge Computing"),
            [
                "edg",
                "devic",
                "raspberry",
                "pi",
                "jetson",
                "nano",
                "iot",
                "internet",
                "controller",
            ],
        ),
        TagKeywords(
            Tag.objects.get(name="Vision and Graphics"),
            [
                "graphic",
                "vision",
                "convolut",
                "convolv",
                "frame",
                "border",
                "imag",
                "3d",
                "pixel",
                "voxel",
                "gpu",
                "draw",
                "opengl",
                "opencv",
                "visual",
                "recogn",
                "classifi",
                "pictur",
            ],
        ),
        TagKeywords(
            Tag.objects.get(name="Theory of Computation"),
            [
                "theori",
                "automaton",
                "automata",
                "determinist",
                "np-hard",
                "polynomi",
                "state",
                "discret",
                "mathemat",
                "math",
                "stack",
                "proof",
                "algorithm",
                "graph",
                "complex",
            ],
        ),
    ]

    import nltk
    from nltk.stem import PorterStemmer, WordNetLemmatizer
    from nltk.tokenize import word_tokenize
    from nltk.corpus import stopwords

    nltk.download("wordnet")
    nltk.download("omw-1.4")
    nltk.download("punkt")
    nltk.download("stopwords")
    ps = PorterStemmer()
    lem = WordNetLemmatizer()
    word_filter = set(stopwords.words("english"))

    def normalize(text):
        tokenized = [w for w in word_tokenize(text.lower()) if w not in word_filter]
        return [ps.stem(lem.lemmatize(w)) for w in tokenized]

    ProjectTags = namedtuple("ProjectTags", ("project", "counter"))
    pi_projects = defaultdict(list)

    for project in uncategorized_projects:
        # We'll evaluate the title and the description of the project
        context = normalize(f"{project.title} {project.description}")
        finds = []
        # Add a count of each matcher every time a word appears in its keywords
        for word in context:
            for matcher in tag_matchers:
                if word in matcher.keywords:
                    finds.append(matcher)
        # Count all the times each matcher had a keyword appear in the text
        counter = Counter(finds)

        LOG.info(f"Keywork matching for project {project.charge_code}: {counter}")

        if len(counter) > 0:
            selected_tag = counter.most_common(1)[0][0].tag
        else:
            selected_tag = other_tag
        LOG.info(f"Selected tag {selected_tag}.")

        with transaction.atomic():
            project.tag = selected_tag
            project.automatically_tagged = True
            project.save()

        # Link the project and keyword info to the PI
        pi_projects[project.pi.email].append(ProjectTags(project, counter))

    for pi_email in pi_projects:
        projects = pi_projects[pi_email]
        body = f"Hi {projects[0].project.pi.first_name},<br>\n\n"
        if len(projects) == 1:
            project = projects[0].project
            counter = projects[0].counter
            runners_up = "\n<br>".join(
                f"• <i>{match[0].tag.name} — {match[0].tag.description}</i>"
                for match in counter.most_common()
                if match[0].tag.name != project.tag.name
            )
            subject = email_subject_1_project(project)
            body += email_body_intro_1_project(project, runners_up)
        else:
            subject = email_subject_n_projects(len(projects))
            body += email_body_intro_n_projects([p.project for p in projects])

        body += """
            Thank you!<br>
            Chameleon team
            """

        mail_sent = send_mail(
            subject=subject,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[pi_email],
            message=strip_tags(body),
            html_message=body,
            fail_silently=True,
        )

        if mail_sent:
            LOG.info(f"Successfully sent tag update mail to {pi_email}.")
        else:
            LOG.warning(f"Could not send tag update mail to {pi_email}")
