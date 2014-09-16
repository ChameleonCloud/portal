import os
from django.shortcuts import render
from django.core.urlresolvers import reverse

def _wantFile(path, file_name):    
    if file_name == "index.html":
        return False
    if file_name.endswith(".html"):
        return True
    return False

def _wantDir(path, file_name):    
    print("testing %s for directory" % os.path.join(path,file_name))
    if os.path.isdir(os.path.join(path,file_name)):
        return True
    return False

def _getFileInfo(file_name):
    (name,extension) = os.path.splitext(file_name)
    parts = name.split("-")
    parts = map(lambda part: part.capitalize(),parts)
    title = " ".join(parts)
    return {"file_name": file_name,
            "title": title}

def _getDirInfo(dir_name):
    parts = dir_name.split("-")
    parts = map(lambda part: part.capitalize(),parts)
    title = " ".join(parts)
    return {"dir_name": dir_name,
            "title": title}

# serve static documentation
def doc(request):

    #print("request is %s" % request)
    print("request path is %s" % request.path)
    print("pwd is %s" % request.META["PWD"])

    path = request.path[1:]  # drop leading '/'

    filesystem_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),"templates",path)
    print("fileystem path is %s" % filesystem_path)

    print("path is %s" % path)
    if path[-1] == "/":
        # maybe use the default index if there isn't an index file in the directory
        path = path[:-1]
        print("  generate an index")
        file_names = filter(lambda fn: _wantFile(filesystem_path,fn),os.listdir(filesystem_path))
        dir_names = filter(lambda fn: _wantDir(filesystem_path,fn),os.listdir(filesystem_path))
        print(file_names)
        print(dir_names)
        
        context = {
            "path": path,
            "file_info": map(lambda fn: _getFileInfo(fn),file_names),
            "dir_info": map(lambda dn: _getDirInfo(dn),dir_names),
            }
        return render(request, "documentation/index.html", context)
    else:
        return render(request, path, {})
