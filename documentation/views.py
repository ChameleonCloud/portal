import os
from django.shortcuts import render
from django.core.urlresolvers import reverse
from django.http import Http404
from github_content import util as content_util

docs_dir = os.path.join( os.path.dirname( __file__ ), 'data' )

def display_doc( request, doc_path='' ):
    doc_file = None
    if os.path.isdir( os.path.join( docs_dir, doc_path ) ):
        doc_file = os.path.join( docs_dir, doc_path, 'index.md' )
    else:
        if doc_path.endswith( '/' ):
            doc_path = doc_path[:-1]

        if os.path.isfile( os.path.join( docs_dir, doc_path + '.md' ) ):
            doc_file = os.path.join( docs_dir, doc_path + '.md' )

    if doc_file:
        fh = open( doc_file )
        markdown = fh.read()
        fh.close()
        parsed = content_util.parse_jekyll( markdown )
        doc = {
            'meta': parsed[0],
            'content': parsed[1],
        }
        return render( request, 'documentation/display_doc.html', doc )
    else:
        raise Http404
