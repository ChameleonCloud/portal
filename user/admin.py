from django.contrib import admin
from user.models import ChameleonRole,Institution,SshPublicKey,UserProfile

admin.site.register(UserProfile)
admin.site.register(Institution)
admin.site.register(SshPublicKey)
admin.site.register(ChameleonRole)
