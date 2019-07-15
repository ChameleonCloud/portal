from sharing.models import Artifact, Label, Author
from datetime import datetime
import random

'''
a = Artifact.objects.all()
for i in range(len(a)):
    print(str(i))
    item = Artifact.objects.get(title=a[i].title) 
    print(str(item))
    if len(str(item.image).split('.')) == 1:
        item.image = None
        item.save() 

'''

'''
#def delete_all_artifacts():
a = Artifact.objects.all()
for i in range(len(a)):
    item = Artifact.objects.get(title=a[i].title)
    print(str(item))
    item.delete()

for i in range(20):
    title = "Sample Artifact "+str(i+1)
    authors = random.sample(list(Author.objects.all()), random.randint(1,5))
    short_desc = "This is a sample artifact"
    long_desc = "This sample artifact was created as a sample. This is sample number "+str(i)+" made as part of a large group of samples. It has the same image as everything else and is generally uninteresting"
    if i > 10:
        image = "sharing/static/sharing/images/csicon.png"
    else:
        image = None
    
    created_at = datetime.now()
    updated_at = created_at
    labels = random.sample(list(Label.objects.all()), random.randint(0,4))
    if i == 0:
        associated_artifacts = []
    else:
        associated_artifacts = random.sample(list(Artifact.objects.all()), random.randint(0,i-1))
    item = Artifact(title=title,short_description=short_desc,description=long_desc, image=image, created_at=created_at, updated_at=updated_at)
    item.save()
    item.associated_artifacts.set(associated_artifacts)
    item.labels.set(labels)
    item.authors.set(authors)
    item.save()

#delete_all_artifacts()
#clear_images()
'''
