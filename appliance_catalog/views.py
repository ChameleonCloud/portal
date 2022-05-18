from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.urls import reverse, reverse_lazy
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.views.generic.edit import DeleteView
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from .forms import ApplianceForm, ApplianceShareForm
from .models import Appliance, Keyword, ApplianceTagging
from .serializers import ApplianceJSONSerializer, KeywordJSONSerializer
from itertools import chain
import markdown_deux
import logging
import json
from django.conf import settings
from keystoneauth1.identity import v3
from keystoneauth1 import session
from keystoneclient.v3 import client
from glanceclient import Client
from smtplib import SMTPException
from six.moves import http_client, urllib
import uuid
from chameleon.keystone_auth import admin_session

logger = logging.getLogger("default")


def make_image_public(username, image_id, region_name):
    sess = admin_session(region_name)
    glance = Client("2", session=sess)
    logger.info(
        (
            "User: {} requesting visibility=public for image id: {} in region: {}".format(
                username, image_id, region_name
            )
        )
    )
    glance.images.update(image_id, visibility="public")
    logger.info(
        (
            "User: {} image status after update: {}".format(
                username, glance.images.get(image_id)
            )
        )
    )


def app_list(request):
    logger.info("App catalog requested.")
    return render(request, "appliance_catalog/list.html")


def get_appliances(request):
    logger.info("Get appliances json endpoint requested.")
    keywords = request.GET.getlist("keywords")
    search = request.GET.get("search")
    logger.debug("URL query params: search=%s, keywords=%s", search, keywords)
    if keywords:
        appliances = Appliance.objects.filter(keywords__in=keywords)
        if appliances and search:
            appliances = appliances.filter(
                Q(name__icontains=search)
                | Q(description__icontains=search)
                | Q(author_name__icontains=search)
            )
        elif search:
            appliances = Appliance.objects.filter(
                Q(name__icontains=search)
                | Q(description__icontains=search)
                | Q(author_name__icontains=search)
            )
    else:
        appliances = Appliance.objects.all()
        # filter out any that need review unless they belong to me
    if request.user.is_authenticated:
        appliances = appliances.filter(
            Q(needs_review=False) | Q(created_by=request.user)
        )
    else:
        appliances = appliances.exclude(needs_review=True)

    for appliance in appliances:
        appliance.description = markdown_deux.markdown(appliance.description)
    logger.debug("Total matching appliances found: %d.", appliances.count())
    serializer = ApplianceJSONSerializer()
    response = {
        "status": "success",
        "message": "",
        "result": json.loads(serializer.serialize(appliances)),
    }
    return JsonResponse(response)


def app_detail(request, pk):
    logger.info("Detail requested for appliance id: %s.", pk)
    appliance = get_object_or_404(Appliance, pk=pk)
    logger.debug("Appliance found. Fetching it's keywords.")
    keywords = appliance.keywords.all()
    logger.debug("This appliance has %d keywords.", keywords.count())
    editable = (
        request.user.is_staff
        or request.user == appliance.created_by
        or request.user.has_perm("appliance_catalog.change_appliance")
    )
    try:
        validate_email(appliance.author_url)
        appliance.author_contact_type = "email"
    except ValidationError:
        appliance.author_contact_type = "url"
    try:
        validate_email(appliance.support_contact_url)
        appliance.support_contact_type = "email"
    except ValidationError:
        appliance.support_contact_type = "url"
    context = {"appliance": appliance, "keywords": keywords, "editable": editable}
    return render(request, "appliance_catalog/detail.html", context)


def app_documentation(request, pk):
    logger.info("Documentation requested for appliance id: %s.", pk)
    appliance = get_object_or_404(Appliance, pk=pk)
    logger.debug("Appliance found.")
    context = {
        "appliance": appliance,
    }
    return render(request, "appliance_catalog/documentation.html", context)


def get_appliance(request, pk):
    logger.info("Get appliance json endpoint requested for id: %s.", pk)
    response = {"status": "success"}
    try:
        serializer = ApplianceJSONSerializer()
        response["message"] = ""
        app = json.loads(serializer.serialize(Appliance.objects.filter(pk=pk)))
        logger.debug("Appliance found. Fetching keywords...")
        keywords = Appliance.objects.get(pk=pk).keywords.all()
        logger.debug("This appliance has %d keyword(s).", keywords.count())
        response["result"] = app
    except Appliance.DoesNotExist:
        response["message"] = "Does not exist."
        response["result"] = None
    return JsonResponse(response)


def get_appliance_by_id(request, appliance_id):
    try:
        pk = Appliance.objects.get(
            Q(chi_tacc_appliance_id=appliance_id)
            | Q(chi_uc_appliance_id=appliance_id)
            | Q(kvm_tacc_appliance_id=appliance_id)
        ).pk
        return get_appliance(request, pk)
    except Appliance.DoesNotExist:
        return get_appliance(request, -1)


def get_appliance_template(request, pk):
    logger.info("Getting and displaying YAML template for appliance")

    appliance = Appliance.objects.filter(pk=pk).get()

    # send message to GA
    if settings.GOOGLE_ANALYTICS_PROPERTY_ID:
        try:
            params = urllib.parse.urlencode(
                {
                    "v": 1,
                    "tid": settings.GOOGLE_ANALYTICS_PROPERTY_ID,
                    "cid": uuid.uuid1(),
                    "t": "event",
                    "ec": "heat_template",
                    "ea": "download",
                    "el": "{}-{}".format(pk, appliance.name),
                    "ev": 0,
                }
            )
            conn = http_client.HTTPConnection("www.google-analytics.com")
            conn.request("POST", "/collect", params)
        except:
            logger.exception("Failed to report to Google Analytics")
    return HttpResponse(appliance.template, content_type="text/yaml")


def _add_keywords(request, cleaned_data, appliance):
    logger.info(
        "Add keyword requested by user %s with data: %s. Appliance %s will be tagged with this keyword.",
        request.user.username,
        cleaned_data,
        appliance,
    )
    keywords = cleaned_data["keywords"]
    new_keywords = cleaned_data["new_keywords"]
    ApplianceTagging.objects.filter(appliance_id=appliance.id).delete()
    for keyword in keywords:
        ApplianceTagging.objects.create(keyword=keyword, appliance=appliance)
        logger.info("Appliance %s successfully tagged as: %s.", appliance, keyword)
    if new_keywords:
        new_keywords = new_keywords.split(",")
        for keyword in new_keywords:
            keyword = keyword.strip()
            try:
                existing_keyword = Keyword.objects.get(name=keyword)
                appliance_tagging = ApplianceTagging(
                    keyword=existing_keyword, appliance=appliance
                )
                appliance_tagging.save()
                logger.info(
                    "Appliance %s successfully tagged as: %s.",
                    appliance,
                    existing_keyword,
                )
            except Keyword.DoesNotExist:
                kw = Keyword(name=keyword)
                kw.save()
                logger.info("New tag %s created.", appliance, keyword)
                appliance_tagging = ApplianceTagging(keyword=kw, appliance=appliance)
                appliance_tagging.save()
                logger.info("Appliance %s successfully tagged as: %s.", appliance, kw)


@login_required
def app_create(request):
    if request.method == "POST":
        logger.info(
            "Appliance create posted by user %s with data %s and files %s",
            request.user.username,
            request.POST,
            request.FILES,
        )
        form = ApplianceForm(request.user, request.POST, request.FILES)
        if form.is_valid():
            logger.debug("Applicate create form is valid. Creating new appliance...")
            appliance = form.save(commit=False)
            appliance.created_by = request.user
            appliance.updated_by = request.user

            if appliance.project_supported:
                appliance.needs_review = False

            appliance.save()

            if request.META["HTTP_HOST"] == "www.chameleoncloud.org":
                message = "New Appliance Submitted: " + appliance.name + "."
                logger.debug(message)
                body = (
                    "A new appliance has been submitted and is ready for review. \n\n"
                    "Appliance Name: " + appliance.name + "\n"
                    "Contact Name and Email: "
                    + appliance.author_name
                    + " ("
                    + appliance.author_url
                    + ")\n\n"
                    "Appliance URL: https://www.chameleoncloud.org/appliances/"
                    + str(appliance.id)
                )
                try:
                    send_mail(
                        message,
                        body,
                        "noreply@chameleoncloud.org",
                        ("systems@chameleoncloud.org",),
                        fail_silently=False,
                    )
                except SMTPException as e:
                    logger.error("Error sending appliance catalog email ", e)

            logger.debug("New appliance successfully created. Adding keywords...")
            _add_keywords(request, form.cleaned_data, appliance)
            logger.debug("Keywords assigned to this appliance successfully.")
            return HttpResponseRedirect(reverse("appliance_catalog:app_list"))
    else:
        logger.info("Appliance create page requested.")
        form = ApplianceForm(request.user)
    return render(
        request, "appliance_catalog/create-edit.html", {"appliance_form": form}
    )


## this handles creating appliances shared from Horizon images
@login_required
def app_create_image(request):
    if request.method == "POST":
        logger.info(
            "Appliance create shared posted by user %s with data %s and files %s",
            request.user.username,
            request.POST,
            request.FILES,
        )
        form = ApplianceShareForm(request.user, request.POST, request.FILES)
        if form.is_valid():
            logger.debug("Appliance create form is valid. Creating new appliance...")
            appliance = form.save(commit=False)
            appliance.created_by = request.user
            appliance.updated_by = request.user
            appliance.needs_review = False
            if str(request.POST.get("chi_uc_appliance_id")):
                make_image_public(
                    request.user.username,
                    str(request.POST.get("chi_uc_appliance_id")),
                    settings.OPENSTACK_UC_REGION,
                )
            if str(request.POST.get("chi_tacc_appliance_id")):
                make_image_public(
                    request.user.username,
                    str(request.POST.get("chi_tacc_appliance_id")),
                    settings.OPENSTACK_TACC_REGION,
                )
            appliance.save()

            if request.META["HTTP_HOST"] == "www.chameleoncloud.org":
                message = "New Appliance Submitted: " + appliance.name + "."
                logger.debug(message)
                body = (
                    "A new appliance has been published to the Appliance Catalog from Horizon. \n\n"
                    "Appliance Name: " + appliance.name + "\n"
                    "Contact Name and Email: "
                    + appliance.author_name
                    + " ("
                    + appliance.author_url
                    + ")\n\n"
                    "Appliance URL: https://www.chameleoncloud.org/appliances/"
                    + str(appliance.id)
                )
                try:
                    send_mail(
                        message,
                        body,
                        "noreply@chameleoncloud.org",
                        ("systems@chameleoncloud.org",),
                        fail_silently=False,
                    )
                except SMTPException as e:
                    logger.error("Error sending appliance catalog email ", e)

            logger.debug("New appliance successfully created. Adding keywords...")
            _add_keywords(request, form.cleaned_data, appliance)
            logger.debug("Keywords assigned to this appliance successfully.")
            return HttpResponseRedirect(reverse("appliance_catalog:app_list"))
    else:
        logger.info("Appliance create page requested.")
        params = list(request.GET.items())
        params.append(
            ("author_name", request.user.first_name + " " + request.user.last_name)
        )
        params.append(
            (
                "support_contact_name",
                request.user.first_name + " " + request.user.last_name,
            )
        )
        params.append(("author_url", request.user.email))
        params.append(("support_contact_url", request.user.email))
        form = ApplianceShareForm(request.user, initial=params)
    return render(
        request,
        "appliance_catalog/create-edit-shared.html",
        {"appliance_share_form": form},
    )


@login_required
def app_edit(request, pk):
    logger.info("Appliance edit requested for appliance id: %s", pk)
    appliance = get_object_or_404(Appliance, pk=pk)

    editable = (
        request.user.is_staff
        or request.user == appliance.created_by
        or request.user.has_perm("appliance_catalog.change_appliance")
    )
    if not editable:
        messages.error(request, "You do not have permission to edit this appliance.")
        raise PermissionDenied()

    if request.method == "POST":
        logger.info(
            "Appliance edit posted by user %s with data %s and files %s",
            request.user.username,
            request.POST,
            request.FILES,
        )
        form = ApplianceForm(
            request.user, request.POST, request.FILES, instance=appliance
        )
        if form.is_valid():
            logger.debug("Appliance edit form is valid. Updating this appliance...")
            post = form.save(commit=False)
            post.updated_by = request.user
            post.save()
            logger.debug("Appliance successfully updated. Updating keywords...")
            _add_keywords(request, form.cleaned_data, appliance)
            logger.debug("Keywords updated for this appliance successfully.")
            return HttpResponseRedirect(
                reverse("appliance_catalog:app_detail", kwargs={"pk": pk})
            )
    else:
        logger.info("Appliance edit page requested.")
        form = ApplianceForm(request.user, instance=appliance)
    return render(
        request,
        "appliance_catalog/create-edit.html",
        {"appliance_form": form, "edit": True, "pk": pk},
    )


@login_required
def app_edit_image(request, pk):
    logger.info("Appliance edit requested for appliance id: %s", pk)
    appliance = get_object_or_404(Appliance, pk=pk)

    editable = (
        request.user.is_staff
        or request.user == appliance.created_by
        or request.user.has_perm("appliance_catalog.change_appliance")
    )
    if not editable:
        messages.error(request, "You do not have permission to edit this appliance.")
        raise PermissionDenied()

    if request.method == "POST":
        logger.info(
            "Appliance edit posted by user %s with data %s and files %s",
            request.user.username,
            request.POST,
            request.FILES,
        )
        form = ApplianceShareForm(
            request.user, request.POST, request.FILES, instance=appliance
        )
        if form.is_valid():
            logger.debug("Appliance edit form is valid. Updating this appliance...")
            post = form.save(commit=False)
            post.updated_by = request.user
            if str(request.POST.get("chi_uc_appliance_id")):
                make_image_public(
                    request.user.username,
                    str(request.POST.get("chi_uc_appliance_id")),
                    settings.OPENSTACK_UC_REGION,
                )
            if str(request.POST.get("chi_tacc_appliance_id")):
                make_image_public(
                    request.user.username,
                    str(request.POST.get("chi_tacc_appliance_id")),
                    settings.OPENSTACK_TACC_REGION,
                )
            post.save()
            logger.debug("Appliance successfully updated. Updating keywords...")
            _add_keywords(request, form.cleaned_data, appliance)
            logger.debug("Keywords updated for this appliance successfully.")
            return HttpResponseRedirect(
                reverse("appliance_catalog:app_detail", kwargs={"pk": pk})
            )
    else:
        logger.info("Appliance edit page requested.")
        form = ApplianceShareForm(request.user, instance=appliance)
    return render(
        request,
        "appliance_catalog/create-edit-shared.html",
        {"appliance_share_form": form, "edit": True, "pk": pk},
    )


def get_keywords(request, appliance_id=None):
    if appliance_id:
        logger.info("Get keywords requested for appliance id: %s", appliance_id)
    else:
        logger.info("Get keywords requested")
    response = {"status": "success", "message": ""}
    if appliance_id is not None:
        appliance = get_object_or_404(Appliance, pk=appliance_id)
        logger.debug("Appliance found.")
        keywords = appliance.keywords.all()
    else:
        keywords = Keyword.objects.all()
    logger.debug("Total keywords found: %d", keywords.count())
    serializer = KeywordJSONSerializer()
    response["result"] = json.loads(serializer.serialize(keywords))
    return JsonResponse(response)


def app_template(request, resource):
    logger.debug("Template requested: %s.html", resource)
    templateUrl = "appliance_catalog/%s.html" % resource
    return render(request, templateUrl)


@login_required
@staff_member_required
def app_delete(request, pk):
    response = {}
    response["result"] = None
    if request.method == "DELETE":
        logger.info(
            "Appliance delete requested for appliance id: %s by user: %s",
            pk,
            request.user.username,
        )
        try:
            appliance = Appliance.objects.get(pk=pk)
            appliance.delete()
            logger.info("Appliance deleted successfully.")
            logger.debug("Appliance found.")
            response["status"] = "success"
            response["message"] = "Deleted Successfully"
        except Appliance.DoesNotExist:
            appliance = None
            response["status"] = "error"
            response["message"] = "Appliance with id %s, not found" % pk
        return HttpResponse(json.dumps(response), content_type="application/json")
    else:
        response["status"] = "error"
        response["message"] = "Invalid method"
        return HttpResponse(
            json.dumps(response), content_type="application/json", status=405
        )


class ApplianceDeleteView(DeleteView):
    model = Appliance
    success_url = reverse_lazy("appliance_catalog:app_list")

    @method_decorator(login_required)
    @method_decorator(staff_member_required)
    def dispatch(self, *args, **kwargs):
        return super(ApplianceDeleteView, self).dispatch(*args, **kwargs)
