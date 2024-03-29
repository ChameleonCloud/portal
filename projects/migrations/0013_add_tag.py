# Generated by Django 3.2 on 2022-08-19 15:11

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


education_tag = None
covid_tag = None
innovative_tag = None
other_tag = None
old_covid_projects = []
old_education_projects = []
old_research_projects = []
old_innovative_projects = []


def create_tags(apps, _):
    """
    Move the tags from Type model to Tag model
    """
    type_model = apps.get_model("projects", "Type")
    tag_model = apps.get_model("projects", "Tag")

    # Tags which are a 1:1 migration
    global education_tag
    global covid_tag
    global innovative_tag
    global other_tag
    education_tag = tag_model(
        name="Computing Education",
        description="Seeding inclusive computing education for the next generation "
        "and all computer-science training",
    )
    covid_tag = tag_model(
        name="COVID",
        description="Related to COVID-19",
    )
    innovative_tag = tag_model(
        name="Innovative Application", description="Applications for domain sciences"
    )
    other_tag = tag_model(
        name="Other",
        description="My project research area doesn’t fit in any of "
        "the predefined categories",
    )

    tags = [
        education_tag,
        covid_tag,
        innovative_tag,
        other_tag,
        tag_model(
            name="Computer Architecture",
            description="Designing computer systems optimized for high performance, "
            "energy efficiency, and scalability",
        ),
        tag_model(
            name="Data Science",
            description="Developing algorithms for managing and analyzing data at scale",
        ),
        tag_model(
            name="Database Systems",
            description="Designing systems for managing and storing data at scale",
        ),
        tag_model(
            name="Human Computer Interaction",
            description="Exploring the interfaces between people and technologies",
        ),
        tag_model(
            name="AI and Machine Learning",
            description="Foundations and applications of computer algorithms making "
            "data-centric models, predictions, and decisions",
        ),
        tag_model(
            name="Networking",
            description="Analysis, design, implementation, and use of local, "
            "wide-area, and mobile networks that link computers together",
        ),
        tag_model(
            name="Programming Languages",
            description="Devising new and better ways of programming the computers",
        ),
        tag_model(
            name="Robotics",
            description="Design, construction, operation, and use of robots",
        ),
        tag_model(
            name="Scientific and High-Performance Computing",
            description="Scientific discovery at the frontiers of computational "
            "performance, intelligence, and scale",
        ),
        tag_model(
            name="Security and Privacy",
            description="Understanding and defending against emerging threats in our "
            "increasingly computational world",
        ),
        tag_model(
            name="Software Engineering",
            description="Design, development, testing, and maintenance of "
            "software applications",
        ),
        tag_model(
            name="Distributed Systems",
            description="Harness the power of multiple computational units",
        ),
        tag_model(
            name="Operating Systems",
            description="Analysis, design, and implementation of operating systems",
        ),
        tag_model(
            name="Storage Systems",
            description="Capturing, managing, securing, and prioritizing data",
        ),
        tag_model(
            name="Cloud Computing",
            description="Delivering computing services over the Internet to offer "
            "faster innovation, flexible resources, and economies of scale",
        ),
        tag_model(
            name="Edge Computing",
            description="Bring applications closer to data sources such as IoT "
            "devices or local edge servers",
        ),
        tag_model(
            name="Vision and Graphics",
            description="Creating and analyzing data from the visual world, "
            "and visually understanding complex data",
        ),
        tag_model(
            name="Theory of Computation",
            description="Mathematical foundations of computation, including "
            "algorithm design, complexity and logic",
        ),
        tag_model(
            name="Daypass",
            description="Daypass project",
            expose=False,
        ),
    ]

    tag_model.objects.bulk_create(tags)

    if type_model.objects.count() == 0:
        return
    covid_type = type_model.objects.get(name="COVID")
    research_type = type_model.objects.get(name="CS Research")
    education_type = type_model.objects.get(name="Education")
    innovative_type = type_model.objects.get(name="Innovative Application")

    # Gather the old tags. We have to remove the type model from the project model
    # to add the projects to the new tag model,
    # So all we do is collect them here, and then move them later.
    global old_covid_projects
    global old_research_projects
    global old_education_projects
    global old_innovative_projects
    old_covid_projects = list(covid_type.project_type.all())
    old_research_projects = list(research_type.project_type.all())
    old_education_projects = list(education_type.project_type.all())
    old_innovative_projects = list(innovative_type.project_type.all())


def migrate_tags(apps, _):
    tag_model = apps.get_model("projects", "Tag")
    project_model = apps.get_model("projects", "Project")
    if project_model.objects.count() == 0:
        return
    global covid_tag
    global education_tag
    global other_tag
    global innovative_tag

    # Refresh tags with proper schema
    covid_tag = tag_model.objects.get(name=covid_tag.name)
    education_tag = tag_model.objects.get(name=education_tag.name)
    other_tag = tag_model.objects.get(name=other_tag.name)
    innovative_tag = tag_model.objects.get(name=innovative_tag.name)

    # Refresh projects with proper schema
    for project_list in (
        old_covid_projects,
        old_research_projects,
        old_education_projects,
        old_innovative_projects,
    ):
        for i, project in enumerate(project_list):
            project_list[i] = project_model.objects.get(pk=project.id)
    covid_tag.projects.add(*old_covid_projects)
    education_tag.projects.add(*old_education_projects)
    other_tag.projects.add(*old_research_projects)
    innovative_tag.projects.add(*old_innovative_projects)


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("projects", "0012_funding"),
    ]

    operations = [
        migrations.CreateModel(
            name="Tag",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255, unique=True)),
                (
                    "description",
                    models.CharField(max_length=255, blank=False, unique=True),
                ),
                ("expose", models.BooleanField(default=True)),
            ],
        ),
        migrations.AddField(
            model_name="project",
            name="tag",
            field=models.ForeignKey(
                default=None,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="projects",
                to="projects.tag",
            ),
            preserve_default=False,
        ),
        migrations.RunPython(create_tags),
        migrations.RemoveField(
            model_name="project",
            name="type",
        ),
        migrations.RunPython(migrate_tags),
    ]
