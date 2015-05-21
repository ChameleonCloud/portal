import binascii
import os
from django.db import models


class Token(models.Model):
    token = models.CharField(max_length=40, primary_key=True)
    nickname = models.CharField(max_length=255)
    created = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = self.generate_token()
        return super(Token, self).save(*args, **kwargs)

    def generate_token(self):
        return binascii.hexlify(os.urandom(20)).decode()

    def __unicode__(self):
        return self.token
