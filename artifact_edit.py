from sharing.models import Artifact,Label,Author

a = Artifact.objects.all()

for i in range(len(a)):
    print(str(i))
    item = Artifact.objects.get(title=a[i].title) 
    print(str(item))
    if len(str(item.image).split('.')) == 1:
        item.image = None
        item.save() 
