from django.conf import settings
from django.db import models

PROGRAM_STATE__OPEN = 0
PROGRAM_STATE__ACTIVE = 1
PROGRAM_STATE__CLOSED = 2

PROGRAM_STATE_CHOICES = (
    (PROGRAM_STATE__OPEN, "Open"),
    (PROGRAM_STATE__ACTIVE, "Active"),
    (PROGRAM_STATE__CLOSED, "Closed"),
)


class EarlyUserProgram(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    state = models.IntegerField(
        choices=PROGRAM_STATE_CHOICES, default=PROGRAM_STATE__OPEN
    )

    def state_name(self):
        if self.is_open():
            return "Open"
        elif self.is_active():
            return "Active"
        elif self.is_closed():
            return "Closed"
        else:
            return "Unknown"

    def is_open(self):
        return self.state == PROGRAM_STATE__OPEN

    def is_active(self):
        return self.state == PROGRAM_STATE__ACTIVE

    def is_closed(self):
        return self.state == PROGRAM_STATE__CLOSED

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Early User Program"
        verbose_name_plural = "Early User Programs"


PARTICIPANT_STATUS__REQUESTED = 0
PARTICIPANT_STATUS__APPROVED = 1
PARTICIPANT_STATUS__DENIED = 2

PARTICIPANT_STATUS_CHOICES = (
    (PARTICIPANT_STATUS__REQUESTED, "Requested"),
    (PARTICIPANT_STATUS__APPROVED, "Approved"),
    (PARTICIPANT_STATUS__DENIED, "Denied"),
)


class EarlyUserParticipant(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    program = models.ForeignKey(
        EarlyUserProgram,
        on_delete=models.CASCADE,
    )
    justification = models.TextField()
    participant_status = models.IntegerField(
        choices=PARTICIPANT_STATUS_CHOICES, default=PARTICIPANT_STATUS__REQUESTED
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def status_name(self):
        if self.is_requested():
            return "Requested"
        elif self.is_approved():
            return "Approved"
        elif self.is_denied():
            return "Denied"
        else:
            return "Unknown"

    def is_requested(self):
        return self.participant_status == PARTICIPANT_STATUS__REQUESTED

    def is_approved(self):
        return self.participant_status == PARTICIPANT_STATUS__APPROVED

    def is_denied(self):
        return self.participant_status == PARTICIPANT_STATUS__DENIED

    def __str__(self):
        return self.user.username

    class Meta:
        verbose_name = "Early User Participant"
        verbose_name_plural = "Early User Participants"
