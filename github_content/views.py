from django.shortcuts import render
from django.http import HttpResponse
from django.http import Http404
from django.core.urlresolvers import reverse
from django.core.servers.basehttp import FileWrapper
from github_content import util
import yaml
import os
import mimetypes

content_dir = os.path.join( os.path.dirname( __file__ ), 'content' )

def about( request ):
    fh = open( os.path.join( content_dir, '_data', 'team.yml' ) )
    team = yaml.load( fh )
    fh.close()

    for member in team:
        member['image'] = member['image'][1:]

    return render( request, 'github_content/about.html', { 'team': team, 'title': 'About' } )

def nsf_cloud_workshop( request ):
    fh = open( os.path.join( content_dir, 'NSFCloudWorkshop', 'index.md' ) )
    jekyll_content = fh.read()
    fh.close()

    meta, content = util.parse_jekyll( jekyll_content )
    meta['image'] = meta['image'][1:]

    context = {
        'meta': meta,
        'content': content,
    }
    return render( request, 'github_content/markdown_page.html', context )

def nsf_cloud_workshop_attachment( request, attachment ):
    return _serve_attachment( request, 'NSFCloudWorkshop', attachment )

def news( request ):

    posts = []
    posts_dir = os.path.join( content_dir, '_posts' )
    for post in os.listdir( posts_dir ):
        fh = open( os.path.join( posts_dir, post ) )
        jekyll_content = fh.read()
        fh.close()
        meta, content = util.parse_jekyll( jekyll_content )
        if 'image' in meta:
            meta['image'] = meta['image'][1:]

        args = os.path.splitext( post )[0].split( '-', 3 )
        meta['url'] = reverse( 'github_content.views.news_story', args=args )

        posts.append( ( meta, content, ) )

    posts.reverse()

    context = {
        'title': 'News',
        'posts': posts
    }

    return render( request, 'github_content/news.html', context )

def news_story( request, year, month, day, slug ):
    post_name = '{0}-{1}-{2}-{3}.md'.format(year, month, day, slug)
    print post_name
    try:
        fh = open( os.path.join( content_dir, '_posts', post_name ) )
        jekyll_content = fh.read()
        fh.close()
    except:
        try:
            post_name = '{0}-{1}-{2}-{3}.markdown'.format(year, month, day, slug)
            fh = open( os.path.join( content_dir, '_posts', post_name ) )
            jekyll_content = fh.read()
            fh.close()
        except:
            raise Http404

    meta, content = util.parse_jekyll( jekyll_content )
    context = {
        'title': meta.get('title'),
        'author': meta.get('author'),
        'date': meta.get('date'),
        'content': content
    }

    if 'image' in meta:
        context['image'] = meta.get('image')[1:]

    return render( request, 'github_content/news_story.html', context )

def talks( request ):

    fh = open( os.path.join( content_dir, 'talks', 'index.md' ) )
    jekyll_content = fh.read()
    fh.close()
    meta, content = util.parse_jekyll( jekyll_content )

    context = {
        'meta': meta,
        'content': content
    }
    return render( request, 'github_content/markdown_page.html', context )

def talks_attachment( request, attachment ):
    return _serve_attachment( request, 'talks', attachment )

def _serve_attachment( request, dir_path, file ):
    file_path = os.path.join( content_dir, dir_path, file )
    if os.path.isfile( file_path ):
        response = HttpResponse(
            FileWrapper( open( file_path ) ),
            content_type=mimetypes.guess_type( file_path )
        )
        response['Content-Disposition'] = 'attachment; filename=%s' % file
        return response
    else:
        raise Http404
