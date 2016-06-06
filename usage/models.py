from django.db import models

QUEUES = (('kvm@tacc', 'kvm@tacc'),('kvm@uc', 'kvm@uc'),('chi@tacc', 'chi@tacc'),('chi@uc', 'chi@uc'))

class Downtime(models.Model):
    queue = models.CharField(max_length=50, choices=QUEUES)
    nodes_down = models.IntegerField("Down nodes")
    start = models.DateTimeField()
    end = models.DateTimeField(null=True, blank=True)
    description = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True, editable=False)
    created_by = models.CharField(max_length=50, editable=False)
    modified_by = models.CharField(max_length=50, editable=False)

    def __unicode__(self):
        return "{0} {1} nodes".format(self.queue, str(self.nodes_down))  
